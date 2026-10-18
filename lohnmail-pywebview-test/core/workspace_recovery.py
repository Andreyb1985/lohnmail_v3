"""Copy-first reconnection of an external workspace after MSIX reinstall.

Never merge it with legacy AppData or infer a license from report history.
The original workspace and verified sibling backup remain intact.
"""
import hashlib
import json
import re
import shutil
import sqlite3
import tempfile
import uuid
from contextlib import closing
from pathlib import Path

from core.storage_paths import StorageError, atomic_json, inventory, validate_workspace


def _object(path):
    value = json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(value, dict):
        raise StorageError(f'Ungültige JSON-Daten: {path}')
    return value


def _validate_snapshot(snapshot, scratch):
    for path in snapshot.rglob('*.json'):
        if path.name in ('settings.json', 'license.json', 'workflow_sessions.json', '.lohnmail-workspace.json'):
            _object(path)
    for db in snapshot.rglob('*'):
        if db.is_file() and db.suffix in ('.sqlite3', '.sqlite', '.db'):
            with tempfile.TemporaryDirectory(dir=scratch) as directory:
                copy = Path(directory) / db.name
                shutil.copy2(db, copy)
                for suffix in ('-wal', '-shm'):
                    sidecar = Path(str(db) + suffix)
                    if sidecar.exists():
                        shutil.copy2(sidecar, Path(str(copy) + suffix))
                with closing(sqlite3.connect(copy.as_uri() + '?mode=ro', uri=True)) as connection:
                    if connection.execute('PRAGMA quick_check').fetchall() != [('ok',)]:
                        raise StorageError(f'Datenbank beschädigt: {db}')


def _recover_companies(snapshot, workspace, settings):
    """Retain saved IDs; use history IDs where available, directories otherwise."""
    companies = settings.setdefault('companies', [])
    if not isinstance(companies, list) or any(not isinstance(c, dict) or not isinstance(c.get('id'), str)
                                             or not c['id'] for c in companies):
        raise StorageError('Ungültige Unternehmensliste; nichts überschrieben.')
    known = {c['id']: c for c in companies}
    if len(known) != len(companies):
        raise StorageError('Doppelte Unternehmenskennungen; nichts überschrieben.')
    names = {cid: {str(c.get('name') or cid)} for cid, c in known.items()}
    db = snapshot / 'History/lohnmail_history.sqlite3'
    if db.exists():
        # SQLite may touch SHM: only read a disposable copy, never the backup.
        with tempfile.TemporaryDirectory() as directory:
            copied = Path(directory) / db.name
            shutil.copy2(db, copied)
            for suffix in ('-wal', '-shm'):
                if Path(str(db) + suffix).exists():
                    shutil.copy2(Path(str(db) + suffix), Path(str(copied) + suffix))
            with closing(sqlite3.connect(copied.as_uri() + '?mode=ro', uri=True)) as connection:
                tables = {r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                for table in ('report_records', 'send_sessions'):
                    if table not in tables:
                        continue
                    for cid, name in connection.execute(f'SELECT DISTINCT company_id, company_name FROM {table}'):
                        if not cid or not name:
                            continue
                        names.setdefault(cid, set()).add(name)
                        known.setdefault(cid, {'id': cid, 'name': name})
    workflows = snapshot / 'History/workflow_sessions.json'
    if workflows.exists():
        for cid in _object(workflows):
            if cid:
                known.setdefault(cid, {'id': cid, 'name': cid})
    def folder_name(name):
        value = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', '_', str(name).strip())
        value = re.sub(r'\s+', '_', value).strip(' ._')
        return 'Lohn_' + (re.sub('_+', '_', value)[:80] or 'Unternehmen')
    company_root = snapshot / 'Companies'
    for folder in sorted(company_root.iterdir()) if company_root.is_dir() else []:
        if not folder.is_dir():
            continue
        matches = [c for cid, c in known.items() if any(folder_name(n) == folder.name for n in names.get(cid, ()))
                   or Path(c.get('output_dir') or '.').name == folder.name]
        if len(matches) > 1:
            raise StorageError(f'Mehrdeutige Unternehmenszuordnung: {folder.name}. Nichts überschrieben.')
        if matches:
            company = matches[0]
        else:
            cid = 'recovered-' + hashlib.sha256(folder.name.encode()).hexdigest()[:16]
            company = {'id': cid, 'name': folder.name.removeprefix('Lohn_')}
            known[cid] = company
        # A saved custom output location is not the company-root setting.
        # Reconnecting the workspace must not redirect future processing.
        if not company.get('output_dir'):
            company['output_dir'] = str(workspace / 'Companies' / folder.name)
    settings['companies'] = list(known.values())
    if settings.get('selected_company_id') not in known:
        settings['selected_company_id'] = next(iter(known), '')


def reconnect_workspace(root, workspace, local, family):
    """User has explicitly selected reuse. Journal makes the switch restartable."""
    workspace = validate_workspace(workspace, local)
    journal = root / 'workspace-reconnect.json'
    if journal.exists():
        plan = _object(journal)
        if plan['workspace'] != str(workspace) or plan['family'] != family:
            raise StorageError('Andere Wiederherstellung läuft bereits; nichts überschrieben.')
    else:
        if (root / 'Data').exists():
            raise StorageError('Vorhandene Programmeinstellungen weichen ab; nichts überschrieben.')
        backup = workspace.parent / ('LohnMail-Recovery-' + uuid.uuid4().hex)
        backup.mkdir()
        snapshot = backup / 'Workspace'
        before = inventory(workspace)  # Reject symlinks/reparse points and unreadable data.
        shutil.copytree(workspace, snapshot)
        if inventory(snapshot) != before or inventory(workspace) != before:
            raise StorageError(f'Sicherung unvollständig. Originaldaten unverändert. Sicherung: {backup}')
        _validate_snapshot(snapshot, backup)
        for name in ('Companies', 'History', 'Settings'):
            if (snapshot / name).exists() and not (snapshot / name).is_dir():
                raise StorageError(f'Kein Ordner: {workspace / name}. Sicherung: {backup}')
        marker = snapshot / '.lohnmail-workspace.json'
        identity = _object(marker).get('id') if marker.exists() else uuid.uuid4().hex
        if not isinstance(identity, str) or not identity:
            raise StorageError(f'Ungültige Arbeitsordner-Kennung. Sicherung: {backup}')
        stage = root / ('reconnect-stage-' + uuid.uuid4().hex)
        (stage / 'Settings').mkdir(parents=True)
        if (snapshot / 'Settings').exists():
            shutil.copytree(snapshot / 'Settings', stage / 'Settings', dirs_exist_ok=True)
        for name in ('settings.json', 'license.json', 'machine_id', 'secrets.dat'):
            saved, target = snapshot / name, stage / 'Settings' / name
            if saved.exists():
                if target.exists() and target.read_bytes() != saved.read_bytes():
                    raise StorageError(f'Widersprüchliche Einstellungen: {name}. Sicherung: {backup}')
                shutil.copy2(saved, target)
        settings_file = stage / 'Settings/settings.json'
        had_settings = settings_file.exists()
        settings = _object(settings_file) if had_settings else {}
        _recover_companies(snapshot, workspace, settings)
        atomic_json(settings_file, settings)
        plan = {'family': family, 'workspace': str(workspace), 'id': identity,
                'backup': str(backup), 'original': before, 'stage': str(stage),
                'state_files': inventory(stage), 'had_settings': had_settings,
                'had_license': (stage / 'Settings/license.json').exists()}
        atomic_json(backup / 'verification.json', plan)
        atomic_json(journal, plan)  # No workspace/state mutation before a verified backup.
    snapshot = Path(plan['backup']) / 'Workspace'
    if inventory(snapshot) != plan['original']:
        raise StorageError(f'Sicherung wurde verändert: {snapshot}. Nichts umgeschaltet.')
    current = inventory(workspace)
    marker = workspace / '.lohnmail-workspace.json'
    if '.lohnmail-workspace.json' not in plan['original'] and marker.exists():
        if _object(marker) != {'id': plan['id']}:
            raise StorageError('Arbeitsordner-Kennung wurde geändert; nichts überschrieben.')
        current.pop('.lohnmail-workspace.json', None)
    if current != plan['original']:
        raise StorageError('Arbeitsordner wurde während der Wiederherstellung geändert; nichts überschrieben.')
    stage, target = Path(plan['stage']), root / 'Data'
    if target.exists():
        if inventory(target) != plan['state_files']:
            raise StorageError('Vorhandene Programmeinstellungen weichen ab; nichts überschrieben.')
    else:
        if inventory(stage) != plan['state_files']:
            raise StorageError('Wiederherstellungskopie unvollständig; nichts umgeschaltet.')
        stage.rename(target)
    for name in ('Companies', 'History'):
        (workspace / name).mkdir(exist_ok=True)
    if not marker.exists():
        atomic_json(marker, {'id': plan['id']})
    layout = {'format': 2, 'id': plan['id'], 'family': family,
              'state': str(target), 'workspace': str(workspace)}
    atomic_json(root / 'workspace-recovery-notice.json', {
        'backup': plan['backup'], 'settings_restored': plan['had_settings'],
        'license_restored': plan['had_license']})
    atomic_json(root / 'storage-layout.json', layout)  # Commit last.
    return layout

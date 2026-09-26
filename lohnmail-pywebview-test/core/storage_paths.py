"""Explicit package app-data and an external Documents/LohnMail workspace.

Virtualization stays enabled. Legacy AppData must be exported outside the package
before import: a packaged process cannot reliably inspect both physical stores.
"""
from pathlib import Path
from contextlib import closing
import ctypes
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import uuid


class StorageError(RuntimeError):
    pass


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=path.name + '.', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def package_identity():
    # Store-distributed Python itself may have a package identity. A source
    # run is not an installed LohnMail package and must retain direct behavior.
    if sys.platform != 'win32' or not getattr(sys, 'frozen', False):
        return None
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    def query(name):
        fn = getattr(kernel, name)
        fn.argtypes = [ctypes.POINTER(wintypes.UINT), wintypes.LPWSTR]
        fn.restype = ctypes.c_long
        length = wintypes.UINT()
        result = fn(ctypes.byref(length), None)
        if result == 15700:  # APPMODEL_ERROR_NO_PACKAGE
            return None
        if result != 122:
            raise StorageError(f'Paketidentität konnte nicht ermittelt werden ({result}).')
        buffer = ctypes.create_unicode_buffer(length.value)
        result = fn(ctypes.byref(length), buffer)
        if result:
            raise StorageError(f'Paketidentität konnte nicht gelesen werden ({result}).')
        return buffer.value
    family = query('GetCurrentPackageFamilyName')
    return (family, Path(query('GetCurrentPackagePath'))) if family else None


def real_local_appdata():
    from core.windows_storage import known_folder
    return known_folder('F1B32785-6FBA-4FCF-9D55-7B8E7F157091')


def inventory(root):
    """Fail on unreadable files/reparse points instead of silently skipping them."""
    root = Path(root)
    try:
        info = root.lstat()
    except FileNotFoundError:
        return {}
    if root.is_symlink() or getattr(info, 'st_file_attributes', 0) & 0x400:
        raise StorageError(f'Verknüpfung im Datenbestand: {root}. Bitte Support kontaktieren.')
    if not root.is_dir():
        raise StorageError(f'Datenordner ist keine Ordner: {root}')
    result = {}
    for directory, dirs, files in os.walk(root, onerror=lambda e: (_ for _ in ()).throw(e)):
        for name in dirs + files:
            p = Path(directory) / name
            if p.is_symlink() or getattr(p.lstat(), 'st_file_attributes', 0) & 0x400:
                raise StorageError(f'Verknüpfung im Datenbestand: {p}. Bitte Support kontaktieren.')
        for name in files:
            p = Path(directory) / name
            digest = hashlib.sha256()
            with p.open('rb') as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                    digest.update(chunk)
            result[p.relative_to(root).as_posix()] = digest.hexdigest()
    return result


def _finish_migration(root, journal, state):
    stage, original = Path(state['stage']), Path(state['original'])
    expected = state['expected']
    if stage.exists():
        if inventory(stage) != expected:
            raise StorageError(f'Kopie unvollständig: {stage}. Originaldaten bleiben erhalten.')
        if root.exists():
            if original.exists():
                raise StorageError(f'Migrationskonflikt: {root}. Bitte Support kontaktieren.')
            if inventory(root) != state['ordinary']:
                raise StorageError(f'Daten wurden während der Migration geändert: {root}.')
            root.rename(original)
        stage.rename(root)
    if inventory(root) != expected:
        raise StorageError(f'Migration nicht bestätigt: {root}. Sicherung: {original.parent}')
    atomic_json(journal, {**state, 'phase': 'complete'})
    return root


def migrate_storage(root, redirected):
    """Merge disposable exported snapshots, NEVER live/virtualized AppData.

    Caller holds a process lock. Export originals are retained separately.
    """
    root, redirected = Path(root), Path(redirected)
    journal = root.parent / '.LohnMail-storage-migration.json'
    if journal.exists():
        state = json.loads(journal.read_text(encoding='utf-8'))
        if state['phase'] == 'complete':
            if state.get('expected') and not root.exists():
                raise StorageError(f'Datenordner fehlt: {root}. Bitte Sicherung wiederherstellen.')
            remaining = inventory(redirected)
            if remaining and remaining != state.get('virtual', {}):
                raise StorageError(f'Alter Paket-Datenbestand wurde nach der Migration geändert: {redirected}. Bitte Support kontaktieren; nichts überschrieben.')
            return root
        if state['phase'] == 'ready':
            return _finish_migration(root, journal, state)
    ordinary, virtual = inventory(root), inventory(redirected)
    if not virtual:
        atomic_json(journal, {'phase': 'complete', 'expected': ordinary, 'virtual': virtual})
        return root
    backup = root.parent / ('LohnMail-storage-backup-' + uuid.uuid4().hex)
    backup.mkdir()
    for label, source, expected in [('ordinary', root, ordinary), ('redirected', redirected, virtual)]:
        if source.exists():
            shutil.copytree(source, backup / label)
            if inventory(backup / label) != expected or inventory(source) != expected:
                raise StorageError(f'Sicherung fehlgeschlagen: {source}. Keine Daten umgeschaltet.')
    conflicts = [name for name in ordinary.keys() & virtual.keys() if ordinary[name] != virtual[name]]
    # A database and its WAL/SHM form one snapshot. Never combine sidecars
    # from separate stores, even if the main database bytes are identical.
    for name in ordinary.keys() & virtual.keys():
        if name.endswith(('.sqlite3', '.sqlite', '.db')):
            for suffix in ('-wal', '-shm'):
                if ordinary.get(name + suffix) != virtual.get(name + suffix):
                    conflicts.append(name + suffix)
    # Treat case-only collisions as conflicts even when testing on a case-sensitive OS.
    names = {}
    for name in ordinary.keys() | virtual.keys():
        if name.casefold() in names and names[name.casefold()] != name:
            conflicts.append(name)
        names[name.casefold()] = name
    if conflicts:
        atomic_json(backup / 'conflicts.json', conflicts)
        raise StorageError(f'Unterschiedliche Datenbestände gefunden. Nichts überschrieben. '
                           f'Bitte Support kontaktieren. Sicherung und Konfliktliste: {backup}')
    stage = backup / 'staged'
    stage.mkdir()
    for label in ('ordinary', 'redirected'):
        if (backup / label).exists():
            shutil.copytree(backup / label, stage, dirs_exist_ok=True)
    expected = {**ordinary, **virtual}
    if inventory(stage) != expected:
        raise StorageError(f'Kopie konnte nicht bestätigt werden: {stage}')
    for name in ('settings.json', 'license.json'):
        saved = stage / 'Settings' / name
        if saved.exists():
            try:
                if not isinstance(json.loads(saved.read_text(encoding='utf-8')), dict):
                    raise ValueError('JSON-Objekt erwartet')
            except (ValueError, UnicodeError) as exc:
                raise StorageError(f'Ungültige Daten, keine Migration: {saved}') from exc
    for db in stage.rglob('*.sqlite3'):
        # Validate a disposable copy including WAL, never mutate staged/original
        # files (SQLite can regenerate SHM even for a read-only connection).
        with tempfile.TemporaryDirectory(dir=backup) as check_dir:
            checked = Path(check_dir) / db.name
            shutil.copy2(db, checked)
            for suffix in ('-wal', '-shm'):
                sidecar = Path(str(db) + suffix)
                if sidecar.exists():
                    shutil.copy2(sidecar, Path(str(checked) + suffix))
            with closing(sqlite3.connect(checked.as_uri() + '?mode=ro', uri=True)) as connection:
                if connection.execute('PRAGMA quick_check').fetchall() != [('ok',)]:
                    raise StorageError(f'Datenbankprüfung fehlgeschlagen: {db}')
    if inventory(root) != ordinary or inventory(redirected) != virtual:
        raise StorageError('Daten wurden gleichzeitig geändert. Alle LohnMail-Instanzen schließen.')
    state = {'phase': 'ready', 'stage': str(stage), 'original': str(backup / 'original'),
             'ordinary': ordinary, 'expected': expected, 'virtual': virtual}
    atomic_json(journal, state)
    return _finish_migration(root, journal, state)


def _remap(value, aliases):
    if isinstance(value, dict):
        return {k: _remap(v, aliases) for k, v in value.items()}
    if isinstance(value, list):
        return [_remap(v, aliases) for v in value]
    if isinstance(value, str):
        normalized = value.replace('\\', '/')
        for old, new in aliases:
            prefix = str(old).replace('\\', '/').rstrip('/')
            if normalized.casefold() == prefix.casefold():
                return str(new)
            if normalized.casefold().startswith(prefix.casefold() + '/'):
                return str(Path(new) / normalized[len(prefix) + 1:])
    return value


def _rewrite_snapshot_paths(root, aliases):
    """Only rewrite new copies, with untouched, hashed snapshots retained."""
    for path in root.rglob('*.json'):
        if path.name not in {'settings.json', 'workflow_sessions.json', 'lohnmail_reports_index.json'}:
            continue
        data = json.loads(path.read_text(encoding='utf-8-sig'))
        atomic_json(path, _remap(data, aliases))
    for path in root.rglob('lohnmail_history.sqlite3'):
        with closing(sqlite3.connect(path)) as connection:
            tables = connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            for (table,) in tables:
                if table.startswith('sqlite_'):
                    continue
                quoted = '"' + table.replace('"', '""') + '"'
                fields = connection.execute('PRAGMA table_info(' + quoted + ')').fetchall()
                for field in fields:
                    name = '"' + field[1].replace('"', '""') + '"'
                    # Replace only whole string path values / JSON values, not substrings.
                    for (old,) in connection.execute('SELECT DISTINCT ' + name + ' FROM ' + quoted).fetchall():
                        if not isinstance(old, str):
                            continue
                        new = _remap(old, aliases)
                        if new == old and old.startswith(('{', '[')):
                            try:
                                obj = json.loads(old)
                                mapped = _remap(obj, aliases)
                                if mapped != obj:
                                    new = json.dumps(mapped, ensure_ascii=False)
                            except ValueError:
                                pass
                        if new != old:
                            connection.execute('UPDATE ' + quoted + ' SET ' + name + '=? WHERE ' + name + '=?', (new, old))
            connection.commit()
            if connection.execute('PRAGMA quick_check').fetchall() != [('ok',)]:
                raise StorageError(f'Datenbankprüfung fehlgeschlagen: {path}')
            connection.execute('PRAGMA wal_checkpoint(TRUNCATE)')


def validate_workspace(path, local):
    workspace = writable_directory(path)
    # AppData is virtualized; workspace and exported snapshots must be outside it.
    if workspace.is_relative_to(Path(local).parent.resolve()):
        raise StorageError('Bitte einen Arbeitsordner außerhalb von AppData wählen.')
    return workspace


def _read_export(bundle, family):
    manifest = json.loads((bundle / 'export.json').read_text(encoding='utf-8-sig'))
    if manifest.get('format') != 1 or manifest.get('family') != family or not manifest.get('complete'):
        raise StorageError(f'Die Datensicherung passt nicht zu diesem Paket: {bundle}')
    if set(manifest.get('sources', {})) != {'ordinary', 'redirected'}:
        raise StorageError(f'Unvollständige Datensicherung: {bundle}')
    for label, data in manifest['sources'].items():
        if inventory(bundle / label) != data['files']:
            raise StorageError(f'Die Sicherung wurde verändert oder ist unvollständig: {bundle / label}')
    return manifest


def _commit_layout(root, plan):
    for item in plan['installs']:
        stage, target = Path(item['stage']), Path(item['target'])
        if target.exists():
            if inventory(target) != item['files']:
                raise StorageError(f'Ziel wurde verändert. Nichts überschrieben: {target}')
        else:
            if inventory(stage) != item['files'] or not stage.is_dir():
                raise StorageError(f'Kopie ist unvollständig: {stage}')
            stage.rename(target)
    atomic_json(root / 'storage-layout.json', plan['layout'])
    return plan['layout']


def initialize_package_storage(root, cache, local, family, choose):
    """Called under package-local process lock before any settings are loaded.

    No unvirtualized access is claimed from a packaged process. Legacy imports
    require a hashed export made by our PowerShell tool outside package identity.
    """
    layout_file = root / 'storage-layout.json'
    if layout_file.exists():
        layout = json.loads(layout_file.read_text(encoding='utf-8'))
        if layout.get('format') != 2 or layout.get('family') != family:
            raise StorageError('Unbekannte Speicherkonfiguration. Bitte Support kontaktieren.')
        state, workspace = Path(layout['state']), Path(layout['workspace'])
        if state != root / 'Data':
            raise StorageError('Ungültiger Einstellungspfad.')
        # Missing workspace must never silently create an empty replacement.
        marker = workspace / '.lohnmail-workspace.json'
        if (not marker.is_file() or json.loads(marker.read_text(encoding='utf-8')) != {'id': layout['id']}
                or not (workspace / 'Companies').is_dir() or not (workspace / 'History').is_dir()
                or not (state / 'Settings').is_dir()):
            raise StorageError(f'Arbeitsordner fehlt oder ist nicht erreichbar: {workspace}. '
                               'Bitte Laufwerk verbinden oder den vollständigen Arbeitsordner wiederherstellen.')
        return layout
    pending = root / 'storage-pending.json'
    if pending.exists():
        plan = json.loads(pending.read_text(encoding='utf-8'))
        if plan.get('phase') == 'prepared':
            return _commit_layout(root, plan)
        workspace = validate_workspace(plan['workspace'], local)
    else:
        selected = choose()
        if selected is None:
            raise StorageError('Einrichtung abgebrochen. Vorhandene Daten wurden nicht verändert.')
        workspace = validate_workspace(selected, local)
        if any((workspace / name).exists() for name in ('Companies', 'History', '.lohnmail-workspace.json')):
            raise StorageError(f'Der Arbeitsordner enthält bereits LohnMail-Daten: {workspace}. '
                               'Bitte Support zur Übernahme kontaktieren; nichts wird überschrieben.')
        plan = {'phase': 'copy', 'id': uuid.uuid4().hex, 'workspace': str(workspace)}
        atomic_json(pending, plan)
    bundle = workspace / 'LohnMail-Legacy-Export'
    legacy_roots = [local / 'LohnMail', cache / 'Local' / 'LohnMail', local / 'Programs' / 'LohnMail']
    if not (bundle / 'export.json').exists() and any(p.exists() for p in legacy_roots):
        raise StorageError('Vorhandene LohnMail-Daten gefunden. Ein automatisches Zusammenführen '
                           'innerhalb des MSIX-Pakets wäre nicht sicher. Programm schließen und '
                           'Export-LegacyStorage.ps1 in normaler Windows PowerShell starten. '
                           f'Arbeitsordner für die Sicherung: {workspace}. Keine Lizenz zurückgesetzt.')
    # A failed copy is retained for diagnosis. Retry in a new staging directory;
    # do not combine SQLite sidecars from a previous interrupted attempt.
    backup = workspace / ('.lohnmail-transfer-' + uuid.uuid4().hex)
    backup.mkdir()
    merged = backup / 'Merged'
    sources = {}
    if (bundle / 'export.json').exists():
        exported = _read_export(bundle, family)
        sources = exported['sources']
        # Immutable export remains the backup. Work only on additional copies.
        merge_journal = backup / '.LohnMail-storage-migration.json'
        if not merge_journal.exists():
            for label, target in [('ordinary', merged), ('redirected', backup / 'Virtual')]:
                if not target.exists():
                    shutil.copytree(bundle / label, target)
                if inventory(target) != sources[label]['files']:
                    raise StorageError(f'Kopie unvollständig: {target}. Sicherung bleibt erhalten.')
        migrate_storage(merged, backup / 'Virtual')
        _read_export(bundle, family)  # recheck sources after copy
    else:
        merged.mkdir(exist_ok=True)
    state_stage = root / ('stage-' + uuid.uuid4().hex)
    docs_stage, history_stage = backup / 'Companies', backup / 'History'
    for p in (state_stage / 'Settings', docs_stage, history_stage):
        p.mkdir(parents=True, exist_ok=True)
    if (merged / 'Settings').exists():
        shutil.copytree(merged / 'Settings', state_stage / 'Settings', dirs_exist_ok=True)
        if inventory(merged / 'Settings') != inventory(state_stage / 'Settings'):
            raise StorageError('Einstellungskopie unvollständig. Keine Daten umgeschaltet.')
    if (merged / 'Companies').exists():
        shutil.copytree(merged / 'Companies', docs_stage, dirs_exist_ok=True)
        if inventory(merged / 'Companies') != inventory(docs_stage):
            raise StorageError('Dokumentenkopie unvollständig. Keine Daten umgeschaltet.')
    # Earlier layouts kept these files directly under the data root. A SQLite
    # group must come from one location, never mix flat/nested WAL snapshots.
    flat_db = merged / 'lohnmail_history.sqlite3'
    nested_db = state_stage / 'Settings' / flat_db.name
    for suffix in ('-wal', '-shm'):
        flat_sidecar = Path(str(flat_db) + suffix)
        nested_sidecar = Path(str(nested_db) + suffix)
        if flat_sidecar.exists() and not flat_db.exists():
            raise StorageError('Unvollständige alte Datenbankgruppe. Originaldaten bleiben erhalten.')
        if flat_db.exists() and nested_db.exists():
            if (flat_sidecar.exists() != nested_sidecar.exists()
                    or (flat_sidecar.exists() and flat_sidecar.read_bytes() != nested_sidecar.read_bytes())):
                raise StorageError('Widersprüchliche alte Datenbankgruppen. Originaldaten bleiben erhalten.')
    # Earlier layouts kept these files directly under the data root.
    for name in ('settings.json', 'license.json', 'machine_id', 'secrets.dat',
                 'lohnmail_history.sqlite3', 'lohnmail_history.sqlite3-wal',
                 'lohnmail_history.sqlite3-shm', 'workflow_sessions.json'):
        source, target = merged / name, state_stage / 'Settings' / name
        if source.exists():
            if target.exists() and source.read_bytes() != target.read_bytes():
                raise StorageError(f'Widersprüchliche alte Einstellungen: {name}. Sicherungen bleiben erhalten.')
            shutil.copy2(source, target)
    # History is valuable user data; it belongs to the workspace, not app cache.
    for name in ('lohnmail_history.sqlite3', 'lohnmail_history.sqlite3-wal',
                 'lohnmail_history.sqlite3-shm', 'workflow_sessions.json'):
        source = state_stage / 'Settings' / name
        if source.exists():
            shutil.copy2(source, history_stage / name)
            if inventory(source.parent).get(name) != inventory(history_stage).get(name):
                raise StorageError('Verlaufskopie unvollständig. Keine Daten umgeschaltet.')
            source.unlink()  # disposable stage only, never export/source
    aliases = []
    for source in sources.values():
        aliases.append((str(Path(source['path']) / 'Companies'), workspace / 'Companies'))
    # Include the logical root even for a redirected-only export.
    aliases.append((str(local / 'LohnMail' / 'Companies'), workspace / 'Companies'))
    _rewrite_snapshot_paths(state_stage, aliases)
    _rewrite_snapshot_paths(history_stage, aliases)
    _rewrite_snapshot_paths(docs_stage, aliases)
    for p in (state_stage / 'Settings' / 'settings.json', state_stage / 'Settings' / 'license.json'):
        if p.exists() and not isinstance(json.loads(p.read_text(encoding='utf-8')), dict):
            raise StorageError(f'Ungültige Einstellungen, Originaldaten bleiben erhalten: {p}')
    layout = {'format': 2, 'id': plan['id'], 'family': family,
              'state': str(root / 'Data'), 'workspace': str(workspace)}
    installs = [{'stage': str(s), 'target': str(t), 'files': inventory(s)} for s, t in (
        (state_stage, root / 'Data'), (docs_stage, workspace / 'Companies'),
        (history_stage, workspace / 'History'))]
    atomic_json(workspace / '.lohnmail-workspace.json', {'id': plan['id']})
    plan = {**plan, 'phase': 'prepared', 'installs': installs, 'layout': layout}
    atomic_json(pending, plan)
    return _commit_layout(root, plan)


_package_root = None
_workspace_root = None


def prepare_storage_or_exit():
    """Run before config/logging/licensing imports; never fall back to empty data."""
    try:
        if '--lohnmail-storage-probe' in sys.argv:
            index = sys.argv.index('--lohnmail-storage-probe')
            output, workspace = map(Path, sys.argv[index + 1:index + 3])
            if not package_identity() or os.environ.get('LOHNMAIL_DATA_DIR'):
                raise StorageError('Speichertest benötigt echte Paketidentität ohne Daten-Override.')
            # CLI is for installed-package CI, never an implicit production override.
            from core import windows_storage
            original_picker = windows_storage.default_workspace
            windows_storage.default_workspace = lambda: workspace
            try:
                root = packaged_data_root()
                atomic_json(output, {'family': package_identity()[0], 'state': str(root),
                                     'workspace': str(_workspace_root)})
            finally:
                windows_storage.default_workspace = original_picker
            raise SystemExit(0)
        if not os.environ.get('LOHNMAIL_DATA_DIR'):
            packaged_data_root()
    except Exception as exc:
        message = 'LohnMail konnte den Datenbestand nicht sicher öffnen.\n\n' + str(exc)
        if sys.platform == 'win32' and '--lohnmail-storage-probe' not in sys.argv:
            from ctypes import wintypes
            show = ctypes.windll.user32.MessageBoxW
            show.argtypes = [wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.UINT]
            show(None, message, 'LohnMail – Datenspeicher', 0x10)
        raise SystemExit(message) from exc


def packaged_data_root():
    global _package_root, _workspace_root
    if _package_root is not None:
        return _package_root
    identity = package_identity()
    if not identity:
        return None
    from core.windows_storage import application_folders, default_workspace
    family, _ = identity
    state_folder, cache_folder = application_folders(family)
    root = state_folder / 'LohnMail'
    root.mkdir(parents=True, exist_ok=True)
    import msvcrt
    with (root / '.storage.lock').open('a+b') as lock:
        lock.write(b'\0')
        lock.flush()
        lock.seek(0)
        try:
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as exc:
            raise StorageError('Die Datenmigration läuft bereits. Andere LohnMail-Instanzen schließen.') from exc
        try:
            layout = initialize_package_storage(
                root, cache_folder, real_local_appdata(), family, default_workspace)
            _package_root = Path(layout['state'])
            _workspace_root = Path(layout['workspace'])
        finally:
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
    return _package_root


def packaged_workspace_root():
    if os.environ.get('LOHNMAIL_DATA_DIR'):
        return None
    packaged_data_root()
    return _workspace_root


def validate_output_location(path):
    """No payroll outputs in virtualized AppData in the new packaged layout."""
    workspace = packaged_workspace_root()
    if workspace is not None:
        if not all((workspace / part).exists() for part in ('.lohnmail-workspace.json', 'Companies', 'History')):
            raise StorageError(f'Arbeitsordner nicht erreichbar: {workspace}. Keine neue Datenstruktur angelegt.')
        resolved = Path(path).expanduser().resolve()
        if resolved.is_relative_to(real_local_appdata().parent.resolve()):
            raise StorageError(f'Bitte einen Ausgabeordner außerhalb von AppData wählen: {path}')
    return Path(path)


def writable_directory(path):
    path = Path(path).expanduser().resolve(strict=True)
    if not path.is_dir():
        raise OSError(f'Kein Ordner: {path}')
    fd, probe = tempfile.mkstemp(prefix='.lohnmail-write-', dir=path)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(b'LohnMail')
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        os.unlink(probe)
    return path


def dialog_directory():
    # Never probe the previously saved path (it may be a disconnected UNC share).
    for candidate in (Path.home() / 'Documents', Path.home(), Path(tempfile.gettempdir())):
        try:
            if candidate.is_dir() and os.access(candidate, os.R_OK | os.X_OK):
                return str(candidate)
        except OSError:
            continue
    return ''

import json
import sqlite3
from pathlib import Path
from unittest.mock import Mock

import pytest
from core import storage_paths as storage
from core import workspace_recovery as recovery


def setup(tmp_path):
    root = tmp_path / 'LocalState/LohnMail'
    root.mkdir(parents=True)
    workspace = tmp_path / 'Documents/LohnMail'
    (workspace / 'Companies/Lohn_Test').mkdir(parents=True)
    (workspace / 'Companies/Lohn_Test/result.pdf').write_bytes(b'SYNTHETIC-PDF')
    (workspace / 'History').mkdir()
    return root, workspace, tmp_path / 'AppData/Local'


def initialize(root, workspace, local, choice):
    return storage.initialize_package_storage(root, local / 'cache', local, 'test-family',
        lambda: workspace, resolve_existing=choice)


def test_reinstall_reconnects_then_restarts_without_prompt(tmp_path):
    old, workspace, local = setup(tmp_path)
    storage.atomic_json(workspace / '.lohnmail-workspace.json', {'id': 'original-id'})
    with sqlite3.connect(workspace / 'History/lohnmail_history.sqlite3') as db:
        db.execute('CREATE TABLE report_records(company_id TEXT, company_name TEXT)')
        db.execute("INSERT INTO report_records VALUES ('preserved-id', 'Test')")
    before = storage.inventory(workspace)
    choice = Mock(return_value=('reuse', workspace))
    layout = initialize(old, workspace, local, choice)
    assert layout['id'] == 'original-id'
    assert storage.inventory(workspace) == before
    plan = json.loads((old / 'workspace-reconnect.json').read_text())
    assert storage.inventory(Path(plan['backup']) / 'Workspace') == before
    settings = json.loads((old / 'Data/Settings/settings.json').read_text())
    assert settings['companies'][0]['id'] == 'preserved-id'
    assert settings['companies'][0]['output_dir'] == str(workspace / 'Companies/Lohn_Test')
    assert not (old / 'Data/Settings/license.json').exists()
    assert initialize(old, workspace, local, Mock(side_effect=AssertionError())) == layout


def test_restore_only_available_settings_license_and_dpapi(tmp_path):
    root, workspace, local = setup(tmp_path)
    (workspace / 'Settings').mkdir()
    storage.atomic_json(workspace / 'Settings/settings.json', {'smtp': {'server': 'synthetic.invalid'},
        'companies': [{'id': 'keep-id', 'name': 'Test'}]})
    storage.atomic_json(workspace / 'Settings/license.json', {'license_key': 'SYNTHETIC-KEEP', 'machine_id': 'bound'})
    (workspace / 'Settings/secrets.dat').write_bytes(b'SYNTHETIC-DPAPI-CIPHERTEXT')
    recovery.reconnect_workspace(root, workspace, local, 'test-family')
    assert (root / 'Data/Settings/license.json').read_bytes() == (workspace / 'Settings/license.json').read_bytes()
    assert (root / 'Data/Settings/secrets.dat').read_bytes() == (workspace / 'Settings/secrets.dat').read_bytes()
    assert json.loads((root / 'Data/Settings/settings.json').read_text())['smtp']['server'] == 'synthetic.invalid'


@pytest.mark.parametrize('choice', [None, 'new'])
def test_cancel_or_choose_new_leaves_old_workspace_unchanged(tmp_path, choice):
    root, workspace, local = setup(tmp_path)
    fresh = tmp_path / 'Other'; fresh.mkdir()
    before = storage.inventory(workspace)
    resolver = Mock(return_value=None if choice is None else ('new', fresh))
    if choice is None:
        with pytest.raises(storage.StorageError, match='abgebrochen'):
            initialize(root, workspace, local, resolver)
        assert not (root / 'storage-layout.json').exists()
    else:
        layout = initialize(root, workspace, local, resolver)
        assert layout['workspace'] == str(fresh)
    assert storage.inventory(workspace) == before
    assert not list(workspace.parent.glob('LohnMail-Recovery-*'))


@pytest.mark.parametrize('failure', ['json', 'database', 'conflict', 'directory', 'marker'])
def test_invalid_data_offers_another_folder_without_overwriting(tmp_path, failure):
    root, workspace, local = setup(tmp_path)
    if failure == 'json': (workspace / 'settings.json').write_text('invalid')
    if failure == 'database': (workspace / 'History/bad.sqlite3').write_bytes(b'broken')
    if failure == 'conflict':
        (workspace / 'Settings').mkdir()
        storage.atomic_json(workspace / 'Settings/license.json', {'key': 'A'})
        storage.atomic_json(workspace / 'license.json', {'key': 'B'})
    if failure == 'directory': (workspace / 'Settings').write_text('not-a-directory')
    if failure == 'marker': storage.atomic_json(workspace / '.lohnmail-workspace.json', {'id': ''})
    before = storage.inventory(workspace)
    fresh = tmp_path / 'Other'; fresh.mkdir()
    decisions = Mock(side_effect=[('reuse', workspace), ('new', fresh)])
    layout = initialize(root, workspace, local, decisions)
    assert layout['workspace'] == str(fresh)
    assert decisions.call_args_list[1].args[1]  # Visible error before alternative choice.
    assert storage.inventory(workspace) == before


def test_backup_failure_never_switches(tmp_path, monkeypatch):
    root, workspace, local = setup(tmp_path)
    before = storage.inventory(workspace)
    monkeypatch.setattr(recovery.shutil, 'copytree', Mock(side_effect=OSError('disk full')))
    with pytest.raises(OSError, match='disk full'):
        recovery.reconnect_workspace(root, workspace, local, 'test-family')
    assert not (root / 'storage-layout.json').exists()
    assert not (root / 'Data').exists()
    assert storage.inventory(workspace) == before


@pytest.mark.parametrize('point', ['state', 'marker', 'layout'])
def test_interrupted_reconnect_resumes_without_data_loss(tmp_path, monkeypatch, point):
    root, workspace, local = setup(tmp_path)
    original_json, original_rename = recovery.atomic_json, Path.rename
    def interrupted_json(path, data):
        if (point == 'layout' and Path(path).name == 'storage-layout.json') or (
                point == 'marker' and Path(path).name == '.lohnmail-workspace.json'):
            raise OSError('interrupted')
        return original_json(path, data)
    def interrupted_rename(path, target):
        if point == 'state' and Path(target) == root / 'Data': raise OSError('interrupted')
        return original_rename(path, target)
    monkeypatch.setattr(recovery, 'atomic_json', interrupted_json)
    monkeypatch.setattr(Path, 'rename', interrupted_rename)
    with pytest.raises(OSError, match='interrupted'):
        recovery.reconnect_workspace(root, workspace, local, 'test-family')
    monkeypatch.setattr(recovery, 'atomic_json', original_json)
    monkeypatch.setattr(Path, 'rename', original_rename)
    layout = initialize(root, workspace, local, Mock(side_effect=AssertionError()))
    assert layout['workspace'] == str(workspace)
    assert (workspace / 'Companies/Lohn_Test/result.pdf').read_bytes() == b'SYNTHETIC-PDF'
    assert len(list(workspace.parent.glob('LohnMail-Recovery-*'))) == 1


def test_changed_data_after_interruption_does_not_switch(tmp_path, monkeypatch):
    root, workspace, local = setup(tmp_path)
    original = Path.rename
    monkeypatch.setattr(Path, 'rename', Mock(side_effect=OSError('interrupted')))
    with pytest.raises(OSError): recovery.reconnect_workspace(root, workspace, local, 'test-family')
    monkeypatch.setattr(Path, 'rename', original)
    (workspace / 'Companies/Lohn_Test/result.pdf').write_bytes(b'NEWER-SYNTHETIC')
    with pytest.raises(storage.StorageError, match='geändert'):
        initialize(root, workspace, local, Mock())
    assert not (root / 'storage-layout.json').exists()


def test_existing_package_settings_are_not_overwritten(tmp_path):
    root, workspace, local = setup(tmp_path)
    storage.atomic_json(root / 'Data/Settings/license.json', {'key': 'different'})
    with pytest.raises(storage.StorageError, match='Programmeinstellungen'):
        recovery.reconnect_workspace(root, workspace, local, 'test-family')
    assert json.loads((root / 'Data/Settings/license.json').read_text()) == {'key': 'different'}
    assert not (root / 'storage-layout.json').exists()
    assert not (root / 'workspace-reconnect.json').exists()


def test_saved_custom_output_and_workflow_identity_survive(tmp_path):
    root, workspace, local = setup(tmp_path)
    custom = tmp_path / 'CustomResults'
    storage.atomic_json(workspace / 'Settings/settings.json', {
        'companies': [{'id': 'saved-id', 'name': 'Test', 'output_dir': str(custom)}]})
    storage.atomic_json(workspace / 'History/workflow_sessions.json', {'workflow-only-id': {'shipping_rows': []}})
    recovery.reconnect_workspace(root, workspace, local, 'test-family')
    companies = json.loads((root / 'Data/Settings/settings.json').read_text())['companies']
    assert companies[0]['output_dir'] == str(custom)
    assert companies[1]['id'] == 'workflow-only-id'


def test_invalid_new_path_can_be_corrected(tmp_path):
    root, workspace, local = setup(tmp_path)
    fresh = tmp_path / 'Other'; fresh.mkdir()
    before = storage.inventory(workspace)
    decisions = Mock(side_effect=[('new', local / 'wrong'), ('new', fresh)])
    layout = initialize(root, workspace, local, decisions)
    assert layout['workspace'] == str(fresh)
    assert decisions.call_args_list[1].args[0] == workspace
    assert decisions.call_args_list[1].args[1]
    assert storage.inventory(workspace) == before


@pytest.mark.parametrize('mode', ['duplicate-id', 'ambiguous-folder'])
def test_ambiguous_company_mapping_never_guesses(tmp_path, mode):
    root, workspace, local = setup(tmp_path)
    storage.atomic_json(workspace / 'Settings/settings.json', {'companies': [
        {'id': 'a', 'name': 'Test'}, {'id': 'a' if mode == 'duplicate-id' else 'b', 'name': 'Test'}]})
    with pytest.raises(storage.StorageError):
        recovery.reconnect_workspace(root, workspace, local, 'test-family')
    assert not (root / 'Data').exists()
    assert not (root / 'storage-layout.json').exists()

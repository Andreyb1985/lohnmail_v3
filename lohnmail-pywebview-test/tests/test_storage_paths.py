import json
from pathlib import Path
import sqlite3
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from core import storage_paths as storage
from core import config
import pywebview_app as app
from ui_web import bridge


def put(root, name, text='synthetic'):
    path=root/name
    if path.suffix == '.json' and text == 'synthetic': text = '{}'
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(text)
    return path


@pytest.mark.parametrize('case', ['empty','ordinary','virtual','both'])
def test_migrate_cases(tmp_path,case):
    normal,virtual=tmp_path/'LohnMail',tmp_path/'Packages/p/LocalCache/Local/LohnMail'
    if case in ('ordinary','both'): put(normal,'Companies/Ordinary/a.pdf')
    if case in ('virtual','both'):
        put(virtual,'Settings/license.json','{"key":"TEST"}')
        put(virtual,'Companies/Virtual/a.xlsx')
        db=sqlite3.connect(virtual/'Settings/history.sqlite3')
        db.execute('create table history(x)')
        db.execute('insert into history values(42)')
        db.commit(); db.close()
    expected={**storage.inventory(normal),**storage.inventory(virtual)}
    storage.migrate_storage(normal,virtual)
    assert storage.inventory(normal)==expected
    storage.migrate_storage(normal,virtual)
    assert storage.inventory(normal)==expected
    if case in ('virtual','both'):
        assert (virtual/'Settings/license.json').exists()
        assert list(tmp_path.glob('LohnMail-storage-backup-*/redirected/Settings/license.json'))


def test_conflict_preserves_and_backs_up_both(tmp_path):
    a,b=tmp_path/'LohnMail',tmp_path/'legacy'
    put(a,'Settings/settings.json','one'); put(b,'Settings/settings.json','two')
    with pytest.raises(storage.StorageError,match='Unterschiedliche'):
        storage.migrate_storage(a,b)
    assert (a/'Settings/settings.json').read_text()=='one'
    assert (b/'Settings/settings.json').read_text()=='two'
    assert list(tmp_path.glob('LohnMail-storage-backup-*/conflicts.json'))


def test_resume_after_original_rename(tmp_path,monkeypatch):
    a,b=tmp_path/'LohnMail',tmp_path/'legacy'
    put(a,'Companies/a'); put(b,'Settings/license.json')
    rename=Path.rename
    def interrupt(self,target):
        if self.name=='staged': raise OSError('power interruption')
        return rename(self,target)
    monkeypatch.setattr(Path,'rename',interrupt)
    with pytest.raises(OSError): storage.migrate_storage(a,b)
    assert not a.exists()
    monkeypatch.setattr(Path,'rename',rename)
    storage.migrate_storage(a,b)
    assert (a/'Companies/a').exists() and (a/'Settings/license.json').exists()


def test_failed_backup_does_not_switch(tmp_path,monkeypatch):
    a,b=tmp_path/'LohnMail',tmp_path/'legacy'
    put(b,'Settings/license.json')
    monkeypatch.setattr(storage.shutil,'copytree',Mock(side_effect=OSError('full disk')))
    with pytest.raises(OSError): storage.migrate_storage(a,b)
    assert not a.exists() and (b/'Settings/license.json').exists()


def test_root_symlink_rejected(tmp_path):
    target = tmp_path / 'target'
    target.mkdir()
    link = tmp_path / 'link'
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(storage.StorageError): storage.inventory(link)


def test_sidecars_must_not_be_merged(tmp_path):
    a, b = tmp_path/'LohnMail', tmp_path/'legacy'
    put(a, 'Settings/history.sqlite3', 'same-db')
    put(b, 'Settings/history.sqlite3', 'same-db')
    put(b, 'Settings/history.sqlite3-wal', 'other-snapshot')
    with pytest.raises(storage.StorageError): storage.migrate_storage(a, b)
    assert not (a/'Settings/history.sqlite3-wal').exists()


def test_output_roundtrip_and_processing(tmp_path, monkeypatch):
    from core import jobs
    monkeypatch.setattr(config, 'ensure_default_config', lambda: None)
    monkeypatch.setattr(config, 'SETTINGS_PATH', tmp_path/'settings.json')
    monkeypatch.setattr(config, '_protect_and_strip_smtp_passwords', lambda value: value)
    monkeypatch.setattr(config, '_hydrate_smtp_passwords', lambda value: value)
    settings = config.build_default_settings()
    settings.update(companies=[{'id':'a', 'name':'A', 'output_dir':str(tmp_path/'chosen')}], selected_company_id='a')
    config.save_settings(settings)
    restored = config.load_settings()
    check = Mock(return_value={})
    monkeypatch.setattr(jobs, 'action_check', check)
    jobs.run_main_job('check', Path('synthetic.pdf'), Path('synthetic.xlsx'), restored, True)
    assert check.call_args.kwargs['output_dir'] == tmp_path/'chosen'


def test_atomic_settings_write_failure_preserves_file(tmp_path, monkeypatch):
    path = put(tmp_path, 'settings.json', '{"previous":true}')
    monkeypatch.setattr(storage.os, 'replace', Mock(side_effect=OSError('disk failure')))
    with pytest.raises(OSError): storage.atomic_json(path, {'new':True})
    assert json.loads(path.read_text()) == {'previous':True}


def test_package_identity_drives_storage_not_hardcoded_pfn(tmp_path, monkeypatch):
    from core import windows_storage
    package, local = tmp_path/'installed', tmp_path/'AppData/Local'
    state, cache = tmp_path/'package-state', tmp_path/'package-cache'
    workspace = tmp_path/'user-workspace'; workspace.mkdir()
    monkeypatch.setattr(storage, '_package_root', None)
    monkeypatch.setattr(storage, '_workspace_root', None)
    monkeypatch.setattr(storage, 'package_identity', lambda: ('Example.Custom_publisher', package))
    monkeypatch.setattr(storage, 'real_local_appdata', lambda: local)
    folders = Mock(return_value=(state, cache))
    monkeypatch.setattr(windows_storage, 'application_folders', folders)
    monkeypatch.setattr(windows_storage, 'default_workspace', lambda: workspace)
    monkeypatch.setitem(sys.modules, 'msvcrt', SimpleNamespace(locking=Mock(), LK_NBLCK=1, LK_UNLCK=0))
    assert storage.packaged_data_root() == state/'LohnMail/Data'
    assert storage._workspace_root == workspace
    folders.assert_called_once_with('Example.Custom_publisher')
    assert not (local/'LohnMail').exists()


def test_api_failure_never_falls_back_to_virtualized_path(tmp_path, monkeypatch):
    from core import windows_storage
    monkeypatch.setattr(storage, '_package_root', None)
    monkeypatch.setattr(storage, 'package_identity', lambda: ('test', tmp_path))
    monkeypatch.setattr(windows_storage, 'application_folders', Mock(side_effect=OSError('API unavailable')))
    lookup = Mock()
    monkeypatch.setattr(storage, 'real_local_appdata', lookup)
    with pytest.raises(OSError): storage.packaged_data_root()
    lookup.assert_not_called()


def export_fixture(workspace, sources, family='test'):
    bundle = workspace/'LohnMail-Legacy-Export'
    manifest = {'format':1, 'family':family, 'complete':True, 'sources':{}}
    for label, source in sources.items():
        (bundle/label).mkdir(parents=True)
        if source.exists(): storage.shutil.copytree(source, bundle/label, dirs_exist_ok=True)
        manifest['sources'][label] = {'path':str(source), 'files':storage.inventory(bundle/label)}
    storage.atomic_json(bundle/'export.json', manifest)
    return bundle


@pytest.mark.parametrize('case', ['clean', 'ordinary', 'redirected', 'both'])
def test_new_package_layout_and_restart(tmp_path, case):
    local, cache = tmp_path/'AppData/Local', tmp_path/'AppData/Local/Packages/test/LocalCache'
    root = tmp_path/'AppData/Local/Packages/test/LocalState/LohnMail'; root.mkdir(parents=True)
    workspace = tmp_path/'Documents/workspace'; workspace.mkdir(parents=True)
    ordinary, redirected = local/'LohnMail', cache/'Local/LohnMail'
    if case in ('ordinary', 'both'): put(ordinary, 'Companies/A/report.pdf')
    if case in ('redirected', 'both'): put(redirected, 'Companies/B/audit_check.xlsx')
    if case != 'clean':
        source = ordinary if case == 'ordinary' else redirected
        put(source, 'Settings/license.json', '{"license_key":"SYNTHETIC"}')
        put(source, 'Settings/secrets.dat', 'encrypted-synthetic')
        put(source, 'Settings/settings.json', json.dumps({'companies':[{'id':'x', 'output_dir':str(source/'Companies/A')}]}))
        export_fixture(workspace, {'ordinary':ordinary, 'redirected':redirected})
    before = (storage.inventory(ordinary), storage.inventory(redirected))
    layout = storage.initialize_package_storage(root, cache, local, 'test', lambda: workspace)
    assert Path(layout['state']) == root/'Data'
    assert Path(layout['workspace']) == workspace
    assert (workspace/'Companies').is_dir() and (workspace/'History').is_dir()
    assert not (root/'Data/Companies').exists()
    if case != 'clean':
        settings = json.loads((root/'Data/Settings/settings.json').read_text())
        assert settings['companies'][0]['output_dir'] == str(workspace/'Companies/A')
        assert (root/'Data/Settings/secrets.dat').read_text() == 'encrypted-synthetic'
        assert json.loads((root/'Data/Settings/license.json').read_text())['license_key']=='SYNTHETIC'
    assert before == (storage.inventory(ordinary), storage.inventory(redirected))
    choose = Mock(side_effect=AssertionError('must not prompt twice'))
    assert storage.initialize_package_storage(root, cache, local, 'test', choose) == layout


def test_legacy_requires_unvirtualized_export_before_any_new_license(tmp_path):
    root, cache, local = tmp_path/'state', tmp_path/'cache', tmp_path/'AppData/Local'
    root.mkdir(); workspace = tmp_path/'workspace'; workspace.mkdir()
    put(cache/'Local/LohnMail', 'Settings/license.json', '{"license_key":"TEST"}')
    with pytest.raises(storage.StorageError, match='Export-LegacyStorage'):
        storage.initialize_package_storage(root, cache, local, 'test', lambda: workspace)
    assert not (root/'Data').exists() and not (root/'storage-layout.json').exists()


def test_new_migration_resume_between_two_destinations(tmp_path, monkeypatch):
    root, local, cache = tmp_path/'state', tmp_path/'AppData/Local', tmp_path/'cache'
    root.mkdir(); workspace = tmp_path/'workspace'; workspace.mkdir()
    rename = Path.rename
    def fail(self, target):
        if Path(target) == workspace/'Companies': raise OSError('interrupted')
        return rename(self, target)
    monkeypatch.setattr(Path, 'rename', fail)
    with pytest.raises(OSError): storage.initialize_package_storage(root, cache, local, 'test', lambda: workspace)
    assert (root/'Data').exists() and not (root/'storage-layout.json').exists()
    monkeypatch.setattr(Path, 'rename', rename)
    layout = storage.initialize_package_storage(root, cache, local, 'test', Mock(side_effect=AssertionError()))
    assert Path(layout['workspace']) == workspace


def test_interrupted_unicode_workspace_with_windows_legacy_encoding(tmp_path, monkeypatch):
    root, local, cache = tmp_path/'state', tmp_path/'AppData/Local', tmp_path/'cache'
    root.mkdir()
    workspace = tmp_path/'Büro Андрей'; workspace.mkdir()
    read_text, rename = Path.read_text, Path.rename
    def legacy_read(self, encoding=None, errors=None):
        return read_text(self, encoding=encoding or 'cp1252', errors=errors)
    def interrupt(self, target):
        if Path(target) == workspace/'Companies':
            raise OSError('interrupted')
        return rename(self, target)
    monkeypatch.setattr(Path, 'read_text', legacy_read)
    monkeypatch.setattr(Path, 'rename', interrupt)
    with pytest.raises(OSError):
        storage.initialize_package_storage(root, cache, local, 'test', lambda: workspace)
    monkeypatch.setattr(Path, 'rename', rename)
    layout = storage.initialize_package_storage(root, cache, local, 'test', Mock())
    assert Path(layout['workspace']) == workspace
    assert (workspace/'Companies').is_dir()
    assert storage.initialize_package_storage(root, cache, local, 'test', Mock()) == layout


def test_missing_workspace_never_recreated(tmp_path):
    root, local, cache = tmp_path/'state', tmp_path/'AppData/Local', tmp_path/'cache'
    root.mkdir(); workspace = tmp_path/'workspace'; workspace.mkdir()
    storage.initialize_package_storage(root, cache, local, 'test', lambda: workspace)
    workspace.rename(tmp_path/'moved')
    with pytest.raises(storage.StorageError, match='Arbeitsordner fehlt'):
        storage.initialize_package_storage(root, cache, local, 'test', Mock())
    assert not workspace.exists()


def test_conflicting_exports_block_switch(tmp_path):
    root, local, cache = tmp_path/'state', tmp_path/'AppData/Local', tmp_path/'cache'
    root.mkdir(); workspace = tmp_path/'workspace'; workspace.mkdir()
    a, b = local/'LohnMail', cache/'Local/LohnMail'
    put(a, 'Settings/license.json', '{"key":"A"}')
    put(b, 'Settings/license.json', '{"key":"B"}')
    export_fixture(workspace, {'ordinary':a, 'redirected':b})
    with pytest.raises(storage.StorageError, match='Unterschiedliche'):
        storage.initialize_package_storage(root, cache, local, 'test', lambda:workspace)
    assert not (root/'Data').exists()
    assert list(workspace.glob('.lohnmail-transfer-*/LohnMail-storage-backup-*/conflicts.json'))


def test_history_moves_and_relinks_only_in_copy(tmp_path):
    root, local, cache = tmp_path/'state', tmp_path/'AppData/Local', tmp_path/'cache'
    root.mkdir(); workspace = tmp_path/'workspace'; workspace.mkdir()
    a, b = local/'LohnMail', cache/'Local/LohnMail'
    settings = a/'Settings'; settings.mkdir(parents=True)
    old = str(a/'Companies/A/audit_check.xlsx')
    put(a, 'Settings/workflow_sessions.json', json.dumps({'a':{'output_dir':str(a/'Companies/A')}}))
    with storage.closing(sqlite3.connect(settings/'lohnmail_history.sqlite3')) as db:
        db.execute('create table reports(path text, metadata text)')
        db.execute('insert into reports values(?,?)', (old, json.dumps({'path':old}))); db.commit()
    original = storage.inventory(a)
    export_fixture(workspace, {'ordinary':a, 'redirected':b})
    storage.initialize_package_storage(root, cache, local, 'test', lambda:workspace)
    with storage.closing(sqlite3.connect(workspace/'History/lohnmail_history.sqlite3')) as db:
        row = db.execute('select * from reports').fetchone()
    assert row[0] == str(workspace/'Companies/A/audit_check.xlsx')
    assert json.loads(row[1])['path'] == row[0]
    assert storage.inventory(a) == original
    assert not (root/'Data/Settings/lohnmail_history.sqlite3').exists()


def test_package_rejects_appdata_workspace_and_cancel(tmp_path):
    local = tmp_path/'AppData/Local'; local.mkdir(parents=True)
    with pytest.raises(storage.StorageError): storage.validate_workspace(local, local)
    root = tmp_path/'state'; root.mkdir()
    with pytest.raises(storage.StorageError, match='abgebrochen'):
        storage.initialize_package_storage(root, tmp_path/'cache', local, 'test', lambda:None)
    assert not list(root.iterdir())


def test_export_tampering_stops_before_switch(tmp_path):
    root, local, cache = tmp_path/'state', tmp_path/'AppData/Local', tmp_path/'cache'
    root.mkdir(); workspace = tmp_path/'workspace'; workspace.mkdir()
    a, b = local/'LohnMail', cache/'Local/LohnMail'
    put(a, 'Settings/license.json', '{"key":"TEST"}')
    bundle = export_fixture(workspace, {'ordinary':a, 'redirected':b})
    put(bundle/'ordinary', 'Settings/license.json', '{"key":"changed"}')
    with pytest.raises(storage.StorageError, match='verändert'):
        storage.initialize_package_storage(root, cache, local, 'test', lambda:workspace)
    assert not (root/'storage-layout.json').exists() and not (root/'Data').exists()


def test_store_output_not_allowed_in_appdata(tmp_path, monkeypatch):
    put(tmp_path/'workspace', '.lohnmail-workspace.json')
    (tmp_path/'workspace/Companies').mkdir()
    (tmp_path/'workspace/History').mkdir()
    monkeypatch.setattr(storage, 'packaged_workspace_root', lambda: tmp_path/'workspace')
    monkeypatch.setattr(storage, 'real_local_appdata', lambda:tmp_path/'AppData/Local')
    with pytest.raises(storage.StorageError):
        storage.validate_output_location(tmp_path/'AppData/Local/old-output')
    assert storage.validate_output_location(tmp_path/'Documents/output') == tmp_path/'Documents/output'
    monkeypatch.setattr(storage, 'packaged_workspace_root', lambda:None)
    assert storage.validate_output_location(tmp_path/'AppData/Local/old-output') == tmp_path/'AppData/Local/old-output'


def test_windows_api_returns_both_package_folders(tmp_path, monkeypatch):
    from core.windows_storage import application_folders
    manager = Mock()
    manager.create_for_package_family.return_value = SimpleNamespace(
        local_folder=SimpleNamespace(path=str(tmp_path/'state')),
        local_cache_folder=SimpleNamespace(path=str(tmp_path/'cache')))
    monkeypatch.setitem(sys.modules, 'winrt.windows.management.core', SimpleNamespace(ApplicationDataManager=manager))
    assert application_folders('Synthetic.Family') == (tmp_path/'state', tmp_path/'cache')
    manager.create_for_package_family.assert_called_once_with('Synthetic.Family')


def test_default_workspace_uses_windows_documents_not_home_guess(tmp_path, monkeypatch):
    from core import windows_storage
    documents = tmp_path/'other-drive/Redirected Documents'
    lookup = Mock(return_value=documents)
    monkeypatch.setattr(windows_storage, 'known_folder', lookup)
    assert windows_storage.default_workspace() == documents/'LohnMail'
    assert (documents/'LohnMail').is_dir()
    lookup.assert_called_once_with('FDD39AD0-238F-46AF-ADB4-6C85480369C7')


def test_relink_preserves_arbitrary_documents(tmp_path):
    old = 'C:/Users/example/AppData/Local/LohnMail/Companies'
    raw = '{  "path": "' + old + '/A"  }'
    put(tmp_path, 'attachment.json', raw)
    put(tmp_path, 'lohnmail_reports_index.json', raw)
    storage._rewrite_snapshot_paths(tmp_path, [(old, tmp_path/'Companies')])
    assert (tmp_path/'attachment.json').read_text() == raw
    assert json.loads((tmp_path/'lohnmail_reports_index.json').read_text())['path'] == str(tmp_path/'Companies/A')


def test_unavailable_network_old_path_does_not_block_cancel(monkeypatch):
    settings = {'selected_company_id':'a','companies':[{'id':'a','output_dir':r'\\offline-server\share\missing'}]}
    monkeypatch.setattr(app, 'load_settings', lambda: settings)
    save = Mock(); monkeypatch.setattr(app, 'save_settings', save)
    adapter = app.ApiAdapter(Mock())
    adapter._bridge._workflow_running.return_value = False
    adapter._window = Mock()
    adapter._window.create_file_dialog.return_value = None
    old = settings['companies'][0]['output_dir']
    assert json.loads(adapter.chooseOutputFolder())['cancelled']
    assert adapter._window.create_file_dialog.call_args.kwargs['directory'] != old
    assert settings['companies'][0]['output_dir'] == old
    save.assert_not_called()


def test_output_selection_cancel_and_persist(tmp_path,monkeypatch):
    settings=config.build_default_settings()
    settings.update(companies=[{'id':'a','name':'A','output_dir':str(tmp_path/'missing')}],selected_company_id='a')
    monkeypatch.setattr(app,'load_settings',lambda:settings)
    saved=Mock(); monkeypatch.setattr(app,'save_settings',saved)
    adapter=app.ApiAdapter(Mock())
    adapter._bridge._workflow_running.return_value=False
    adapter._processing_payload_after_selection=Mock()
    adapter._window=Mock()
    adapter._window.create_file_dialog.return_value=None
    assert json.loads(adapter.chooseOutputFolder())['cancelled']
    saved.assert_not_called()
    adapter._window.create_file_dialog.return_value=[str(tmp_path)]
    assert json.loads(adapter.chooseOutputFolder())['ok']
    assert config.company_output_dir(config._deep_merge_settings(settings))==tmp_path
    assert adapter._window.create_file_dialog.call_args.kwargs['directory']!=str(tmp_path/'missing')
    saved.assert_called_once()


def test_output_unwritable_does_not_save(tmp_path,monkeypatch):
    settings={'selected_company_id':'a','companies':[{'id':'a','output_dir':'old'}]}
    monkeypatch.setattr(app,'load_settings',lambda:settings)
    saved=Mock(); monkeypatch.setattr(app,'save_settings',saved)
    monkeypatch.setattr(storage,'writable_directory',Mock(side_effect=PermissionError()))
    adapter=app.ApiAdapter(Mock()); adapter._bridge._workflow_running.return_value=False
    adapter._window=Mock(); adapter._window.create_file_dialog.return_value=[str(tmp_path)]
    assert not json.loads(adapter.chooseOutputFolder())['ok']
    assert settings['companies'][0]['output_dir']=='old'
    saved.assert_not_called()


def test_missing_open_does_not_create(tmp_path,monkeypatch):
    missing=tmp_path/'missing'
    monkeypatch.setattr(bridge,'load_settings',lambda:{})
    monkeypatch.setattr(bridge,'company_output_dir',lambda _:missing)
    result=json.loads(bridge.WebBridge.openOutputFolder(object()))
    assert not result['ok'] and result['action']=='choose-output'
    assert not missing.exists() and 'geöffnet' not in result['message']


def test_shell_failure_and_url_classification(tmp_path,monkeypatch):
    file=put(tmp_path,'a.pdf')
    monkeypatch.setattr(bridge.sys,'platform','win32')
    launch=Mock(side_effect=OSError('association missing'))
    monkeypatch.setattr(bridge.os,'startfile',launch,raising=False)
    browser=Mock(); monkeypatch.setattr(bridge.webbrowser,'open',browser)
    assert not bridge._open_target(file)
    launch.assert_called_once(); browser.assert_not_called()


def test_export_failure_reports_path(tmp_path,monkeypatch):
    monkeypatch.setattr(Path,'write_text',Mock(side_effect=PermissionError()))
    result=json.loads(bridge._write_export(tmp_path/'report.csv','test'))
    assert not result['ok'] and str(tmp_path) in result['message']

"""Native export orchestration: no real process, license or customer files."""
import json
import sys
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from core import windows_storage
from core.storage_paths import StorageError, atomic_json


@pytest.mark.parametrize('identity,complete,code', [(15700, True, 0), (122, True, 0), (15700, False, 0), (15700, True, 1)])
def test_helper_requires_completion_and_unpacked_identity(tmp_path, monkeypatch, identity, complete, code):
    app = tmp_path/'App'; app.mkdir()
    (app/'LohnMail.StorageExport.exe').write_bytes(b'synthetic executable')
    monkeypatch.setattr(sys, 'executable', str(app/'LohnMail.exe'))
    workspace = tmp_path/'Dokumente Büro Андрей'; workspace.mkdir()
    local, cache = tmp_path/'Local', tmp_path/'cache'
    def run(arguments, **options):
        assert options['creationflags'] == 0x08000000
        assert not options.get('shell')
        assert Path(arguments[0]).is_relative_to(workspace)
        request = json.loads(Path(arguments[1]).read_text(encoding='utf-8'))
        assert request['family'] == 'Example.Dynamic_publisher'
        assert request['local'] == str(local) and request['cache'] == str(cache)
        atomic_json(request['response'], {'identity_result':identity, 'complete':complete})
        return SimpleNamespace(returncode=code)
    monkeypatch.setattr(subprocess, 'run', run)
    if identity == 15700 and complete and code == 0:
        windows_storage.export_legacy_storage(workspace, 'Example.Dynamic_publisher', local, cache)
    else:
        with pytest.raises(StorageError, match='nichts umgeschaltet'):
            windows_storage.export_legacy_storage(workspace, 'Example.Dynamic_publisher', local, cache)


def test_missing_bundled_helper_cannot_fall_back(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, 'executable', str(tmp_path/'LohnMail.exe'))
    with pytest.raises(StorageError, match='Datensicherungsmodul fehlt'):
        windows_storage.export_legacy_storage(tmp_path, 'test', tmp_path, tmp_path)

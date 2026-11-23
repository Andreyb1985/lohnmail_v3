import json
import plistlib
import sys
from pathlib import Path

import pytest

from ui_web.version import APP_VERSION, APP_BUILD, app_metadata


@pytest.mark.parametrize('platform,frozen', [('win32', True), ('win32', False), ('darwin', False), ('linux', True)])
def test_source_and_windows_keep_canonical_metadata(monkeypatch, platform, frozen):
    monkeypatch.setattr(sys, 'platform', platform)
    monkeypatch.setattr(sys, 'frozen', frozen, raising=False)
    assert app_metadata() == {'version': APP_VERSION, 'build': APP_BUILD}


@pytest.mark.parametrize('payload', [
    {'CFBundleShortVersionString': '2.2.0', 'CFBundleVersion': '2026102203'},
    {}, [], {'CFBundleShortVersionString': 'bad', 'CFBundleVersion': '1'},
    {'CFBundleShortVersionString': '2.2.0', 'CFBundleVersion': 123},
    None, b'broken plist',
])
def test_macos_bundle_metadata_and_safe_fallback(monkeypatch, tmp_path, payload):
    contents = tmp_path / 'LohnMail.app' / 'Contents'
    contents.mkdir(parents=True)
    if payload is not None:
        (contents / 'Info.plist').write_bytes(payload if isinstance(payload, bytes) else plistlib.dumps(payload))
    monkeypatch.setattr(sys, 'platform', 'darwin')
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, 'executable', str(contents / 'MacOS' / 'LohnMail'))
    expected = {'version': '2.2.0', 'build': '2026102203'} if isinstance(payload, dict) and payload.get('CFBundleVersion') == '2026102203' else {'version': APP_VERSION, 'build': APP_BUILD}
    assert app_metadata() == expected


def test_bridge_and_pywebview_expose_same_metadata_without_initialization(monkeypatch):
    from ui_web import bridge
    from pywebview_app import ApiAdapter
    expected = {'version': '9.8.7', 'build': '2030010109'}
    monkeypatch.setattr(bridge, 'app_metadata', lambda: expected)
    # No WebBridge constructor: no settings, license service or network side effects.
    assert json.loads(bridge.WebBridge.getAppInfo(None)) == expected
    assert bridge.WebBridge.appVersion(None) == expected['version']
    assert bridge.WebBridge.appBuild(None) == expected['build']
    assert bridge._app_store_update_state()['installed_build'] == expected['build']
    class FakeBridge:
        def getAppInfo(self):
            return bridge.WebBridge.getAppInfo(None)
    assert json.loads(ApiAdapter(FakeBridge()).getAppInfo()) == expected


def test_version_labels_have_no_hardcoded_release():
    root = Path(__file__).resolve().parents[1]
    for relative in ('web/index.html', 'web/app.js'):
        text = (root / relative).read_text()
        assert '2.0.3' not in text
        assert '2026.09.01.3' not in text
    html = (root / 'web/index.html').read_text()
    assert 'data-app-version="sidebar"' in html
    assert 'data-app-version="about"' in html

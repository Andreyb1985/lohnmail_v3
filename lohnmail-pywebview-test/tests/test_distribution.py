from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from core import config
from core.distribution import DIRECT, STORE, get_distribution_channel
from ui_web.bridge import WebBridge, _store_update_state


def test_store_and_direct_updater_capabilities_remain_separate():
    from ui_web.bridge import _self_updates_supported
    with patch('ui_web.bridge.is_store_build', return_value=True):
        assert not _self_updates_supported('win32', True)
        assert not _self_updates_supported('win32', False)
    with patch('ui_web.bridge.is_store_build', return_value=False):
        assert _self_updates_supported('win32', True)
        assert _self_updates_supported('darwin', False)
        assert not _self_updates_supported('darwin', True)


def test_distribution_defaults_to_direct_without_marker() -> None:
    with TemporaryDirectory() as directory:
        marker = Path(directory) / "missing.json"
        assert get_distribution_channel({}, marker) == DIRECT


def test_store_ui_preserves_privacy_version_and_update_guards():
    root = Path(__file__).resolve().parents[1]
    html = (root / "web/index.html").read_text(encoding="utf-8")
    js = (root / "web/app.js").read_text(encoding="utf-8")
    assert 'data-about-action="privacy-website"' in html
    assert 'data-app-version' in html
    assert 'data-about="distribution"' in html
    assert "state.distribution_label" in js
    assert "openProductContact('privacy')" in js
    guard = "if (latestUpdateState.supported === false || latestUpdateState.distribution === 'store') return;"
    for name in ('dispatchUpdateAction', 'persistUpdatePreferences', 'maybeCheckForUpdates'):
        body = js.split('function ' + name + '(', 1)[1].split('\n  function ', 1)[0]
        assert guard in body
    with patch('ui_web.bridge._open_target', return_value=True) as opened:
        result = json.loads(object.__new__(WebBridge).openProductContact('privacy'))
        assert result['ok'] is True
        opened.assert_called_once_with('https://lohn-mail.de/datenschutz')


def test_distribution_reads_marker_and_environment_has_priority() -> None:
    with TemporaryDirectory() as directory:
        marker = Path(directory) / "channel.json"
        marker.write_text(json.dumps({"distribution": "store"}), encoding="utf-8")
        assert get_distribution_channel({}, marker) == STORE
        assert get_distribution_channel({"LOHNMAIL_DISTRIBUTION": "direct"}, marker) == DIRECT


@patch("ui_web.bridge.is_store_build", return_value=True)
def test_store_update_bridge_state_never_uses_update_service(_store) -> None:
    bridge = object.__new__(WebBridge)
    bridge._update_service = None

    assert json.loads(bridge.getUpdateState()) == _store_update_state()
    assert json.loads(bridge.checkForUpdates())["status"] == "disabled"
    assert json.loads(bridge.downloadUpdate())["supported"] is False
    assert json.loads(bridge.installUpdateOnExit())["distribution"] == "store"


def test_store_migration_copies_only_missing_settings_and_companies() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        legacy = root / "legacy"
        target = root / "target"
        (legacy / "Settings").mkdir(parents=True)
        (legacy / "Companies" / "alpha").mkdir(parents=True)
        (legacy / "Settings" / "settings.json").write_text("legacy", encoding="utf-8")
        (legacy / "Companies" / "alpha" / "report.txt").write_text("report", encoding="utf-8")
        (target / "Settings").mkdir(parents=True)
        (target / "Settings" / "settings.json").write_text("current", encoding="utf-8")

        with patch.object(config.sys, "platform", "win32"), patch.object(
            config, "is_store_build", return_value=True
        ), patch.object(config, "USER_DATA_DIR", target), patch.object(
            config, "SETTINGS_DIR", target / "Settings"
        ), patch.object(config, "COMPANIES_DIR", target / "Companies"):
            copied = config.migrate_windows_store_data(legacy)
            copied_again = config.migrate_windows_store_data(legacy)

        assert copied == 1
        assert copied_again == 0
        assert (target / "Settings" / "settings.json").read_text(encoding="utf-8") == "current"
        assert (target / "Companies" / "alpha" / "report.txt").read_text(encoding="utf-8") == "report"
        assert (target / "Settings" / ".store-migration-v1.json").is_file()

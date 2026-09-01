from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from core.license_manager import LicenseManager, LicenseNotFoundError


class LicenseOfflineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.license_dir = Path(self.temp_dir.name)
        self.license_path = self.license_dir / "license.json"
        self.patches = (
            patch("core.license_manager.LICENSE_DIR", self.license_dir),
            patch("core.license_manager.LICENSE_PATH", self.license_path),
        )
        for active_patch in self.patches:
            active_patch.start()
            self.addCleanup(active_patch.stop)
        machine_patch = patch.object(LicenseManager, "_current_machine_id", return_value="test-machine")
        machine_patch.start()
        self.addCleanup(machine_patch.stop)
        self.addCleanup(self.temp_dir.cleanup)
        self.manager = LicenseManager({})

    def write_state(self, **overrides) -> None:
        now = datetime.now(timezone.utc)
        state = {
            "license_key": "LM-TEST-OFFLINE",
            "status": "active",
            "type": "subscription",
            "machine_id": "test-machine",
            "last_successful_check_at": (now - timedelta(days=30)).isoformat(),
            "next_check_at": (now - timedelta(days=23)).isoformat(),
            "access_ends_at": (now + timedelta(days=14)).isoformat(),
        }
        state.update(overrides)
        self.license_path.write_text(json.dumps(state), encoding="utf-8")

    def test_active_cached_subscription_allows_processing_without_network(self) -> None:
        self.write_state()

        def unexpected_request(*args, **kwargs):
            raise AssertionError("An active cached entitlement must not make a request")

        with patch.object(self.manager, "_post", side_effect=unexpected_request):
            allowed, state = self.manager.require_action("processing")

        self.assertTrue(allowed)
        self.assertEqual(state["status"], "active")

    def test_failed_refresh_keeps_valid_cached_license_active(self) -> None:
        self.write_state()
        with patch.object(self.manager, "_post", side_effect=OSError("offline")):
            state = self.manager.refresh(force=True, start_trial=False)

        self.assertEqual(state["status"], "active")
        self.assertEqual(state["server"], "Nicht erreichbar")
        self.assertTrue(self.manager.require_action("processing")[0])

    def test_expired_cached_entitlement_is_not_allowed_offline(self) -> None:
        self.write_state(
            access_ends_at=(datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
        )
        with patch.object(self.manager, "_post", side_effect=OSError("offline")):
            allowed, state = self.manager.require_action("processing")

        self.assertFalse(allowed)
        self.assertEqual(state["status"], "no_connection")

    def test_blocked_cached_license_remains_blocked(self) -> None:
        self.write_state(status="revoked")

        allowed, state = self.manager.require_action("processing")

        self.assertFalse(allowed)
        self.assertEqual(state["status"], "revoked")

    def test_missing_server_license_starts_persistent_fourteen_day_grace(self) -> None:
        self.write_state()
        with patch.object(self.manager, "_post", side_effect=LicenseNotFoundError("License not found")):
            state = self.manager.refresh(force=True, start_trial=False)

        self.assertEqual(state["status"], "license_problem")
        self.assertEqual(state["server"], "Verbunden")
        self.assertIn("Lizenz nicht gefunden", state["last_message"])
        self.assertTrue(self.manager.require_action("processing")[0])
        first_end = state["license_problem_grace_ends_at"]

        with patch.object(self.manager, "_post", side_effect=LicenseNotFoundError("License not found")):
            repeated = self.manager.refresh(force=True, start_trial=False)
        self.assertEqual(repeated["license_problem_grace_ends_at"], first_end)

    def test_missing_license_is_blocked_after_transition_period(self) -> None:
        now = datetime.now(timezone.utc)
        self.write_state(
            status="license_problem",
            license_problem_started_at=(now - timedelta(days=15)).isoformat(),
            license_problem_grace_ends_at=(now - timedelta(days=1)).isoformat(),
        )

        allowed, state = self.manager.require_action("processing")

        self.assertFalse(allowed)
        self.assertEqual(state["status"], "invalid")
        self.assertIn("Übergangsfrist ist abgelaufen", state["last_message"])

    def test_legacy_license_files_are_copied_to_settings_directory(self) -> None:
        legacy_dir = self.license_dir / "legacy"
        target_dir = self.license_dir / "Settings"
        legacy_dir.mkdir()
        legacy_state = {"license_key": "LM-MIGRATED", "status": "active", "machine_id": "legacy-machine"}
        (legacy_dir / "license.json").write_text(json.dumps(legacy_state), encoding="utf-8")
        (legacy_dir / "machine_id").write_text("legacy-machine", encoding="utf-8")

        with (
            patch("core.license_manager.LEGACY_LICENSE_DIR", legacy_dir),
            patch("core.license_manager.DEFAULT_LICENSE_DIR", target_dir),
            patch("core.license_manager.LICENSE_DIR", target_dir),
            patch("core.license_manager.LICENSE_PATH", target_dir / "license.json"),
            patch.object(LicenseManager, "_current_machine_id", return_value="legacy-machine"),
        ):
            state = LicenseManager({}).load_state()

        self.assertEqual(state["license_key"], "LM-MIGRATED")
        self.assertEqual((target_dir / "machine_id").read_text(encoding="utf-8"), "legacy-machine")
        self.assertTrue((legacy_dir / "license.json").exists())

    def test_fresh_install_uses_same_machine_id_in_different_install_folders(self) -> None:
        first_dir = self.license_dir / "first-copy"
        second_dir = self.license_dir / "second-copy"
        with patch.object(LicenseManager, "_hardware_seed", return_value="windows:stable-machine-guid"):
            with patch("core.license_manager.LICENSE_DIR", first_dir):
                first_id = LicenseManager({}).machine_id()
            with patch("core.license_manager.LICENSE_DIR", second_dir):
                second_id = LicenseManager({}).machine_id()

        self.assertEqual(first_id, second_id)

    def test_copied_license_is_blocked_on_a_different_computer(self) -> None:
        self.write_state(machine_id="already-activated-machine")

        state = self.manager.load_state()

        self.assertEqual(state["status"], "device_mismatch")
        self.assertEqual(state["machine_id"], "test-machine")
        self.assertEqual(state["licensed_machine_id"], "already-activated-machine")
        self.assertIn("anderen Computer", state["last_message"])
        self.assertFalse(self.manager.require_action("processing")[0])

    def test_machine_file_is_rechecked_against_hardware_on_every_start(self) -> None:
        (self.license_dir / "machine_id").write_text("copied-machine", encoding="utf-8")

        machine_id = self.manager.machine_id()

        self.assertEqual(machine_id, "test-machine")
        self.assertEqual((self.license_dir / "machine_id").read_text(encoding="utf-8"), "test-machine")


if __name__ == "__main__":
    unittest.main()

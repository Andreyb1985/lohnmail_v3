from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from core.license_manager import LicenseManager


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


if __name__ == "__main__":
    unittest.main()

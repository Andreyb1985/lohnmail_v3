from __future__ import annotations

import tempfile
import unittest
import os
from pathlib import Path
from unittest.mock import patch

from core.config import build_default_settings
from ui_web.bridge import WebBridge
from ui_web.workflow_sessions import WorkflowSessionStore


class WorkflowSessionTests(unittest.TestCase):
    def test_store_keeps_independent_company_sessions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = WorkflowSessionStore(Path(temp_dir) / "sessions.json")
            store.save("alpha", {"step": "validation"})
            store.save("beta", {"step": "shipping"})
            self.assertEqual(store.load("alpha")["step"], "validation")
            self.assertEqual(store.load("beta")["step"], "shipping")
            store.delete("alpha")
            self.assertEqual(store.load("alpha"), {})
            self.assertEqual(store.load("beta")["step"], "shipping")

    def test_store_retries_windows_permission_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = WorkflowSessionStore(Path(temp_dir) / "sessions.json")
            real_replace = os.replace
            calls = 0

            def temporarily_blocked(source, target):
                nonlocal calls
                calls += 1
                if calls < 3:
                    raise PermissionError(5, "Access denied")
                return real_replace(source, target)

            with patch("ui_web.workflow_sessions.os.replace", side_effect=temporarily_blocked), patch(
                "ui_web.workflow_sessions.time.sleep"
            ):
                store.save("alpha", {"step": "validation"})

            self.assertEqual(calls, 3)
            self.assertEqual(store.load("alpha")["step"], "validation")

    def test_store_does_not_crash_when_windows_keeps_file_locked(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = WorkflowSessionStore(Path(temp_dir) / "sessions.json")
            with patch("ui_web.workflow_sessions.os.replace", side_effect=PermissionError(5, "Access denied")), patch(
                "ui_web.workflow_sessions.time.sleep"
            ):
                store.save("alpha", {"step": "validation"})

            self.assertEqual(store.load("alpha"), {})
            self.assertEqual(list(Path(temp_dir).glob("*.tmp")), [])

    def test_bridge_restores_finished_validation_for_selected_company(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = WorkflowSessionStore(Path(temp_dir) / "sessions.json")
            settings = build_default_settings()
            settings["companies"] = [{"id": "alpha", "name": "Alpha", "email_excel_file": ""}]
            settings["selected_company_id"] = "alpha"
            with patch("ui_web.bridge.load_settings", side_effect=lambda: settings), patch(
                "ui_web.bridge.WorkflowSessionStore", return_value=store
            ):
                first = WebBridge()
                signature = first._input_signature(settings)
                first._processing_company_id = "alpha"
                first._processing_input_signature = signature
                first._processing_status.update(finished=True, progress=100, current_step="Prüfung abgeschlossen")
                first._validation_company_id = "alpha"
                first._validation_input_signature = signature
                first._validation_state.update(ready=True, rows=[{"PersNr": "1", "Status": "OK"}])
                first._persist_workflow_session(settings)

                restored = WebBridge()

            self.assertTrue(restored._processing_status["finished"])
            self.assertEqual(restored._processing_status["progress"], 100)
            self.assertTrue(restored._validation_state["ready"])
            self.assertEqual(restored._validation_state["rows"][0]["PersNr"], "1")

    def test_interrupted_run_restores_as_resumable_not_running(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = WorkflowSessionStore(Path(temp_dir) / "sessions.json")
            settings = build_default_settings()
            settings["companies"] = [{"id": "alpha", "name": "Alpha", "email_excel_file": ""}]
            settings["selected_company_id"] = "alpha"
            signature = ("alpha", "folder", "", "")
            store.save(
                "alpha",
                {
                    "processing_company_id": "alpha",
                    "processing_input_signature": list(signature),
                    "processing_status": {"running": True, "progress": 42},
                },
            )
            with patch("ui_web.bridge.load_settings", side_effect=lambda: settings), patch(
                "ui_web.bridge.WorkflowSessionStore", return_value=store
            ):
                bridge = WebBridge()

            self.assertFalse(bridge._processing_running)
            self.assertFalse(bridge._processing_status["running"])
            self.assertTrue(bridge._processing_status["can_check"])
            self.assertIn("unterbrochen", bridge._processing_status["message"].lower())


if __name__ == "__main__":
    unittest.main()

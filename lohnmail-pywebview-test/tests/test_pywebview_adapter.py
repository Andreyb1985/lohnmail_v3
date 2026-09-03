from __future__ import annotations

import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from pywebview_app import ApiAdapter
from core.config import build_default_settings
from ui_web.bridge import WebBridge
from ui_web.bridge_compat import Signal
from ui_web.workflow_sessions import WorkflowSessionStore


class FakeWindow:
    def __init__(self, selection: tuple[str, ...] | None = None, prompt: str | None = None) -> None:
        self.selection = selection
        self.prompt = prompt
        self.dialog_calls: list[tuple[tuple, dict]] = []

    def create_file_dialog(self, *args, **kwargs):
        self.dialog_calls.append((args, kwargs))
        return self.selection

    def evaluate_js(self, _script: str):
        return self.prompt


class FakeBridge:
    processingStateChanged = Signal(str)
    shippingStateChanged = Signal(str)

    def __init__(self) -> None:
        self.reset_count = 0
        self.company_excel = ""

    def _workflow_running(self):
        return False

    def _pdf_input_mode(self, settings):
        return settings.get("ui", {}).get("last_pdf_input_mode", "folder")

    def _dialog_start_path(self, value):
        return value

    def _reset_workflow_state(self):
        self.reset_count += 1

    def _set_company_excel_file(self, settings, value):
        self.company_excel = value

    def _set_company_pdf_input(self, settings, value, mode):
        settings.setdefault("company_pdf", {})["path"] = value
        settings["company_pdf"]["mode"] = mode

    def _processing_payload(self, settings):
        return {"pdf": settings.get("ui", {}).get("last_pdf_dir", ""), "excel": self.company_excel}

    def _shipping_payload(self, _settings):
        return {"ok": True}

    def _company_payload(self, settings):
        return {
            "selected_company_id": settings.get("selected_company_id", "test"),
            "companies": settings.get("companies", [{"id": "test", "name": "Test"}]),
            "selected_excel": {"path": self.company_excel, "valid": bool(self.company_excel)},
        }


class PywebviewAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self._session_temp = tempfile.TemporaryDirectory()
        session_path = Path(self._session_temp.name) / "workflow_sessions.json"
        self._session_patcher = patch(
            "ui_web.bridge.WorkflowSessionStore",
            side_effect=lambda _path: WorkflowSessionStore(session_path),
        )
        self._session_patcher.start()

    def tearDown(self) -> None:
        self._session_patcher.stop()
        self._session_temp.cleanup()

    def test_runtime_bridge_has_no_qt_imports(self) -> None:
        root = Path(__file__).resolve().parents[1]
        for relative in ("pywebview_app.py", "ui_web/bridge.py", "ui_web/bridge_compat.py"):
            text = (root / relative).read_text(encoding="utf-8")
            self.assertNotIn("PySide6", text, relative)
            self.assertNotIn("QFileDialog", text, relative)
            self.assertNotIn("QThread", text, relative)

    def test_all_webbridge_public_methods_are_exposed(self) -> None:
        missing = [
            name
            for name, member in WebBridge.__dict__.items()
            if callable(member) and not name.startswith("_") and not hasattr(ApiAdapter, name)
        ]
        self.assertEqual(missing, [])

    def test_folder_selection_is_saved_and_emitted(self) -> None:
        bridge = FakeBridge()
        adapter = ApiAdapter(bridge)  # type: ignore[arg-type]
        selected = str(Path(tempfile.gettempdir()) / "pdfs")
        adapter.attach_window(FakeWindow((selected,)))  # type: ignore[arg-type]
        settings = {"ui": {"last_pdf_dir": "", "last_pdf_input_mode": "folder"}}
        saved = []
        with patch("pywebview_app.load_settings", side_effect=lambda: settings), patch(
            "pywebview_app.save_settings", side_effect=lambda value: saved.append(value.copy())
        ):
            payload = json.loads(adapter.choosePdfInput())
        self.assertEqual(payload["pdf"], selected)
        self.assertEqual(settings["ui"]["last_pdf_dialog_dir"], selected)
        self.assertEqual(bridge.reset_count, 1)
        self.assertEqual(len(saved), 1)

    def test_cancelled_selection_does_not_reset_workflow(self) -> None:
        bridge = FakeBridge()
        adapter = ApiAdapter(bridge)  # type: ignore[arg-type]
        adapter.attach_window(FakeWindow(None))  # type: ignore[arg-type]
        settings = {"ui": {"last_pdf_dir": "", "last_pdf_input_mode": "folder"}}
        with patch("pywebview_app.load_settings", side_effect=lambda: settings):
            adapter.choosePdfInput()
        self.assertEqual(bridge.reset_count, 0)

    def test_company_excel_uses_native_dialog_override(self) -> None:
        bridge = FakeBridge()
        adapter = ApiAdapter(bridge)  # type: ignore[arg-type]
        selected = str(Path(tempfile.gettempdir()) / "employees.xlsx")
        adapter.attach_window(FakeWindow((selected,)))  # type: ignore[arg-type]
        settings = {
            "ui": {"last_excel_file": ""},
            "selected_company_id": "test",
            "companies": [{"id": "test", "name": "Test"}],
        }
        with patch("pywebview_app.load_settings", side_effect=lambda: settings), patch(
            "pywebview_app.save_settings"
        ), patch("pywebview_app.get_company_email_excel_file", return_value=""):
            payload = json.loads(adapter.chooseCompanyExcelInput())
        self.assertEqual(payload["selected_excel"]["path"], selected)
        self.assertEqual(settings["ui"]["last_excel_dialog_dir"], str(Path(selected).parent))
        self.assertEqual(payload["companies"], [{"id": "test", "name": "Test"}])
        self.assertEqual(bridge.reset_count, 1)

    def test_file_dialog_reuses_last_selected_directories(self) -> None:
        bridge = FakeBridge()
        adapter = ApiAdapter(bridge)  # type: ignore[arg-type]
        window = FakeWindow(("/next/employees.xlsx",))
        adapter.attach_window(window)  # type: ignore[arg-type]
        settings = {
            "ui": {
                "last_excel_file": "/old/company.xlsx",
                "last_excel_dialog_dir": "/remembered/imports",
            }
        }
        with patch("pywebview_app.load_settings", side_effect=lambda: settings), patch(
            "pywebview_app.save_settings"
        ):
            adapter.chooseExcelInput()
        self.assertEqual(window.dialog_calls[0][1]["directory"], "/remembered/imports")

    def test_empty_dialog_path_defaults_to_program_directory(self) -> None:
        base_dir = Path(tempfile.gettempdir()) / "portable" / "LohnMail" / "App"
        with patch("ui_web.bridge.BASE_DIR", base_dir):
            self.assertEqual(WebBridge._dialog_start_path(""), str(base_dir.parent))

    def test_company_switch_clears_previous_company_files(self) -> None:
        settings = build_default_settings()
        settings["companies"] = [
            {"id": "first", "name": "First", "email_excel_file": "/tmp/first.xlsx"},
            {"id": "second", "name": "Second", "email_excel_file": "", "pdf_input": "", "pdf_input_mode": "folder"},
        ]
        settings["selected_company_id"] = "first"
        settings["ui"]["last_pdf_dir"] = "/tmp/first-pdfs"
        settings["ui"]["last_pdf_input_mode"] = "folder"
        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "ui_web.bridge.load_settings", side_effect=lambda: settings
        ), patch("ui_web.bridge.save_settings"), patch(
            "ui_web.bridge.company_output_dir", return_value=Path(temp_dir) / "output"
        ):
            bridge = WebBridge()
            result = json.loads(bridge.selectCompany("second"))

        self.assertTrue(result["ok"])
        self.assertEqual(settings["companies"][0]["pdf_input"], "/tmp/first-pdfs")
        self.assertEqual(settings["ui"]["last_pdf_dir"], "")
        self.assertEqual(settings["ui"]["last_pdf_input_mode"], "folder")
        self.assertEqual(result["selected_excel"]["path"], "")

    def test_processing_thread_reaches_finished_without_qt_event_loop(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pdf_path = root / "journal.pdf"
            excel_path = root / "employees.xlsx"
            pdf_path.write_bytes(b"test")
            excel_path.write_bytes(b"test")
            settings = build_default_settings()
            settings["companies"] = [{"id": "test", "name": "Test", "email_excel_file": str(excel_path)}]
            settings["selected_company_id"] = "test"
            settings["ui"]["last_pdf_input_mode"] = "single_pdf"
            settings["ui"]["last_pdf_dir"] = str(pdf_path)
            finished = threading.Event()

            with patch("ui_web.bridge.load_settings", side_effect=lambda: settings), patch(
                "ui_web.bridge.LicenseManager.require_action", return_value=(True, {})
            ), patch(
                "ui_web.bridge.company_output_dir", return_value=root / "output"
            ), patch(
                "core.jobs.run_main_job",
                return_value={"summary": {}, "table_rows": []},
            ):
                bridge = WebBridge()
                bridge._register_result_reports = lambda *_args, **_kwargs: None  # type: ignore[method-assign]
                bridge.processingFinished.connect(lambda _payload: finished.set())
                json.loads(bridge.startCheck())
                self.assertTrue(finished.wait(2), "processing thread did not finish")
                final = json.loads(bridge.getProcessingState())

            self.assertFalse(final["status"]["running"])
            self.assertTrue(final["status"]["finished"])
            self.assertEqual(final["status"]["progress"], 100)

    def test_shipping_dry_run_reaches_finished_without_qt_event_loop(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pdf_path = root / "journal.pdf"
            excel_path = root / "employees.xlsx"
            pdf_path.write_bytes(b"test")
            excel_path.write_bytes(b"test")
            settings = build_default_settings()
            settings["companies"] = [{"id": "test", "name": "Test", "email_excel_file": str(excel_path)}]
            settings["selected_company_id"] = "test"
            settings["ui"]["last_pdf_input_mode"] = "single_pdf"
            settings["ui"]["last_pdf_dir"] = str(pdf_path)
            finished = threading.Event()

            with patch("ui_web.bridge.load_settings", side_effect=lambda: settings), patch(
                "ui_web.bridge.LicenseManager.require_action", return_value=(True, {})
            ), patch("ui_web.bridge.company_output_dir", return_value=root / "output"), patch(
                "core.jobs.run_main_job",
                return_value={
                    "summary": {"dry_run": True, "prepared_or_sent_count": 1},
                    "table_rows": [{"PersNr": "1", "Name": "Test", "Email": "test@example.de", "Status": "Bereit"}],
                },
            ):
                bridge = WebBridge()
                bridge._register_result_reports = lambda *_args, **_kwargs: None  # type: ignore[method-assign]
                bridge._validation_company_id = "test"
                bridge._validation_input_signature = bridge._input_signature(settings)
                bridge._validation_state = {"ready": True}
                bridge.shippingFinished.connect(lambda _payload: finished.set())
                json.loads(bridge.startShippingDryRun())
                self.assertTrue(finished.wait(2), "shipping thread did not finish")
                final = json.loads(bridge.getShippingState())

            self.assertFalse(final["status"]["running"])
            self.assertTrue(final["status"]["finished"])
            self.assertEqual(final["status"]["progress"], 100)
            self.assertTrue(final["status"]["dry_run"])

    def test_selected_shipping_dry_run_passes_only_selected_personnel_numbers(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pdf_path = root / "journal.pdf"
            excel_path = root / "employees.xlsx"
            pdf_path.write_bytes(b"test")
            excel_path.write_bytes(b"test")
            settings = build_default_settings()
            settings["companies"] = [{"id": "test", "name": "Test", "email_excel_file": str(excel_path)}]
            settings["selected_company_id"] = "test"
            settings["ui"]["last_pdf_input_mode"] = "single_pdf"
            settings["ui"]["last_pdf_dir"] = str(pdf_path)
            finished = threading.Event()

            with patch("ui_web.bridge.load_settings", side_effect=lambda: settings), patch(
                "ui_web.bridge.LicenseManager.require_action", return_value=(True, {})
            ), patch("ui_web.bridge.company_output_dir", return_value=root / "output"), patch(
                "core.jobs.run_main_job",
                return_value={"summary": {"dry_run": True}, "table_rows": []},
            ) as run_job:
                bridge = WebBridge()
                bridge._register_result_reports = lambda *_args, **_kwargs: None  # type: ignore[method-assign]
                bridge._validation_company_id = "test"
                bridge._validation_input_signature = bridge._input_signature(settings)
                bridge._validation_state = {"ready": True}
                bridge.shippingFinished.connect(lambda _payload: finished.set())
                json.loads(bridge.startSelectedShippingDryRun('["100", "200"]'))
                self.assertTrue(finished.wait(2), "selected shipping dry-run did not finish")

            self.assertEqual(run_job.call_args.kwargs["selected_persnr"], {"100", "200"})

    def test_mass_message_attachment_dialog_updates_state_and_remembers_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            attachment = Path(temp_dir) / "Hinweis.pdf"
            attachment.write_bytes(b"pdf")
            settings = build_default_settings()
            bridge = WebBridge()
            adapter = ApiAdapter(bridge)
            adapter.attach_window(FakeWindow((str(attachment),)))  # type: ignore[arg-type]
            with patch("pywebview_app.load_settings", side_effect=lambda: settings), patch(
                "pywebview_app.save_settings"
            ), patch("ui_web.bridge.load_settings", side_effect=lambda: settings):
                payload = json.loads(adapter.chooseMassMessageAttachments())

            self.assertEqual(payload["attachments"][0]["name"], "Hinweis.pdf")
            self.assertEqual(settings["ui"]["last_mass_attachment_dir"], str(Path(temp_dir).resolve()))
            self.assertFalse(payload["status"]["preview_ready"])

    def test_structured_shipping_progress_uses_exact_recipient_count(self) -> None:
        settings = build_default_settings()
        settings["companies"] = [{"id": "test", "name": "Test"}]
        settings["selected_company_id"] = "test"
        with patch("ui_web.bridge.load_settings", side_effect=lambda: settings):
            bridge = WebBridge()
            bridge._register_result_reports = lambda *_args, **_kwargs: None  # type: ignore[method-assign]
            bridge._shipping_company_id = "test"
            bridge._shipping_input_signature = bridge._shipping_signature(settings)
            bridge._shipping_running = True
            bridge._shipping_status = {
                **bridge._idle_shipping_status(),
                "running": True,
                "dry_run": False,
            }

            bridge._on_shipping_progress({
                "kind": "shipping_progress",
                "phase": "sending",
                "current": 3,
                "total": 10,
                "operation": "E-Mail wird gesendet.",
                "persnr": "10003",
                "email": "person@example.de",
                "prepared": 4,
                "sent": 3,
                "errors": 0,
            })

        self.assertEqual(bridge._shipping_status["progress"], 30)
        self.assertEqual(bridge._shipping_status["current_step"], "E-Mails werden gesendet")
        self.assertEqual(bridge._shipping_status["live_progress"]["current"], 3)
        self.assertEqual(bridge._shipping_status["live_progress"]["total"], 10)

    def test_mass_message_thread_reaches_finished_without_qt_event_loop(self) -> None:
        settings = build_default_settings()
        settings["companies"] = [{"id": "test", "name": "Test", "email_excel_file": "/tmp/test.xlsx"}]
        settings["selected_company_id"] = "test"
        finished = threading.Event()
        preview = {
            "ready": True,
            "company_id": "test",
            "total_count": 1,
            "recipients": [{"PersNr": "1", "Email": "test@example.de"}],
        }
        result = {"sent_count": 1, "error_count": 0, "total_count": 1, "errors": []}
        with patch("ui_web.bridge.load_settings", side_effect=lambda: settings), patch(
            "ui_web.bridge.LicenseManager.require_action", return_value=(True, {})
        ), patch("core.jobs.run_mass_message_job", return_value=result):
            bridge = WebBridge()
            bridge._build_mass_message_preview = lambda *_args: preview  # type: ignore[method-assign]
            bridge.massMessageFinished.connect(lambda _payload: finished.set())
            json.loads(bridge.startMassMessage("Betreff", "Text"))
            self.assertTrue(finished.wait(2), "mass-message thread did not finish")
            final = json.loads(bridge.getMassMessageState())

        self.assertFalse(final["status"]["running"])
        self.assertTrue(final["status"]["finished"])
        self.assertEqual(final["status"]["progress"], 100)
        self.assertEqual(final["status"]["sent_count"], 1)

    def test_smtp_password_is_retained_when_form_sends_blank_value(self) -> None:
        settings = build_default_settings()
        settings["smtp"]["password"] = "already-saved-secret"
        saved: list[dict] = []
        with patch("ui_web.bridge.load_settings", side_effect=lambda: settings), patch(
            "ui_web.bridge.save_settings", side_effect=lambda value: saved.append(value)
        ):
            bridge = WebBridge()
            bridge._processing_payload = lambda _settings: {}  # type: ignore[method-assign]
            bridge._shipping_payload = lambda _settings: {}  # type: ignore[method-assign]
            result = json.loads(bridge.saveSettingsState(json.dumps({"smtp": {"password": ""}})))
            public_state = json.loads(bridge.getSettingsState())

        self.assertTrue(result["ok"])
        self.assertEqual(saved[-1]["smtp"]["password"], "already-saved-secret")
        self.assertTrue(public_state["smtp"]["password_set"])
        self.assertNotIn("password", public_state["smtp"])

    def test_invalid_sender_email_is_not_saved(self) -> None:
        settings = build_default_settings()
        saved: list[dict] = []
        with patch("ui_web.bridge.load_settings", side_effect=lambda: settings), patch(
            "ui_web.bridge.save_settings", side_effect=lambda value: saved.append(value)
        ):
            bridge = WebBridge()
            result = json.loads(
                bridge.saveSettingsState(
                    json.dumps(
                        {
                            "smtp": {
                                "server": "smtp.example.de",
                                "username": "payroll@example.de",
                                "from_email": "payroll",
                            }
                        }
                    )
                )
            )
        self.assertFalse(result["ok"])
        self.assertIn("vollständige gültige Adresse", result["message"])
        self.assertEqual(saved, [])

    def test_shipping_preparation_is_invalidated_when_mail_settings_change(self) -> None:
        settings = build_default_settings()
        settings["companies"] = [{"id": "test", "name": "Test"}]
        settings["selected_company_id"] = "test"
        settings["smtp"].update(
            server="smtp.example.de",
            port=587,
            username="payroll@example.de",
            from_email="payroll@example.de",
        )
        bridge = WebBridge()
        before = bridge._shipping_signature(settings)
        settings["smtp"]["from_email"] = "other@example.de"
        after = bridge._shipping_signature(settings)
        self.assertNotEqual(before, after)
        self.assertEqual(before[:4], after[:4])

    def test_failed_shipping_is_not_reported_as_success(self) -> None:
        settings = build_default_settings()
        settings["companies"] = [{"id": "test", "name": "Test"}]
        settings["selected_company_id"] = "test"
        with patch("ui_web.bridge.load_settings", side_effect=lambda: settings):
            bridge = WebBridge()
            bridge._register_result_reports = lambda *_args, **_kwargs: None  # type: ignore[method-assign]
            bridge._shipping_company_id = "test"
            bridge._shipping_input_signature = bridge._shipping_signature(settings)
            bridge._on_shipping_finished(
                {
                    "summary": {"dry_run": False, "prepared_or_sent_count": 0, "failed_count": 2},
                    "table_rows": [{"PersNr": "1", "Status": "Fehler"}],
                }
            )
        self.assertTrue(bridge._shipping_status["failed"])
        self.assertFalse(bridge._shipping_status["finished"])
        self.assertEqual(bridge._shipping_status["current_step"], "Versand fehlgeschlagen")
        self.assertIn("Keine E-Mail wurde gesendet", bridge._shipping_status["message"])

    def test_partial_shipping_reports_sent_and_failed_counts(self) -> None:
        settings = build_default_settings()
        settings["companies"] = [{"id": "test", "name": "Test"}]
        settings["selected_company_id"] = "test"
        with patch("ui_web.bridge.load_settings", side_effect=lambda: settings):
            bridge = WebBridge()
            bridge._register_result_reports = lambda *_args, **_kwargs: None  # type: ignore[method-assign]
            bridge._shipping_company_id = "test"
            bridge._shipping_input_signature = bridge._shipping_signature(settings)
            bridge._on_shipping_finished(
                {
                    "summary": {"dry_run": False, "prepared_or_sent_count": 3, "failed_count": 1},
                    "table_rows": [{"PersNr": "1", "Status": "Gesendet"}],
                }
            )
        self.assertFalse(bridge._shipping_status["failed"])
        self.assertTrue(bridge._shipping_status["finished"])
        self.assertEqual(bridge._shipping_status["current_step"], "Versand teilweise abgeschlossen")
        self.assertIn("3 E-Mails", bridge._shipping_status["message"])
        self.assertIn("1", bridge._shipping_status["message"])

    def test_pdf_encryption_settings_are_saved(self) -> None:
        settings = build_default_settings()
        saved: list[dict] = []
        with patch("ui_web.bridge.load_settings", side_effect=lambda: settings), patch(
            "ui_web.bridge.save_settings", side_effect=lambda value: saved.append(value)
        ):
            bridge = WebBridge()
            bridge._processing_payload = lambda _settings: {}  # type: ignore[method-assign]
            bridge._shipping_payload = lambda _settings: {}  # type: ignore[method-assign]
            result = json.loads(
                bridge.saveSettingsState(
                    json.dumps(
                        {
                            "pdf_password": {
                                "enabled": True,
                                "source": "birth_date",
                                "prefix": "LM-",
                                "suffix": "-2026",
                            }
                        }
                    )
                )
            )

        self.assertTrue(result["ok"])
        self.assertEqual(
            saved[-1]["pdf_password"],
            {"enabled": True, "source": "birth_date", "prefix": "LM-", "suffix": "-2026"},
        )

    def test_outlook_accounts_are_returned_for_sender_selection(self) -> None:
        settings = build_default_settings()
        accounts = [
            {
                "identifier": "payroll@example.de",
                "smtp_address": "payroll@example.de",
                "label": "Lohnbuchhaltung <payroll@example.de>",
            }
        ]
        with patch("ui_web.bridge.load_settings", side_effect=lambda: settings), patch(
            "core.mailer.list_outlook_accounts", return_value=accounts
        ):
            bridge = WebBridge()
            result = json.loads(bridge.getOutlookAccounts())

        self.assertTrue(result["ok"])
        self.assertEqual(result["accounts"], accounts)


if __name__ == "__main__":
    unittest.main()

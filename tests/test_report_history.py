from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ui_web.report_history import ReportHistoryStore


class ReportHistoryStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temporary_directory.name) / "lohnmail_history.sqlite3"
        self.store = ReportHistoryStore(self.database_path)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_report_records_survive_reopening_database(self) -> None:
        record = {
            "id": "company-a:run-1:send",
            "company_id": "company-a",
            "company_name": "Company A",
            "run_id": "run-1",
            "run_dir": "/tmp/run-1",
            "kind": "send",
            "type": "xlsx",
            "title": "Versandbericht",
            "filename": "send_report.xlsx",
            "subtitle": "Versand",
            "operation": "Versand",
            "path": "/tmp/run-1/send_report.xlsx",
            "exists": True,
            "status": "ready",
            "created_at": "2026-08-21T10:00:00+02:00",
            "size": 512,
            "owner": "LohnMail",
            "source": "workflow",
            "dry_run": False,
            "metrics": {"employees": 2, "sent": 1, "failed": 1},
        }
        self.store.upsert_records([record])

        records = ReportHistoryStore(self.database_path).load_records()

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["id"], record["id"])
        self.assertEqual(records[0]["metrics"]["sent"], 1)
        self.assertFalse(records[0]["dry_run"])

    def test_session_keeps_recipient_validation_and_delivery_fields(self) -> None:
        session = {
            "id": "run-2",
            "run_id": "run-2",
            "company_id": "company-b",
            "company_name": "Company B",
            "created_at": "2026-08-21T11:00:00+02:00",
            "status": "Versendet",
            "status_key": "sent",
            "dry_run": False,
            "metrics": {"employees": 1, "sent": 1},
            "recipients": [
                {
                    "persnr": "00123",
                    "employee": "Max Mustermann",
                    "email": "max@example.com",
                    "document": "00123.pdf",
                    "status": "Gesendet",
                    "error": "",
                    "sent_at": "2026-08-21T11:02:00+02:00",
                    "message_id": "message-123",
                    "delivery_status": "accepted",
                    "delivery_checked_at": "2026-08-21T11:03:00+02:00",
                    "email_validation": {
                        "code": "valid",
                        "label": "Gültig",
                        "mx_status": "OK",
                        "checked_at": "2026-08-21T10:59:00+02:00",
                        "sendable": True,
                        "hint": "",
                    },
                }
            ],
        }
        self.store.upsert_session(session)

        recipients = ReportHistoryStore(self.database_path).load_recipients("company-b", "run-2")

        self.assertEqual(len(recipients), 1)
        self.assertEqual(recipients[0]["persnr"], "00123")
        self.assertEqual(recipients[0]["message_id"], "message-123")
        self.assertEqual(recipients[0]["delivery_status"], "accepted")
        self.assertTrue(recipients[0]["email_validation"]["sendable"])
        self.assertEqual(recipients[0]["email_validation"]["mx_status"], "OK")

    def test_empty_refresh_does_not_delete_saved_recipients(self) -> None:
        session = {
            "run_id": "run-3",
            "company_id": "company-c",
            "recipients": [{"persnr": "77", "email": "saved@example.com"}],
        }
        self.store.upsert_session(session)
        self.store.upsert_session({"run_id": "run-3", "company_id": "company-c", "recipients": []})

        recipients = self.store.load_recipients("company-c", "run-3")

        self.assertEqual(len(recipients), 1)
        self.assertEqual(recipients[0]["email"], "saved@example.com")

    def test_report_refresh_preserves_saved_delivery_fields(self) -> None:
        self.store.upsert_session(
            {
                "run_id": "run-4",
                "company_id": "company-d",
                "recipients": [
                    {
                        "persnr": "88",
                        "email": "delivered@example.com",
                        "status": "Gesendet",
                        "sent_at": "2026-08-21T12:01:00+02:00",
                        "message_id": "message-88",
                        "delivery_status": "accepted",
                        "delivery_checked_at": "2026-08-21T12:02:00+02:00",
                    }
                ],
            }
        )

        self.store.upsert_session(
            {
                "run_id": "run-4",
                "company_id": "company-d",
                "recipients": [
                    {
                        "persnr": "88",
                        "employee": "Updated Name",
                        "email": "delivered@example.com",
                        "status": "Gesendet",
                    }
                ],
            }
        )

        recipients = self.store.load_recipients("company-d", "run-4")

        self.assertEqual(len(recipients), 1)
        self.assertEqual(recipients[0]["employee"], "Updated Name")
        self.assertEqual(recipients[0]["message_id"], "message-88")
        self.assertEqual(recipients[0]["delivery_status"], "accepted")
        self.assertEqual(
            recipients[0]["delivery_checked_at"],
            "2026-08-21T12:02:00+02:00",
        )

    def test_sessions_survive_reopening_without_report_files(self) -> None:
        self.store.upsert_session(
            {
                "run_id": "run-5",
                "company_id": "company-e",
                "company_name": "Company E",
                "created_at": "2026-08-21T13:00:00+02:00",
                "status": "Versendet",
                "status_key": "sent",
                "dry_run": False,
                "metrics": {"employees": 2, "sent": 1, "failed": 1},
                "recipients": [
                    {
                        "persnr": "99",
                        "email": "history@example.com",
                        "status": "Gesendet",
                        "delivery_status": "accepted",
                    }
                ],
            }
        )

        sessions = ReportHistoryStore(self.database_path).load_sessions("company-e")

        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["run_id"], "run-5")
        self.assertEqual(sessions[0]["metrics"]["sent"], 1)
        self.assertFalse(sessions[0]["dry_run"])
        self.assertEqual(sessions[0]["recipients"][0]["email"], "history@example.com")
        self.assertEqual(sessions[0]["recipients"][0]["delivery_status"], "accepted")

    def test_sparse_refresh_preserves_saved_session_metadata(self) -> None:
        self.store.upsert_session(
            {
                "run_id": "run-6",
                "company_id": "company-f",
                "company_name": "Company F",
                "created_at": "2026-08-21T14:00:00+02:00",
                "status": "Versendet",
                "status_key": "sent",
                "dry_run": False,
                "metrics": {"employees": 3, "sent": 3},
            }
        )

        self.store.upsert_session({"run_id": "run-6", "company_id": "company-f"})
        session = self.store.load_sessions("company-f")[0]

        self.assertEqual(session["company_name"], "Company F")
        self.assertEqual(session["created_at"], "2026-08-21T14:00:00+02:00")
        self.assertEqual(session["status_key"], "sent")
        self.assertEqual(session["metrics"]["sent"], 3)
        self.assertFalse(session["dry_run"])

    def test_changed_recipient_does_not_inherit_delivery_fields_by_row(self) -> None:
        self.store.upsert_session(
            {
                "run_id": "run-7",
                "company_id": "company-g",
                "recipients": [
                    {
                        "persnr": "100",
                        "email": "first@example.com",
                        "document": "100.pdf",
                        "sent_at": "2026-08-21T15:00:00+02:00",
                        "message_id": "message-first",
                        "delivery_status": "accepted",
                    }
                ],
            }
        )

        self.store.upsert_session(
            {
                "run_id": "run-7",
                "company_id": "company-g",
                "recipients": [
                    {
                        "persnr": "200",
                        "email": "second@example.com",
                        "document": "200.pdf",
                    }
                ],
            }
        )
        recipient = self.store.load_recipients("company-g", "run-7")[0]

        self.assertEqual(recipient["persnr"], "200")
        self.assertNotIn("message_id", recipient)
        self.assertNotIn("delivery_status", recipient)


if __name__ == "__main__":
    unittest.main()

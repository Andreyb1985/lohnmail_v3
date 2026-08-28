from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ReportHistoryStore:
    """Persistent report and delivery history for the WebEngine UI."""

    SCHEMA_VERSION = 1

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=10.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    @contextmanager
    def _connection(self):
        connection = self._connect()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _json(value: Any) -> str:
        return json.dumps(value or {}, ensure_ascii=False, sort_keys=True)

    @staticmethod
    def _load_json(value: str | None) -> dict[str, Any]:
        if not value:
            return {}
        try:
            loaded = json.loads(value)
        except (TypeError, ValueError):
            return {}
        return loaded if isinstance(loaded, dict) else {}

    def _ensure_schema(self) -> None:
        with self._connection() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS schema_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS report_records (
                    record_id TEXT PRIMARY KEY,
                    company_id TEXT NOT NULL DEFAULT '',
                    company_name TEXT NOT NULL DEFAULT '',
                    run_id TEXT NOT NULL DEFAULT '',
                    run_dir TEXT NOT NULL DEFAULT '',
                    kind TEXT NOT NULL DEFAULT '',
                    report_type TEXT NOT NULL DEFAULT '',
                    title TEXT NOT NULL DEFAULT '',
                    filename TEXT NOT NULL DEFAULT '',
                    subtitle TEXT NOT NULL DEFAULT '',
                    operation TEXT NOT NULL DEFAULT '',
                    path TEXT NOT NULL DEFAULT '',
                    file_exists INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT '',
                    size INTEGER NOT NULL DEFAULT 0,
                    owner TEXT NOT NULL DEFAULT '',
                    source TEXT NOT NULL DEFAULT '',
                    dry_run INTEGER,
                    metrics_json TEXT NOT NULL DEFAULT '{}',
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_report_records_company_created
                    ON report_records(company_id, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_report_records_company_run
                    ON report_records(company_id, run_id);

                CREATE TABLE IF NOT EXISTS send_sessions (
                    company_id TEXT NOT NULL DEFAULT '',
                    run_id TEXT NOT NULL,
                    company_name TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT '',
                    status_key TEXT NOT NULL DEFAULT '',
                    dry_run INTEGER,
                    metrics_json TEXT NOT NULL DEFAULT '{}',
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (company_id, run_id)
                );

                CREATE INDEX IF NOT EXISTS idx_send_sessions_company_created
                    ON send_sessions(company_id, created_at DESC);

                CREATE TABLE IF NOT EXISTS send_recipients (
                    recipient_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_id TEXT NOT NULL DEFAULT '',
                    run_id TEXT NOT NULL,
                    row_index INTEGER NOT NULL,
                    persnr TEXT NOT NULL DEFAULT '',
                    employee TEXT NOT NULL DEFAULT '',
                    email TEXT NOT NULL DEFAULT '',
                    document TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT '',
                    error TEXT NOT NULL DEFAULT '',
                    validation_code TEXT NOT NULL DEFAULT '',
                    validation_label TEXT NOT NULL DEFAULT '',
                    mx_status TEXT NOT NULL DEFAULT '',
                    validation_checked_at TEXT NOT NULL DEFAULT '',
                    sendable INTEGER,
                    validation_hint TEXT NOT NULL DEFAULT '',
                    sent_at TEXT NOT NULL DEFAULT '',
                    message_id TEXT NOT NULL DEFAULT '',
                    delivery_status TEXT NOT NULL DEFAULT '',
                    delivery_checked_at TEXT NOT NULL DEFAULT '',
                    UNIQUE (company_id, run_id, row_index),
                    FOREIGN KEY (company_id, run_id)
                        REFERENCES send_sessions(company_id, run_id)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_send_recipients_session
                    ON send_recipients(company_id, run_id, row_index);
                """
            )
            connection.execute(
                """
                INSERT INTO schema_meta(key, value) VALUES('schema_version', ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (str(self.SCHEMA_VERSION),),
            )

    def load_records(self) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM report_records ORDER BY created_at DESC, record_id"
            ).fetchall()

        records: list[dict[str, Any]] = []
        for row in rows:
            record = {
                "id": row["record_id"],
                "company_id": row["company_id"],
                "company_name": row["company_name"],
                "run_id": row["run_id"],
                "run_dir": row["run_dir"],
                "kind": row["kind"],
                "type": row["report_type"],
                "title": row["title"],
                "filename": row["filename"],
                "subtitle": row["subtitle"],
                "operation": row["operation"],
                "path": row["path"],
                "exists": bool(row["file_exists"]),
                "status": row["status"],
                "created_at": row["created_at"],
                "size": int(row["size"] or 0),
                "owner": row["owner"],
                "source": row["source"],
                "metrics": self._load_json(row["metrics_json"]),
            }
            if row["dry_run"] is not None:
                record["dry_run"] = bool(row["dry_run"])
            records.append(record)
        return records

    def upsert_records(self, records: list[dict[str, Any]]) -> None:
        if not records:
            return
        updated_at = self._now()
        values = []
        for record in records:
            record_id = str(record.get("id") or "").strip()
            if not record_id:
                continue
            dry_run = record.get("dry_run")
            values.append(
                (
                    record_id,
                    str(record.get("company_id") or ""),
                    str(record.get("company_name") or ""),
                    str(record.get("run_id") or ""),
                    str(record.get("run_dir") or ""),
                    str(record.get("kind") or ""),
                    str(record.get("type") or ""),
                    str(record.get("title") or ""),
                    str(record.get("filename") or ""),
                    str(record.get("subtitle") or ""),
                    str(record.get("operation") or ""),
                    str(record.get("path") or ""),
                    1 if record.get("exists") else 0,
                    str(record.get("status") or ""),
                    str(record.get("created_at") or ""),
                    int(record.get("size") or 0),
                    str(record.get("owner") or ""),
                    str(record.get("source") or ""),
                    None if dry_run is None else (1 if dry_run else 0),
                    self._json(record.get("metrics")),
                    updated_at,
                )
            )
        if not values:
            return

        with self._connection() as connection:
            connection.executemany(
                """
                INSERT INTO report_records (
                    record_id, company_id, company_name, run_id, run_dir,
                    kind, report_type, title, filename, subtitle, operation,
                    path, file_exists, status, created_at, size, owner, source,
                    dry_run, metrics_json, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(record_id) DO UPDATE SET
                    company_id = excluded.company_id,
                    company_name = excluded.company_name,
                    run_id = excluded.run_id,
                    run_dir = excluded.run_dir,
                    kind = excluded.kind,
                    report_type = excluded.report_type,
                    title = excluded.title,
                    filename = excluded.filename,
                    subtitle = excluded.subtitle,
                    operation = excluded.operation,
                    path = excluded.path,
                    file_exists = excluded.file_exists,
                    status = excluded.status,
                    created_at = excluded.created_at,
                    size = excluded.size,
                    owner = excluded.owner,
                    source = excluded.source,
                    dry_run = excluded.dry_run,
                    metrics_json = excluded.metrics_json,
                    updated_at = excluded.updated_at
                """,
                values,
            )

    def upsert_session(self, session: dict[str, Any]) -> None:
        company_id = str(session.get("company_id") or "")
        run_id = str(session.get("run_id") or session.get("id") or "").strip()
        if not run_id:
            return
        dry_run = session.get("dry_run")
        recipients = session.get("recipients")
        if not isinstance(recipients, list):
            recipients = []
        recipient_rows = [recipient for recipient in recipients if isinstance(recipient, dict)]
        updated_at = self._now()

        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO send_sessions (
                    company_id, run_id, company_name, created_at, status,
                    status_key, dry_run, metrics_json, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(company_id, run_id) DO UPDATE SET
                    company_name = CASE
                        WHEN excluded.company_name <> '' THEN excluded.company_name
                        ELSE send_sessions.company_name
                    END,
                    created_at = CASE
                        WHEN excluded.created_at <> '' THEN excluded.created_at
                        ELSE send_sessions.created_at
                    END,
                    status = CASE
                        WHEN excluded.status <> '' THEN excluded.status
                        ELSE send_sessions.status
                    END,
                    status_key = CASE
                        WHEN excluded.status_key <> '' THEN excluded.status_key
                        ELSE send_sessions.status_key
                    END,
                    dry_run = COALESCE(excluded.dry_run, send_sessions.dry_run),
                    metrics_json = CASE
                        WHEN excluded.metrics_json <> '{}' THEN excluded.metrics_json
                        ELSE send_sessions.metrics_json
                    END,
                    updated_at = excluded.updated_at
                """,
                (
                    company_id,
                    run_id,
                    str(session.get("company_name") or ""),
                    str(session.get("created_at") or ""),
                    str(session.get("status") or ""),
                    str(session.get("status_key") or ""),
                    None if dry_run is None else (1 if dry_run else 0),
                    self._json(session.get("metrics")),
                    updated_at,
                ),
            )
            if recipient_rows:
                connection.execute(
                    """
                    DELETE FROM send_recipients
                    WHERE company_id = ? AND run_id = ? AND row_index >= ?
                    """,
                    (company_id, run_id, len(recipient_rows)),
                )
                connection.executemany(
                    """
                    INSERT INTO send_recipients (
                        company_id, run_id, row_index, persnr, employee, email,
                        document, status, error, validation_code,
                        validation_label, mx_status, validation_checked_at,
                        sendable, validation_hint, sent_at, message_id,
                        delivery_status, delivery_checked_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(company_id, run_id, row_index) DO UPDATE SET
                        persnr = excluded.persnr,
                        employee = excluded.employee,
                        email = excluded.email,
                        document = excluded.document,
                        status = excluded.status,
                        error = excluded.error,
                        validation_code = excluded.validation_code,
                        validation_label = excluded.validation_label,
                        mx_status = excluded.mx_status,
                        validation_checked_at = excluded.validation_checked_at,
                        sendable = excluded.sendable,
                        validation_hint = excluded.validation_hint,
                        sent_at = CASE
                            WHEN excluded.sent_at <> '' THEN excluded.sent_at
                            WHEN send_recipients.persnr = excluded.persnr
                                AND send_recipients.email = excluded.email
                                AND send_recipients.document = excluded.document
                                THEN send_recipients.sent_at
                            ELSE ''
                        END,
                        message_id = CASE
                            WHEN excluded.message_id <> '' THEN excluded.message_id
                            WHEN send_recipients.persnr = excluded.persnr
                                AND send_recipients.email = excluded.email
                                AND send_recipients.document = excluded.document
                                THEN send_recipients.message_id
                            ELSE ''
                        END,
                        delivery_status = CASE
                            WHEN excluded.delivery_status <> '' THEN excluded.delivery_status
                            WHEN send_recipients.persnr = excluded.persnr
                                AND send_recipients.email = excluded.email
                                AND send_recipients.document = excluded.document
                                THEN send_recipients.delivery_status
                            ELSE ''
                        END,
                        delivery_checked_at = CASE
                            WHEN excluded.delivery_checked_at <> '' THEN excluded.delivery_checked_at
                            WHEN send_recipients.persnr = excluded.persnr
                                AND send_recipients.email = excluded.email
                                AND send_recipients.document = excluded.document
                                THEN send_recipients.delivery_checked_at
                            ELSE ''
                        END
                    """,
                    [
                        self._recipient_values(company_id, run_id, index, recipient)
                        for index, recipient in enumerate(recipient_rows)
                    ],
                )

    @staticmethod
    def _recipient_values(
        company_id: str,
        run_id: str,
        row_index: int,
        recipient: dict[str, Any],
    ) -> tuple[Any, ...]:
        validation = recipient.get("email_validation")
        if not isinstance(validation, dict):
            validation = {}
        sendable = validation.get("sendable")
        return (
            company_id,
            run_id,
            row_index,
            str(recipient.get("persnr") or ""),
            str(recipient.get("employee") or ""),
            str(recipient.get("email") or ""),
            str(recipient.get("document") or ""),
            str(recipient.get("status") or ""),
            str(recipient.get("error") or ""),
            str(validation.get("code") or ""),
            str(validation.get("label") or ""),
            str(validation.get("mx_status") or ""),
            str(validation.get("checked_at") or ""),
            None if sendable is None else (1 if sendable else 0),
            str(validation.get("hint") or ""),
            str(recipient.get("sent_at") or ""),
            str(recipient.get("message_id") or ""),
            str(recipient.get("delivery_status") or ""),
            str(recipient.get("delivery_checked_at") or ""),
        )

    def load_recipients(self, company_id: str, run_id: str) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM send_recipients
                WHERE company_id = ? AND run_id = ?
                ORDER BY row_index
                """,
                (company_id, run_id),
            ).fetchall()

        recipients: list[dict[str, Any]] = []
        for row in rows:
            validation: dict[str, Any] = {
                "code": row["validation_code"],
                "label": row["validation_label"],
                "mx_status": row["mx_status"],
                "checked_at": row["validation_checked_at"],
                "hint": row["validation_hint"],
            }
            if row["sendable"] is not None:
                validation["sendable"] = bool(row["sendable"])
            recipient = {
                "persnr": row["persnr"],
                "employee": row["employee"],
                "email": row["email"],
                "document": row["document"],
                "status": row["status"],
                "error": row["error"],
                "email_validation": validation,
            }
            for field in ("sent_at", "message_id", "delivery_status", "delivery_checked_at"):
                if row[field]:
                    recipient[field] = row[field]
            recipients.append(recipient)
        return recipients

    def load_sessions(self, company_id: str) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM send_sessions
                WHERE company_id = ?
                ORDER BY created_at DESC, run_id DESC
                """,
                (company_id,),
            ).fetchall()

        sessions: list[dict[str, Any]] = []
        for row in rows:
            session = {
                "id": row["run_id"],
                "run_id": row["run_id"],
                "company_id": row["company_id"],
                "company_name": row["company_name"],
                "created_at": row["created_at"],
                "status": row["status"],
                "status_key": row["status_key"],
                "metrics": self._load_json(row["metrics_json"]),
                "recipients": self.load_recipients(row["company_id"], row["run_id"]),
            }
            if row["dry_run"] is not None:
                session["dry_run"] = bool(row["dry_run"])
            sessions.append(session)
        return sessions

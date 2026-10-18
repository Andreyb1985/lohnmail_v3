"""Opt-in support reports. Never serialize exceptions, settings or job rows.

Only this allowlisted representation may leave the device. Transport failures
are deliberately not reported through this service (no recursive reporting).
"""
from __future__ import annotations

import contextvars
import hashlib
import json
import math
import re
import smtplib
import socket
import sqlite3
import ssl
import threading
import time
import uuid
import zipfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib import request
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit

from core.storage_paths import atomic_json
from core.tls import create_ssl_context

ACTIVE = contextvars.ContextVar("diagnostic_operation", default=None)
STAGES = {"check", "prepare", "send", "mass_message", "update", "mail_test", "license", "startup"}
RETENTION = 14 * 86400
MAX_BYTES = 20 * 1024 * 1024
CONSENT_VERSION = 1
ERROR_CODES = {"SUPPORT_REQUEST", "NETWORK_DNS", "NETWORK_TIMEOUT", "NETWORK_TLS", "FILE_ACCESS", "FILE_MISSING",
    "IO_ERROR", "INVALID_INPUT", "OPERATION_FAILED", "SMTP_AUTH", "SMTP_RECIPIENT", "SMTP_SENDER", "SMTP_ERROR",
    "SQLITE_ERROR", "ARCHIVE_ERROR", "HTTP_FORBIDDEN", "HTTP_ERROR", "OUTLOOK_ERROR"}


def utc(timestamp):
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat()


def safe_failure(exc):
    # Messages, arguments, local variables, filenames and recipients are NOT read.
    chain, seen = [], set()
    while isinstance(exc, BaseException) and id(exc) not in seen and len(chain) < 8:
        chain.append(exc)
        seen.add(id(exc))
        cause = exc.__cause__
        if cause is None and isinstance(exc, URLError) and isinstance(exc.reason, BaseException):
            cause = exc.reason
        if cause is None:
            break
        exc = cause
    if isinstance(exc, socket.gaierror):
        code = "NETWORK_DNS"
    elif isinstance(exc, (TimeoutError, socket.timeout)):
        code = "NETWORK_TIMEOUT"
    elif isinstance(exc, ssl.SSLError):
        code = "NETWORK_TLS"
    elif isinstance(exc, smtplib.SMTPAuthenticationError):
        code = "SMTP_AUTH"
    elif isinstance(exc, smtplib.SMTPRecipientsRefused):
        code = "SMTP_RECIPIENT"
    elif isinstance(exc, smtplib.SMTPSenderRefused):
        code = "SMTP_SENDER"
    elif isinstance(exc, smtplib.SMTPException):
        code = "SMTP_ERROR"
    elif isinstance(exc, sqlite3.Error):
        code = "SQLITE_ERROR"
    elif isinstance(exc, zipfile.BadZipFile):
        code = "ARCHIVE_ERROR"
    elif isinstance(exc, HTTPError):
        code = "HTTP_FORBIDDEN" if exc.code in (401, 403) else "HTTP_ERROR"
    elif type(exc).__module__ == "pywintypes" and type(exc).__name__ == "com_error":
        code = "OUTLOOK_ERROR"
    elif isinstance(exc, PermissionError):
        code = "FILE_ACCESS"
    elif isinstance(exc, FileNotFoundError):
        code = "FILE_MISSING"
    elif isinstance(exc, OSError):
        code = "IO_ERROR"
    elif isinstance(exc, ValueError):
        code = "INVALID_INPUT"
    else:
        code = "OPERATION_FAILED"
    frames = []
    for error in chain:
        tb = error.__traceback__
        while tb:
            module = tb.tb_frame.f_globals.get("__name__", "")
            # Module names work in frozen EXEs too; absolute build paths do not.
            if isinstance(module, str) and re.fullmatch(r"(?:core|ui_web)(?:\.[a-zA-Z_][a-zA-Z0-9_]*)+", module):
                frames.append({"module": module.replace(".", "/") + ".py", "line": tb.tb_lineno})
            tb = tb.tb_next
    return {"code": code, "frames": frames[-12:]}


def clean_report(value):
    """Re-allowlist persisted data before exposing/exporting/sending it."""
    def text(value, limit):
        if not isinstance(value, str) or len(value) > limit or re.search(r"[\x00-\x1f\x7f]", value):
            raise ValueError("Invalid stored report")
        return value
    def identity(value):
        return str(uuid.UUID(value))
    if value["schema"] != 1 or value["code"] not in ERROR_CODES or value["stage"] not in STAGES:
        raise ValueError("Unsupported report")
    result = {"schema": 1, "id": identity(value["id"]), "operation_id": identity(value["operation_id"]),
        "occurred_at": text(value["occurred_at"], 40), "code": value["code"], "stage": value["stage"]}
    datetime.fromisoformat(result["occurred_at"])
    for key in ("version", "build"):
        result[key] = text(value[key], 40)
        if not re.fullmatch(r"[0-9][0-9A-Za-z.+_-]*", result[key]):
            raise ValueError("Invalid version")
    if value["platform"] not in {"win32", "darwin", "linux"}:
        raise ValueError("Invalid platform")
    result["platform"] = value["platform"]
    result["company"] = {"id": text(value["company"]["id"], 100), "name": text(value["company"]["name"], 200)}
    result["frames"] = []
    for frame in value["frames"][-12:]:
        if not re.fullmatch(r"(?:core|ui_web)/[a-zA-Z0-9_/-]+\.py", frame["module"]) or not isinstance(frame["line"], int) or not 0 < frame["line"] < 1000000:
            raise ValueError("Invalid frame")
        result["frames"].append({"module": frame["module"], "line": frame["line"]})
    result["events"] = [clean_event(e) for e in value["events"][-20:]]
    if any(e["operation_id"] != result["operation_id"] or e["stage"] != result["stage"] for e in result["events"]):
        raise ValueError("Invalid operation")
    return result


def clean_event(value):
    if not isinstance(value["at"], (int, float)) or not math.isfinite(value["at"]) or value["stage"] not in STAGES:
        raise ValueError("Invalid event")
    if value["event"] not in {"started", "progress", "error", "finished", "failed"} or not isinstance(value["elapsed_ms"], int) or not 0 <= value["elapsed_ms"] <= 30 * 86400000:
        raise ValueError("Invalid event")
    return {"at": value["at"], "operation_id": str(uuid.UUID(value["operation_id"])), "stage": value["stage"],
        "event": value["event"], "elapsed_ms": value["elapsed_ms"]}


def record_handled_error(exc):
    active = ACTIVE.get()
    if active:
        service, context = active
        service.error(context, exc)


def record_progress():
    active = ACTIVE.get()
    if active:
        service, context = active
        service.progress(context)


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None  # Never forward a license credential to another endpoint.


def send_report(url, credential, report):
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError("HTTPS required")
    opener = request.build_opener(NoRedirect(), request.HTTPSHandler(context=create_ssl_context()))
    report = clean_report(report)
    body = json.dumps({"report": report, "machine_id": credential["machine_id"]}).encode("utf-8")
    if len(body) > 32768:
        raise ValueError("Report limit")
    req = request.Request(url.rstrip("/") + "/api/diagnostics", data=body,
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + credential["key"]})
    with opener.open(req, timeout=8) as response:
        data = response.read(65537)
        if len(data) > 65536:
            raise ValueError("Response limit")
        result = json.loads(data)
        if result.get("report_id") != report["id"] or result.get("ok") is not True:
            raise ValueError("Acknowledgement missing")


class Diagnostics:
    def __init__(self, directory, *, version, build, platform, credentials,
                 transport=send_report, clock=time.time):
        self.directory = Path(directory)
        self.path = self.directory / "journal.json"
        self.version, self.build, self.platform = version, build, platform
        self.credentials, self.transport, self.clock = credentials, transport, clock
        self.lock = threading.RLock()
        self.wake = threading.Event()
        self.stop = threading.Event()
        self.thread = None
        self.sending = False
        self.storage_ok = True
        self.data = {"automatic": False, "events": [], "reports": [], "last_send": ""}
        try:
            if self.path.is_file() and self.path.stat().st_size <= MAX_BYTES:
                saved = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(saved, dict) and isinstance(saved.get("events"), list) and isinstance(saved.get("reports"), list):
                    consent = saved.get("consent", {})
                    self.data["automatic"] = saved.get("automatic") is True and consent.get("enabled") is True and consent.get("version") == CONSENT_VERSION
                    consent_at = consent.get("at", "")
                    if consent_at:
                        consent_at = datetime.fromisoformat(consent_at).isoformat()
                    self.data["consent"] = {"enabled": self.data["automatic"], "version": CONSENT_VERSION, "at": consent_at}
                    self.data["events"] = [clean_event(e) for e in saved["events"][-1000:]]
                    for row in saved["reports"][-100:]:
                        report = clean_report(row["report"])
                        if not re.fullmatch(r"[0-9a-f]{64}", row["binding"]):
                            raise ValueError("Invalid binding")
                        queued = row.get("queued") if row.get("queued") in {"manual", "automatic"} else ""
                        if queued == "automatic" and not self.data["automatic"]:
                            queued = ""
                        self.data["reports"].append({"at": datetime.fromisoformat(report["occurred_at"]).timestamp(),
                            "report": report, "binding": row["binding"], "queued": queued, "sent": row.get("sent") is True,
                            "attempts": max(0, min(100, int(row.get("attempts", 0)))), "next_at": float(row.get("next_at", 0))})
                        if not math.isfinite(self.data["reports"][-1]["next_at"]):
                            raise ValueError("Invalid retry time")
                    if any(row.get("sent") for row in self.data["reports"]):
                        self.data["last_send"] = "Bereits übermittelte Berichte sind in der Liste markiert."
        except (OSError, ValueError, KeyError, TypeError, AttributeError, OverflowError):
            self.data = {"automatic": False, "events": [], "reports": [], "last_send": ""}
            self.storage_ok = False
        self._prune()

    def _prune(self):
        cutoff = self.clock() - RETENTION
        for key, count in (("events", 1000), ("reports", 100)):
            self.data[key] = [x for x in self.data[key] if isinstance(x, dict) and x.get("at", 0) >= cutoff][-count:]

    def _save(self):
        self._prune()
        try:
            self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            atomic_json(self.path, self.data)
            self.path.chmod(0o600)
            self.storage_ok = True
        except OSError:
            self.storage_ok = False  # Diagnostics must never stop payroll processing.

    def start(self):
        if self.thread is None:
            self.thread = threading.Thread(target=self._worker, name="lohnmail-diagnostics", daemon=True)
            self.thread.start()

    def close(self):
        self.stop.set()
        self.wake.set()

    def _worker(self):
        while not self.stop.is_set():
            self.flush()
            self.wake.wait(30)
            self.wake.clear()

    def consent(self, enabled):
        with self.lock:
            self.data["automatic"] = enabled is True
            self.data["consent"] = {"version": CONSENT_VERSION, "at": utc(self.clock()), "enabled": enabled is True}
            if not enabled:
                for row in self.data["reports"]:
                    if row.get("queued") == "automatic":
                        row["queued"] = ""
            self._save()
            if enabled and not self.storage_ok:
                self.data["automatic"] = False
        self.wake.set()

    def _credential(self):
        try:
            credential = self.credentials()
            if not isinstance(credential, dict) or not all(isinstance(credential.get(k), str) for k in ("key", "machine_id", "url")):
                return {}
            return credential if credential["key"] and credential["machine_id"] else {}
        except Exception:
            return {}

    @contextmanager
    def operation(self, stage, company_id="", company_name=""):
        credential = self._credential()
        company_id = re.sub(r"[\x00-\x1f\x7f]", "", str(company_id))[:100]
        company_name = re.sub(r"[\x00-\x1f\x7f]", "", str(company_name))[:200]
        context = {"id": str(uuid.uuid4()), "stage": stage if stage in STAGES else "startup",
            "company": {"id": company_id, "name": company_name},
            "binding": hashlib.sha256(credential.get("key", "").encode()).hexdigest(),
            "started": self.clock(), "progress_at": 0, "errors": set()}
        token = ACTIVE.set((self, context))
        self.event(context, "started")
        try:
            yield context
        except Exception as exc:
            self.error(context, exc)
            raise
        finally:
            self.event(context, "failed" if context["errors"] else "finished")
            ACTIVE.reset(token)

    def event(self, context, event):
        with self.lock:
            self.data["events"].append({"at": self.clock(), "operation_id": context["id"],
                "stage": context["stage"], "event": event,
                "elapsed_ms": max(0, int((self.clock() - context["started"]) * 1000))})
            self._save()

    def progress(self, context):
        if self.clock() - context["progress_at"] >= 5:
            context["progress_at"] = self.clock()
            self.event(context, "progress")

    def error(self, context, exc, *, support_request=False):
        failure = {"code": "SUPPORT_REQUEST", "frames": []} if support_request else safe_failure(exc)
        signature = json.dumps(failure, sort_keys=True)
        if signature in context["errors"]:
            return  # One report per error signature in an operation, not per employee.
        context["errors"].add(signature)
        self.event(context, "error")
        with self.lock:
            report = {"schema": 1, "id": str(uuid.uuid4()), "operation_id": context["id"],
                "occurred_at": utc(self.clock()), "version": self.version, "build": self.build,
                "platform": self.platform, "stage": context["stage"], "company": context["company"],
                **failure, "events": [dict(e) for e in self.data["events"] if e["operation_id"] == context["id"]][-20:]}
            self.data["reports"].append({"at": self.clock(), "report": report,
                "binding": context["binding"], "queued": "automatic" if self.data["automatic"] and not support_request else "",
                "attempts": 0, "next_at": 0, "sent": False})
            self._save()
        self.wake.set()

    def snapshot(self, company_id, company_name):
        with self.operation("startup", company_id, company_name) as context:
            self.error(context, None, support_request=True)
            context["errors"].clear()

    def state(self):
        with self.lock:
            self._prune()
            return {"automatic": bool(self.data["automatic"]), "storage_ok": self.storage_ok,
                "sending": self.sending, "pending": sum(bool(r.get("queued")) for r in self.data["reports"]),
                "last_send": self.data["last_send"],
                "reports": [{"report": r["report"], "sent": r.get("sent", False)} for r in self.data["reports"][-20:]][::-1]}

    def queue_manual(self, report_id):
        with self.lock:
            row = next((r for r in self.data["reports"] if r["report"]["id"] == report_id), None)
            if not row or row.get("sent"):
                return False
            row.update(queued="manual", next_at=0, attempts=0)
            self._save()
        self.wake.set()
        return True

    def flush(self):
        with self.lock:
            if self.sending or self.stop.is_set():
                return
            self._prune()
            eligible = [r for r in self.data["reports"] if r.get("queued") and not r.get("sent") and r.get("next_at", 0) <= self.clock()]
            # An explicit send must not wait behind the automatic backlog.
            row = next((r for r in eligible if r["queued"] == "manual"), eligible[0] if eligible else None)
            if not row or (row["queued"] == "automatic" and not self.data["automatic"]):
                return
            credential = self._credential()
            if not credential or hashlib.sha256(credential["key"].encode()).hexdigest() != row["binding"]:
                row["next_at"] = self.clock() + 3600
                self.data["last_send"] = "Lizenzzuordnung fehlt oder wurde geändert. Bericht bleibt lokal."
                self._save()
                return
            self.sending = True
        try:
            self.transport(credential["url"], credential, row["report"])
        except Exception:
            with self.lock:
                row["attempts"] += 1
                row["next_at"] = self.clock() + min(3600, 30 * 2 ** min(row["attempts"], 7))
                self.data["last_send"] = "Nicht übermittelt. Erneuter Versuch im Hintergrund; Bericht bleibt maximal 14 Tage gespeichert."
        else:
            with self.lock:
                row.update(sent=True, queued="")
                self.data["last_send"] = "Übermittelt: " + row["report"]["id"] + " · " + utc(self.clock())
        finally:
            with self.lock:
                self.sending = False
                self._save()

    def export(self, path):
        with self.lock:
            self._prune()
            payload = {"schema": 1, "reports": [r["report"] for r in self.data["reports"]],
                "events": self.data["events"]}
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("diagnostics.json", json.dumps(payload, ensure_ascii=False, indent=2))

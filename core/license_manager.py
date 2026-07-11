from __future__ import annotations

import json
import os
import platform
import socket
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


LICENSE_DIR = Path.home() / ".lohnmail"
LICENSE_PATH = LICENSE_DIR / "license.json"
CHECK_INTERVAL = timedelta(days=7)
SUBSCRIPTION_OFFLINE_GRACE = timedelta(days=7)
LIFETIME_OFFLINE_GRACE = timedelta(days=30)

ACTIVE_STATUSES = {"trialing", "active", "expiring_soon"}
BLOCKED_STATUSES = {"expired", "unpaid", "canceled", "refunded", "disputed", "revoked", "invalid"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


class LicenseManager:
    """Desktop license client.

    The desktop app never generates valid license keys. It stores local server
    responses and asks the license server to create/check/activate licenses.
    """

    def __init__(self, settings: dict | None = None) -> None:
        self.settings = settings or {}
        license_settings = self.settings.get("license", {}) if isinstance(self.settings.get("license"), dict) else {}
        self.server_url = str(
            os.environ.get("LICENSE_SERVER_URL")
            or license_settings.get("server_url", "")
            or ""
        ).strip().rstrip("/")

    def load_state(self) -> dict:
        if not LICENSE_PATH.exists():
            state = self._empty_state()
            self._save_state(state)
            return state
        try:
            data = json.loads(LICENSE_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {**self._empty_state(), **data}
        except Exception:
            pass
        return self._empty_state()

    def refresh(self, force: bool = False, start_trial: bool = True) -> dict:
        state = self.load_state()
        if not self.server_url:
            return self._with_local_status(state, "no_connection", "Lizenzserver ist nicht konfiguriert.")

        if not force and not self._needs_online_check(state):
            return self._with_local_status(state, message="Lokaler Lizenzstatus ist aktuell.")

        try:
            if not state.get("license_key") and start_trial:
                response = self._post(
                    "/api/license/start-trial",
                    {
                        "machine_id": state["machine_id"],
                        "app_version": self.app_version(),
                    },
                )
            elif state.get("license_key"):
                response = self._post(
                    "/api/license/check",
                    {
                        "license_key": state.get("license_key"),
                        "machine_id": state["machine_id"],
                        "app_version": self.app_version(),
                    },
                )
            else:
                return self._with_local_status(state, "no_connection", "Keine Lizenz vorhanden.")

            state = self._merge_server_response(state, response)
            self._save_state(state)
            return state
        except Exception as exc:
            return self._offline_state(state, str(exc))

    def activate(self, license_key: str) -> dict:
        state = self.load_state()
        if not self.server_url:
            return self._with_local_status(state, "no_connection", "Lizenzserver ist nicht konfiguriert.")
        response = self._post(
            "/api/license/activate",
            {
                "license_key": license_key,
                "machine_id": state["machine_id"],
                "app_version": self.app_version(),
            },
        )
        state = self._merge_server_response(state, response)
        self._save_state(state)
        return state

    def deactivate(self) -> dict:
        state = self.load_state()
        if not self.server_url or not state.get("license_key"):
            return self._with_local_status(state, message="Keine aktive Lizenz zum Deaktivieren.")
        self._post("/api/license/deactivate", {"license_key": state.get("license_key"), "machine_id": state["machine_id"]})
        state["status"] = "unregistered"
        state["license_key"] = ""
        state["last_message"] = "Lizenz wurde deaktiviert."
        self._save_state(state)
        return state

    def purchase_session(self, email: str = "", company_name: str = "") -> dict:
        state = self.load_state()
        response = self._post(
            "/api/stripe/create-checkout-session",
            {"email": email, "company_name": company_name, "machine_id": state["machine_id"]},
        )
        if response.get("license"):
            state = self._merge_server_response(state, response["license"])
            self._save_state(state)
        return response

    def purchase_url(self, email: str = "", company_name: str = "") -> str:
        response = self.purchase_session(email=email, company_name=company_name)
        return str(response.get("url") or "")

    def portal_url(self) -> str:
        state = self.load_state()
        response = self._post(
            "/api/stripe/customer-portal",
            {"license_key": state.get("license_key"), "machine_id": state["machine_id"]},
        )
        return str(response.get("url") or "")

    def require_action(self, action: str) -> tuple[bool, dict]:
        state = self.refresh(force=False, start_trial=True)
        status = str(state.get("status", "") or "").lower()
        if status in BLOCKED_STATUSES:
            return False, {**state, "last_message": self.block_message(status)}
        if status == "no_connection":
            return self._allow_offline(state), state
        return True, state

    def _allow_offline(self, state: dict) -> bool:
        if not self.server_url:
            return True
        last_success = _parse_dt(state.get("last_successful_check_at"))
        if not last_success:
            return False
        license_type = str(state.get("type", "") or "").lower()
        grace = LIFETIME_OFFLINE_GRACE if license_type in {"lifetime", "internal"} else SUBSCRIPTION_OFFLINE_GRACE
        return _now() <= last_success + grace

    def _needs_online_check(self, state: dict) -> bool:
        next_check = _parse_dt(state.get("next_check_at"))
        if not next_check:
            return True
        return _now() >= next_check

    def _offline_state(self, state: dict, message: str) -> dict:
        state = {**state}
        state["last_message"] = f"Lizenzserver nicht erreichbar: {message}"
        state["server"] = "Nicht erreichbar"
        if not self._allow_offline(state):
            state["status"] = "no_connection"
        self._save_state(state)
        return state

    def _with_local_status(self, state: dict, status: str | None = None, message: str = "") -> dict:
        result = {**state}
        if status:
            result["status"] = status
        result["server"] = "Nicht konfiguriert" if not self.server_url else result.get("server", "Verbunden")
        result["last_message"] = message or result.get("last_message", "")
        result["days_remaining"] = self._days_remaining(result)
        return result

    def _merge_server_response(self, state: dict, response: dict[str, Any]) -> dict:
        now = _now()
        merged = {**state}
        for key in [
            "license_key",
            "status",
            "type",
            "plan",
            "trial_started_at",
            "trial_ends_at",
            "current_period_end",
            "days_remaining",
        ]:
            if key in response and response[key] is not None:
                merged[key] = response[key]
        merged["last_successful_check_at"] = _iso(now)
        merged["next_check_at"] = _iso(now + CHECK_INTERVAL)
        merged["offline_grace_until"] = _iso(now + (LIFETIME_OFFLINE_GRACE if merged.get("type") in {"lifetime", "internal"} else SUBSCRIPTION_OFFLINE_GRACE))
        merged["last_message"] = str(response.get("message") or self.message_for_state(merged))
        merged["server"] = "Verbunden"
        merged["machine_id"] = state.get("machine_id") or self._machine_id()
        return merged

    def _post(self, path: str, payload: dict) -> dict:
        if not self.server_url:
            raise RuntimeError("LICENSE_SERVER_URL is not configured.")
        request = urllib.request.Request(
            f"{self.server_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=12) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            try:
                data = json.loads(detail)
                raise RuntimeError(str(data.get("message") or detail))
            except json.JSONDecodeError:
                raise RuntimeError(detail or exc.reason)

    def _empty_state(self) -> dict:
        return {
            "license_key": "",
            "status": "unregistered",
            "type": "none",
            "plan": "",
            "machine_id": self._machine_id(),
            "trial_started_at": None,
            "trial_ends_at": None,
            "current_period_end": None,
            "last_successful_check_at": None,
            "next_check_at": None,
            "offline_grace_until": None,
            "days_remaining": None,
            "last_message": "",
            "server": "Nicht konfiguriert" if not self.server_url else "Verbunden",
        }

    def _machine_id(self) -> str:
        LICENSE_DIR.mkdir(parents=True, exist_ok=True)
        machine_file = LICENSE_DIR / "machine_id"
        if machine_file.exists():
            value = machine_file.read_text(encoding="utf-8").strip()
            if value:
                return value
        raw = f"{platform.node()}:{uuid.getnode()}:{socket.gethostname()}"
        value = str(uuid.uuid5(uuid.NAMESPACE_DNS, raw))
        machine_file.write_text(value, encoding="utf-8")
        return value

    def _save_state(self, state: dict) -> None:
        LICENSE_DIR.mkdir(parents=True, exist_ok=True)
        LICENSE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    def _days_remaining(self, state: dict) -> int | None:
        end = _parse_dt(state.get("trial_ends_at") or state.get("current_period_end"))
        if not end:
            return None
        return max(0, (end.date() - _now().date()).days)

    @staticmethod
    def app_version() -> str:
        return "v2.0.0"

    @staticmethod
    def block_message(status: str) -> str:
        messages = {
            "expired": "Ihre kostenlose Testphase ist abgelaufen. Bitte aktivieren Sie eine Lizenz, um LohnMail weiter zu nutzen.",
            "past_due": "Die Zahlung ist überfällig. Bitte aktualisieren Sie Ihre Zahlungsdaten.",
            "unpaid": "Die Lizenz ist wegen offener Zahlung gesperrt.",
            "refunded": "Die Zahlung wurde erstattet. Die Lizenz ist gesperrt.",
            "disputed": "Die Zahlung wurde angefochten. Die Lizenz ist gesperrt.",
            "revoked": "Diese Lizenz wurde widerrufen.",
            "canceled": "Diese Lizenz wurde gekündigt.",
            "invalid": "Diese Lizenz ist ungültig.",
        }
        return messages.get(status, "Lizenz ist nicht aktiv.")

    def message_for_state(self, state: dict) -> str:
        status = str(state.get("status", "") or "").lower()
        days = state.get("days_remaining")
        if status == "trialing":
            return f"Ihre Testphase ist aktiv. Sie können LohnMail noch {days} Tage kostenlos nutzen."
        if status == "active":
            return "Lizenz ist aktiv."
        if status == "expired":
            return self.block_message(status)
        return state.get("last_message") or "Lizenzstatus geladen."

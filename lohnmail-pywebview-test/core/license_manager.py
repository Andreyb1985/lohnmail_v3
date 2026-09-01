from __future__ import annotations

import json
import os
import platform
import shutil
import socket
import subprocess
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .config import SETTINGS_DIR

DEFAULT_LICENSE_DIR = SETTINGS_DIR
LEGACY_LICENSE_DIR = Path.home() / ".lohnmail"
LICENSE_DIR = DEFAULT_LICENSE_DIR
LICENSE_PATH = LICENSE_DIR / "license.json"
DEFAULT_LICENSE_SERVER_URL = "https://license-server-lm.vercel.app"
CHECK_INTERVAL = timedelta(days=7)
SUBSCRIPTION_OFFLINE_GRACE = timedelta(days=7)
LIFETIME_OFFLINE_GRACE = timedelta(days=30)
MISSING_LICENSE_GRACE = timedelta(days=14)

ACTIVE_STATUSES = {"trialing", "active", "expiring_soon", "license_problem"}
BLOCKED_STATUSES = {"past_due", "expired", "unpaid", "canceled", "refunded", "disputed", "revoked", "invalid", "device_mismatch"}


class LicenseNotFoundError(RuntimeError):
    """The server was reached successfully, but it no longer has this license."""


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
        self.server_url = str(
            os.environ.get("LICENSE_SERVER_URL")
            or DEFAULT_LICENSE_SERVER_URL
        ).strip().rstrip("/")

    def load_state(self) -> dict:
        self._migrate_legacy_files()
        if not LICENSE_PATH.exists():
            state = self._empty_state()
            self._save_state(state)
            return state
        try:
            data = json.loads(LICENSE_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                state = {**self._empty_state(), **data}
                current_machine_id = self._machine_id()
                licensed_machine_id = str(data.get("machine_id", "") or "").strip()
                if data.get("license_key") and licensed_machine_id and licensed_machine_id != current_machine_id:
                    return {
                        **state,
                        "status": "device_mismatch",
                        "machine_id": current_machine_id,
                        "licensed_machine_id": licensed_machine_id,
                        "days_remaining": None,
                        "last_message": (
                            "Diese Lizenz ist an einen anderen Computer gebunden. "
                            "Bitte wenden Sie sich an den LohnMail-Support."
                        ),
                        "server": "Nicht geprüft",
                    }
                state["machine_id"] = current_machine_id
                grace_end = _parse_dt(state.get("license_problem_grace_ends_at"))
                if state.get("status") == "license_problem" and grace_end and grace_end < _now():
                    state["status"] = "invalid"
                    state["last_message"] = "Die 14-tägige Übergangsfrist ist abgelaufen. Bitte aktivieren Sie eine neue Lizenz."
                    self._save_state(state)
                return state
        except Exception:
            pass
        return self._empty_state()

    def refresh(self, force: bool = False, start_trial: bool = True) -> dict:
        state = self.load_state()
        if state.get("status") == "device_mismatch":
            return state
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
        except LicenseNotFoundError:
            return self._missing_license_state(state)
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

    def purchase_session(
        self,
        email: str = "",
        company_name: str = "",
        address: str = "",
        company_number: str = "",
    ) -> dict:
        state = self.load_state()
        response = self._post(
            "/api/stripe/create-checkout-session",
            {
                "email": email,
                "company_name": company_name,
                "licensee_name": company_name,
                "licensee_email": email,
                "licensee_address": address,
                "licensee_company_number": company_number,
                "machine_id": state["machine_id"],
            },
        )
        if response.get("license"):
            state = self._merge_server_response(state, response["license"])
            self._save_state(state)
        return response

    def purchase_url(self, email: str = "", company_name: str = "") -> str:
        response = self.purchase_session(email=email, company_name=company_name)
        return str(response.get("url") or "")

    def purchase_invoice_subscription(
        self,
        email: str = "",
        company_name: str = "",
        address: str = "",
        company_number: str = "",
    ) -> dict:
        state = self.load_state()
        response = self._post(
            "/api/stripe/create-invoice-subscription",
            {
                "email": email,
                "company_name": company_name,
                "licensee_name": company_name,
                "licensee_email": email,
                "licensee_address": address,
                "licensee_company_number": company_number,
                "machine_id": state["machine_id"],
            },
        )
        if response.get("license"):
            state = self._merge_server_response(state, response["license"])
            self._save_state(state)
        return response

    def update_licensee(
        self,
        name: str = "",
        email: str = "",
        address: str = "",
        company_number: str = "",
    ) -> dict:
        state = self.load_state()
        license_key = str(state.get("license_key") or "").strip()
        if not license_key:
            raise RuntimeError("Keine Serverlizenz zum Synchronisieren vorhanden.")
        response = self._post(
            "/api/license/check",
            {
                "action": "update_licensee",
                "license_key": license_key,
                "machine_id": state["machine_id"],
                "app_version": self.app_version(),
                "licensee_name": name,
                "licensee_email": email,
                "licensee_address": address,
                "licensee_company_number": company_number,
            },
        )
        state = self._merge_server_response(state, response)
        self._save_state(state)
        return state

    def portal_url(self) -> str:
        state = self.load_state()
        response = self._post(
            "/api/stripe/customer-portal",
            {"license_key": state.get("license_key"), "machine_id": state["machine_id"]},
        )
        return str(response.get("url") or "")

    def require_action(self, action: str) -> tuple[bool, dict]:
        state = self.load_state()
        status = str(state.get("status", "") or "").lower()
        if status in BLOCKED_STATUSES:
            message = (
                state.get("last_message")
                if status == "invalid" and state.get("license_problem_started_at")
                else self.block_message(status)
            )
            return False, {**state, "last_message": message}

        # Processing is local and must not wait for a network timeout. A cached
        # entitlement remains valid until its known access end. Regular status
        # refreshes still synchronize revocations and payment state.
        if self._allow_offline(state):
            return True, state

        state = self.refresh(force=False, start_trial=True)
        status = str(state.get("status", "") or "").lower()
        if status in BLOCKED_STATUSES:
            message = (
                state.get("last_message")
                if status == "invalid" and state.get("license_problem_started_at")
                else self.block_message(status)
            )
            return False, {**state, "last_message": message}
        if self._allow_offline(state):
            return True, state
        return False, state

    def _allow_offline(self, state: dict) -> bool:
        status = str(state.get("status", "") or "").lower()
        if status not in ACTIVE_STATUSES:
            return False

        if status == "license_problem":
            grace_end = _parse_dt(state.get("license_problem_grace_ends_at"))
            return bool(grace_end and _now() <= grace_end)

        entitlement_end = self._entitlement_end(state)
        if entitlement_end is not None:
            return _now() <= entitlement_end

        last_success = _parse_dt(state.get("last_successful_check_at"))
        if not last_success:
            return False
        license_type = str(state.get("type", "") or "").lower()
        grace = LIFETIME_OFFLINE_GRACE if license_type in {"lifetime", "internal"} else SUBSCRIPTION_OFFLINE_GRACE
        return _now() <= last_success + grace

    @staticmethod
    def _entitlement_end(state: dict) -> datetime | None:
        dates = [
            _parse_dt(state.get(key))
            for key in (
                "access_ends_at",
                "trial_ends_at",
                "related_trial_ends_at",
                "current_period_end",
            )
        ]
        known_dates = [value for value in dates if value is not None]
        return max(known_dates) if known_dates else None

    def _needs_online_check(self, state: dict) -> bool:
        next_check = _parse_dt(state.get("next_check_at"))
        if not next_check:
            return True
        return _now() >= next_check

    def _offline_state(self, state: dict, message: str) -> dict:
        state = {**state}
        state["last_message"] = f"Lizenzserver nicht erreichbar: {message}"
        state["server"] = "Nicht erreichbar"
        # Connection state and license state are independent. Keep an active
        # cached license visible and usable while its stored entitlement lasts.
        if not self._allow_offline(state):
            state["status"] = "no_connection"
        self._save_state(state)
        return state

    def _missing_license_state(self, state: dict) -> dict:
        """Grant one persistent 14-day transition period for a server-deleted license."""
        now = _now()
        started_at = _parse_dt(state.get("license_problem_started_at")) or now
        grace_ends_at = _parse_dt(state.get("license_problem_grace_ends_at")) or (started_at + MISSING_LICENSE_GRACE)
        remaining = max(0, (grace_ends_at.date() - now.date()).days)
        state = {**state}
        state["license_problem_started_at"] = _iso(started_at)
        state["license_problem_grace_ends_at"] = _iso(grace_ends_at)
        state["last_successful_check_at"] = _iso(now)
        state["next_check_at"] = _iso(now + CHECK_INTERVAL)
        state["server"] = "Verbunden"
        state["days_remaining"] = remaining
        if now <= grace_ends_at:
            state["status"] = "license_problem"
            state["last_message"] = (
                "Lizenz nicht gefunden oder ungültig. Bitte aktivieren Sie eine neue Lizenz. "
                f"LohnMail kann noch {remaining} Tage weiter genutzt werden."
            )
        else:
            state["status"] = "invalid"
            state["last_message"] = "Die 14-tägige Übergangsfrist ist abgelaufen. Bitte aktivieren Sie eine neue Lizenz."
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
        nullable_keys = {
            "trial_started_at",
            "trial_ends_at",
            "current_period_end",
            "access_ends_at",
            "related_trial_ends_at",
            "related_trial_license_key",
            "days_remaining",
            "email",
            "company_name",
            "licensee_name",
            "licensee_email",
            "licensee_address",
            "licensee_company_number",
            "license_key_masked",
        }
        for key in [
            "license_key",
            "license_key_masked",
            "status",
            "type",
            "plan",
            "email",
            "company_name",
            "licensee_name",
            "licensee_email",
            "licensee_address",
            "licensee_company_number",
            "seats",
            "trial_started_at",
            "trial_ends_at",
            "current_period_end",
            "access_ends_at",
            "related_trial_ends_at",
            "related_trial_license_key",
            "days_remaining",
        ]:
            if key in response and (response[key] is not None or key in nullable_keys):
                merged[key] = response[key]
        merged["days_remaining"] = self._days_remaining(merged)
        merged["last_successful_check_at"] = _iso(now)
        merged["next_check_at"] = _iso(now + CHECK_INTERVAL)
        merged["offline_grace_until"] = _iso(now + (LIFETIME_OFFLINE_GRACE if merged.get("type") in {"lifetime", "internal"} else SUBSCRIPTION_OFFLINE_GRACE))
        merged["last_message"] = str(response.get("message") or self.message_for_state(merged))
        merged["server"] = "Verbunden"
        merged["machine_id"] = state.get("machine_id") or self._machine_id()
        merged.pop("license_problem_started_at", None)
        merged.pop("license_problem_grace_ends_at", None)
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
                message = str(data.get("message") or detail)
                if exc.code == 404 and message.strip().lower() == "license not found":
                    raise LicenseNotFoundError(message)
                raise RuntimeError(message)
            except json.JSONDecodeError:
                raise RuntimeError(detail or exc.reason)

    def _empty_state(self) -> dict:
        return {
            "license_key": "",
            "status": "unregistered",
            "type": "none",
            "plan": "",
            "machine_id": self._machine_id(),
            "licensed_machine_id": "",
            "trial_started_at": None,
            "trial_ends_at": None,
            "current_period_end": None,
            "access_ends_at": None,
            "related_trial_ends_at": None,
            "related_trial_license_key": "",
            "license_key_masked": "",
            "email": "",
            "company_name": "",
            "licensee_name": "",
            "licensee_email": "",
            "licensee_address": "",
            "licensee_company_number": "",
            "seats": 1,
            "last_successful_check_at": None,
            "next_check_at": None,
            "offline_grace_until": None,
            "license_problem_started_at": None,
            "license_problem_grace_ends_at": None,
            "days_remaining": None,
            "last_message": "",
            "server": "Nicht konfiguriert" if not self.server_url else "Verbunden",
        }

    def _machine_id(self) -> str:
        self._migrate_legacy_files()
        LICENSE_DIR.mkdir(parents=True, exist_ok=True)
        machine_file = LICENSE_DIR / "machine_id"
        value = self._current_machine_id()
        try:
            stored = machine_file.read_text(encoding="utf-8").strip() if machine_file.exists() else ""
            if stored != value:
                machine_file.write_text(value, encoding="utf-8")
        except OSError:
            # The live hardware value remains authoritative even if a read-only
            # portable directory cannot update its diagnostic cache file.
            pass
        return value

    def _current_machine_id(self) -> str:
        return str(uuid.uuid5(uuid.NAMESPACE_URL, f"lohnmail-device:{self._hardware_seed()}"))

    def machine_id(self) -> str:
        """Return the persistent device ID without creating or refreshing a license."""
        return self._machine_id()

    @staticmethod
    def _hardware_seed() -> str:
        """Read a stable OS/hardware identifier; never send the raw value to the server."""
        if platform.system() == "Windows":
            try:
                import winreg

                with winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    r"SOFTWARE\Microsoft\Cryptography",
                ) as key:
                    value, _ = winreg.QueryValueEx(key, "MachineGuid")
                    if str(value or "").strip():
                        return f"windows:{str(value).strip().lower()}"
            except Exception:
                pass
        elif platform.system() == "Darwin":
            try:
                result = subprocess.run(
                    ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                for line in result.stdout.splitlines():
                    if "IOPlatformUUID" in line and "=" in line:
                        value = line.split("=", 1)[1].strip().strip('"')
                        if value:
                            return f"macos:{value.lower()}"
            except Exception:
                pass
        else:
            for candidate in (Path("/etc/machine-id"), Path("/var/lib/dbus/machine-id")):
                try:
                    value = candidate.read_text(encoding="utf-8").strip()
                    if value:
                        return f"linux:{value.lower()}"
                except Exception:
                    continue

        return f"fallback:{platform.system()}:{platform.node()}:{socket.gethostname()}:{uuid.getnode():012x}"

    @staticmethod
    def _preserve_state_machine_id(state: dict) -> None:
        """Keep an already activated license bound to its existing device ID."""
        value = str(state.get("machine_id", "") or "").strip()
        if not value:
            return
        machine_file = LICENSE_DIR / "machine_id"
        if machine_file.exists():
            return
        LICENSE_DIR.mkdir(parents=True, exist_ok=True)
        machine_file.write_text(value, encoding="utf-8")

    def _save_state(self, state: dict) -> None:
        LICENSE_DIR.mkdir(parents=True, exist_ok=True)
        LICENSE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _migrate_legacy_files() -> None:
        if LICENSE_DIR != DEFAULT_LICENSE_DIR or LEGACY_LICENSE_DIR == LICENSE_DIR:
            return
        for filename in ("license.json", "machine_id"):
            source = LEGACY_LICENSE_DIR / filename
            target = LICENSE_DIR / filename
            if target.exists() or not source.is_file():
                continue
            LICENSE_DIR.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)

    def _days_remaining(self, state: dict) -> int | None:
        if str(state.get("status", "") or "").lower() == "license_problem":
            grace_end = _parse_dt(state.get("license_problem_grace_ends_at"))
            if grace_end:
                return max(0, (grace_end.date() - _now().date()).days)
        end = _parse_dt(
            state.get("access_ends_at")
            or state.get("trial_ends_at")
            or state.get("related_trial_ends_at")
            or state.get("current_period_end")
        )
        if not end:
            return None
        return max(0, (end.date() - _now().date()).days)

    @staticmethod
    def app_version() -> str:
        return "v2.0.3"

    @staticmethod
    def block_message(status: str) -> str:
        messages = {
            "expired": "Ihre kostenlose Testphase ist abgelaufen. Bitte aktivieren Sie eine Lizenz, um LohnMail weiter zu nutzen.",
            "past_due": "Die Zahlung ist überfällig. Bitte begleichen Sie die offene Rechnung oder aktualisieren Sie Ihre Zahlungsdaten.",
            "unpaid": "Die Lizenz ist wegen offener Zahlung gesperrt.",
            "refunded": "Die Zahlung wurde erstattet. Die Lizenz ist gesperrt.",
            "disputed": "Die Zahlung wurde angefochten. Die Lizenz ist gesperrt.",
            "revoked": "Diese Lizenz wurde widerrufen.",
            "canceled": "Diese Lizenz wurde gekündigt.",
            "invalid": "Diese Lizenz ist ungültig.",
            "device_mismatch": "Diese Lizenz ist an einen anderen Computer gebunden. Bitte wenden Sie sich an den LohnMail-Support.",
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

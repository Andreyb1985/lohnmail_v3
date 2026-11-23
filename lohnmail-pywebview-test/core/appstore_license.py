"""App Store adapter. Never reads/writes legacy license.json or contacts Stripe."""
from __future__ import annotations

import ctypes
import json
import plistlib
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path


def is_app_store() -> bool:
    if sys.platform != "darwin" or not getattr(sys, "frozen", False):
        return False
    path = Path(sys.executable).parent.parent / "Info.plist"
    if (path.parent / "embedded.provisionprofile").exists():
        return True
    try:
        return plistlib.loads(path.read_bytes()).get("LohnMailDistributionChannel") == "appstore"
    except (OSError, ValueError, plistlib.InvalidFileException):
        return False


class NativeStore:
    _library = None
    _lock = threading.Lock()

    @classmethod
    def request(cls, action: str) -> dict:
        if threading.current_thread() is threading.main_thread():
            raise RuntimeError("StoreKit muss im API-Worker aufgerufen werden.")
        with cls._lock:
            if cls._library is None:
                path = Path(sys.executable).parent.parent / "Frameworks/LohnMailStoreKit.dylib"
                lib = ctypes.CDLL(str(path))
                lib.lohnmail_store_request.argtypes = [ctypes.c_char_p]
                lib.lohnmail_store_request.restype = ctypes.c_void_p
                lib.lohnmail_store_free.argtypes = [ctypes.c_void_p]
                lib.lohnmail_store_free.restype = None
                cls._library = lib
            ptr = cls._library.lohnmail_store_request(action.encode("ascii"))
            if not ptr:
                raise RuntimeError("Keine StoreKit-Antwort.")
            try:
                result = json.loads(ctypes.string_at(ptr))
                if not isinstance(result, dict):
                    raise ValueError("Ungültige StoreKit-Antwort.")
                return result
            finally:
                cls._library.lohnmail_store_free(ptr)


class AppStoreLicenseManager:
    channel = "appstore"
    server_url = ""  # No legacy diagnostics/license credentials transmitted.

    def __init__(self, settings=None):
        pass

    def machine_id(self):
        return ""

    def refresh(self, force=False, start_trial=False):
        try:
            state = NativeStore.request("status")
        except Exception:
            state = {"message": "App Store konnte nicht geprüft werden. Bitte erneut versuchen."}
        return self._state(state)

    load_state = refresh

    @staticmethod
    def _state(raw):
        active = (raw.get("verified") is True and raw.get("active") is True
                  and raw.get("product_id") == "lohnmail"
                  and raw.get("status") in {"active", "grace_period"})
        try:
            expiry = datetime.fromisoformat(raw.get("access_ends_at", "").replace("Z", "+00:00"))
            active = active and expiry > datetime.now(timezone.utc)
        except (ValueError, TypeError):
            active = False
        return {**raw, "channel": "appstore", "active": bool(active),
                "status": ("active" if active else "unregistered"),
                "apple_status": raw.get("status", "unavailable"),
                "type": "subscription", "license_key": "", "machine_id": "",
                "last_message": raw.get("message", "Abonnement über Apple verwalten.")}

    def require_action(self, action):
        state = self.refresh()
        # Existing reports/data must remain readable without a paid entitlement.
        return action == "export" or state["active"], state

    def purchase(self, action):
        if action not in {"purchase", "restore", "manage"}:
            raise ValueError("Unzulässige App-Store-Aktion.")
        return NativeStore.request(action)

    @staticmethod
    def _unsupported(*args, **kwargs):
        raise RuntimeError("In dieser Version werden Abonnements ausschließlich über Apple verwaltet.")

    activate = deactivate = purchase_session = purchase_invoice_subscription = _unsupported
    update_licensee = portal_url = purchase_url = _unsupported

    def payload(self, state=None):
        state = self.load_state() if state is None else state
        label = "Aktiv" if state["active"] else "Kein aktives Apple-Abonnement"
        if state["active"] and state.get("apple_status") == "grace_period":
            label = "Zahlungsfrist · Zugriff aktiv"
        return {**state, "label": label, "status_label": label,
                "mode": "App Store", "server": "Apple StoreKit", "server_note": "Verifizierte Apple-Käufe",
                "plan": "App Store", "type": "Apple-Abonnement", "key_present": False,
                "key_masked": "Nicht erforderlich", "licensee": {}, "history": [], "state_list": [],
                "days_remaining": None, "message": state.get("last_message", ""),
                "features": [], "unlimited": False}

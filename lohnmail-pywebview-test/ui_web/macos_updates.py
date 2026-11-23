"""Website-only update notifications. Never downloads or installs executable code."""
from __future__ import annotations

import json
import platform
import plistlib
import sys
import webbrowser
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from core.config import load_settings, save_settings
from ui_web.updater import _version_parts
from ui_web.version import APP_VERSION, APP_BUILD


def website_metadata():
    if sys.platform != "darwin" or not getattr(sys, "frozen", False):
        return {}
    contents = Path(sys.executable).parent.parent
    if (contents / "embedded.provisionprofile").exists():
        return {}
    try:
        data = plistlib.loads((contents / "Info.plist").read_bytes())
        return data if data.get("LohnMailDistributionChannel") == "website" else {}
    except (OSError, ValueError):
        return {}


def https_url(value):
    value = str(value or "")
    url = urlsplit(value)
    if (url.scheme != "https" or not url.hostname or url.username or url.password
            or url.fragment or any(c.isspace() for c in value)):
        raise ValueError("Ungültige HTTPS-Adresse für macOS-Updates.")
    return value


class MacWebsiteUpdates:
    def __init__(self, *, metadata=None, loader=load_settings, saver=save_settings,
                 opener=urlopen, browser=webbrowser.open, machine=None, system=None):
        self.meta = website_metadata() if metadata is None else metadata
        self.loader, self.saver = loader, saver
        self.opener, self.browser = opener, browser
        self.machine = machine or platform.machine()
        self.system = system or platform.mac_ver()[0]
        self.url = self.meta.get("LohnMailUpdateManifestURL", "")
        self.version = self.meta.get("CFBundleShortVersionString", APP_VERSION)
        self.build = self.meta.get("CFBundleVersion", APP_BUILD)
        self.state = dict(status="idle", available_version="", available_build="",
                          download_url="", release_notes=[], last_checked_at="", message="")

    def current_state(self):
        prefs = self.loader().get("macos_website_updates", {})
        return {**self.state, "ok": self.state["status"] != "error", "supported": True,
                "manual_download": True, "install_supported": False, "install_on_exit": False,
                "mandatory": False, "required": False, "progress": 0,
                "installed_version": self.version, "installed_build": self.build,
                "auto_check": bool(self.url) and prefs.get("auto_check", True)}

    def recover_interrupted_state(self):
        return self.current_state()

    def begin(self, action):
        return self.current_state()

    def set_preferences(self, *, auto_check=None, install_on_exit=None):
        data = self.loader()
        if isinstance(auto_check, bool):
            data["macos_website_updates"] = {"auto_check": auto_check}
            self.saver(data)
        return self.current_state()

    def check(self):
        # Never reuse a download URL after an unsuccessful or incompatible check.
        self.state.update(status="error", download_url="", available_version="",
                          available_build="", release_notes=[],
                          last_checked_at=datetime.now(timezone.utc).isoformat())
        try:
            if not self.url:
                raise ValueError("Die Update-Adresse wurde für diese Version noch nicht eingerichtet.")
            req = Request(https_url(self.url), headers={"Accept": "application/json"})
            with self.opener(req, timeout=15) as response:
                https_url(response.geturl())
                raw = response.read(65537)
            if len(raw) > 65536:
                raise ValueError("Update-Information ist zu groß.")
            data = json.loads(raw)
            if (data.get("platform") != "macos" or data.get("channel") != "website"
                    or data.get("architecture") not in {self.machine, "universal"}):
                raise ValueError("Das Update passt nicht zu dieser macOS-Installation.")
            version, build = str(data["version"]), str(data["build"])
            if not all(v and all(c.isdigit() or c == "." for c in v) for v in (version, build)):
                raise ValueError("Ungültige Versionsnummer.")
            download = https_url(data["download_url"])
            if not urlsplit(download).path.lower().endswith(".dmg"):
                raise ValueError("Die macOS-Datei muss ein DMG sein.")
            minimum = str(data["minimum_macos"])
            if _version_parts(self.system) < _version_parts(minimum):
                raise ValueError("Diese Version benötigt macOS " + minimum + " oder neuer.")
            newer = (_version_parts(version), _version_parts(build)) > (
                _version_parts(self.version), _version_parts(self.build))
            notes = data.get("release_notes", [])
            if not isinstance(notes, list) or not all(isinstance(n, str) for n in notes):
                raise ValueError("Ungültige Versionshinweise.")
            self.state.update(status="available" if newer else "current", message="",
                              available_version=version if newer else "", available_build=build if newer else "",
                              release_notes=notes, download_url=download if newer else "")
        except Exception as exc:
            self.state["message"] = "Update-Prüfung nicht möglich. " + str(exc)
        return self.current_state()

    def download(self, progress=None):
        if self.state["status"] != "available" or not self.state["download_url"]:
            return {**self.current_state(), "ok": False, "message": "Bitte zuerst nach Updates suchen."}
        try:
            if not self.browser(https_url(self.state["download_url"])):
                raise RuntimeError("Browser konnte nicht geöffnet werden.")
            return {**self.current_state(), "message": "Download im Browser geöffnet. Manuell installieren – siehe Anleitung."}
        except Exception as exc:
            return {**self.current_state(), "ok": False, "message": str(exc)}

    def install_on_exit(self):
        return {**self.current_state(), "ok": False,
                "message": "Manuelle Installation: DMG öffnen und LohnMail in Programme ersetzen."}

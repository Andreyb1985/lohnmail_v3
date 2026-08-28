from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from core.config import SETTINGS_DIR, load_settings, save_settings
from ui_web.version import APP_BUILD, APP_VERSION


DEFAULT_MANIFEST_URL = "https://license-server-lm.vercel.app/api/updates/windows/latest"
MAX_MANIFEST_BYTES = 1024 * 1024
REQUIRED_REASONS = {
    "security",
    "critical_security",
    "incompatible",
    "critical_incompatibility",
}


class UpdateError(RuntimeError):
    pass


def _version_parts(value: str) -> tuple[int, ...]:
    parts = [int(part) for part in re.findall(r"\d+", str(value or ""))]
    while len(parts) > 1 and parts[-1] == 0:
        parts.pop()
    return tuple(parts or [0])


def _safe_int(value: object, default: int = 0) -> int:
    try:
        return int(value or default)
    except (TypeError, ValueError):
        return default


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_newer(version: str, build: str) -> bool:
    remote_version = _version_parts(version)
    local_version = _version_parts(APP_VERSION)
    if remote_version != local_version:
        return remote_version > local_version
    return _version_parts(build) > _version_parts(APP_BUILD)


def _safe_download_url(value: str) -> str:
    url = str(value or "").strip()
    if not url:
        return ""
    parsed = urlparse(url)
    is_local = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    if parsed.scheme != "https" and not (parsed.scheme == "http" and is_local):
        raise UpdateError("Die Update-Datei muss über HTTPS bereitgestellt werden.")
    suffix = Path(parsed.path).suffix.lower()
    if suffix not in {".exe", ".msi"}:
        raise UpdateError("Das Update muss eine signierte EXE- oder MSI-Datei sein.")
    return url


def _verify_windows_signature(path: Path) -> tuple[bool, str]:
    command = [
        "powershell.exe",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        "& { param([string]$Path) (Get-AuthenticodeSignature -LiteralPath $Path).Status }",
        str(path),
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"Die digitale Signatur konnte nicht geprüft werden: {exc}"

    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    status = lines[-1].casefold() if lines else ""
    if result.returncode == 0 and status == "valid":
        return True, ""
    return False, "Die digitale Signatur der Installationsdatei ist ungültig oder nicht vertrauenswürdig."


class UpdateService:
    def __init__(
        self,
        *,
        settings_loader: Callable[[], dict] = load_settings,
        settings_saver: Callable[[dict], None] = save_settings,
        download_dir: Path | None = None,
        manifest_url: str | None = None,
        opener: Callable = urlopen,
        process_launcher: Callable = subprocess.Popen,
        signature_verifier: Callable[[Path], tuple[bool, str]] = _verify_windows_signature,
        platform: str | None = None,
    ) -> None:
        self._load_settings = settings_loader
        self._save_settings = settings_saver
        self.download_dir = download_dir or SETTINGS_DIR / "updates"
        self.manifest_url = (
            manifest_url
            or os.environ.get("LOHNMAIL_UPDATE_MANIFEST_URL", "").strip()
            or DEFAULT_MANIFEST_URL
        )
        self._opener = opener
        self._process_launcher = process_launcher
        self._signature_verifier = signature_verifier
        self.platform = platform or sys.platform

    def current_state(self) -> dict:
        return self._public_state(dict(self._load_settings().get("updates", {})))

    def recover_interrupted_state(self) -> dict:
        updates = dict(self._load_settings().get("updates", {}))
        if updates.get("status") in {"checking", "downloading"}:
            updates.update({
                "status": "error",
                "progress": 0,
                "downloaded_bytes": 0,
                "total_bytes": 0,
                "message": "Der letzte Update-Vorgang wurde unterbrochen.",
            })
            self._save_changes(updates)
        return self._public_state(updates)

    def begin(self, action: str) -> dict:
        if action == "check":
            return self._save_changes({
                "status": "checking",
                "progress": 0,
                "downloaded_bytes": 0,
                "total_bytes": 0,
                "message": "Updates werden gesucht.",
            })
        if action == "download":
            return self._save_changes({
                "status": "downloading",
                "progress": 0,
                "downloaded_bytes": 0,
                "total_bytes": _safe_int(self._load_settings().get("updates", {}).get("size", 0)),
                "message": "Update wird heruntergeladen.",
            })
        raise UpdateError("Unbekannte Update-Aktion.")

    def set_preferences(self, *, auto_check: bool | None = None, install_on_exit: bool | None = None) -> dict:
        settings = self._load_settings()
        updates = dict(settings.get("updates", {}))
        if auto_check is not None:
            updates["auto_check"] = bool(auto_check)
        if install_on_exit is not None:
            updates["install_on_exit"] = bool(install_on_exit)
        settings["updates"] = updates
        self._save_settings(settings)
        return self._public_state(updates)

    def check(self) -> dict:
        checked_at = datetime.now(timezone.utc).isoformat()
        previous_updates = dict(self._load_settings().get("updates", {}))
        try:
            manifest = self._fetch_manifest()
            if not manifest.get("available", True):
                return self._save_changes({
                    "last_checked_at": checked_at,
                    "status": "current",
                    "available_version": "",
                    "available_build": "",
                    "required": False,
                    "download_url": "",
                    "sha256": "",
                    "size": 0,
                    "release_notes": [],
                    "required_reason": "",
                    "downloaded_path": "",
                    "downloaded_sha256": "",
                    "progress": 0,
                    "downloaded_bytes": 0,
                    "total_bytes": 0,
                    "message": "Keine veröffentlichten Updates.",
                })
            available = _is_newer(manifest["version"], manifest["build"])
            status = "required" if available and manifest["required"] else (
                "available" if available else "current"
            )
            message = (
                f"Version {manifest['version']} ist verfügbar."
                if available
                else "LohnMail ist aktuell."
            )
            existing_download = (
                self._verified_existing_download(previous_updates, manifest)
                if available
                else None
            )
            if existing_download:
                status = "ready"
                message = "Update wurde bereits heruntergeladen und ist zur Installation bereit."
            changes = {
                "last_checked_at": checked_at,
                "status": status,
                "available_version": manifest["version"] if available else "",
                "available_build": manifest["build"] if available else "",
                "required": manifest["required"] if available else False,
                "download_url": manifest["download_url"] if available else "",
                "sha256": manifest["sha256"] if available else "",
                "size": manifest["size"] if available else 0,
                "release_notes": manifest["release_notes"] if available else [],
                "required_reason": manifest["required_reason"] if available else "",
                "downloaded_path": str(existing_download) if existing_download else "",
                "downloaded_sha256": manifest["sha256"] if existing_download else "",
                "progress": 100 if existing_download else 0,
                "downloaded_bytes": manifest["size"] if existing_download else 0,
                "total_bytes": manifest["size"] if existing_download else 0,
                "message": message,
            }
            return self._save_changes(changes)
        except Exception as exc:
            return self._save_changes({
                "last_checked_at": checked_at,
                "status": "error",
                "message": str(exc) or "Update-Prüfung fehlgeschlagen.",
            })

    def download(self, progress: Callable[[dict], None] | None = None) -> dict:
        updates = dict(self._load_settings().get("updates", {}))
        url = _safe_download_url(updates.get("download_url", ""))
        expected_hash = str(updates.get("sha256", "") or "").strip().lower()
        expected_size = _safe_int(updates.get("size", 0))
        if not url or not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
            return self._save_changes({"status": "error", "message": "Keine gültige Update-Datei verfügbar."})

        self.download_dir.mkdir(parents=True, exist_ok=True)
        filename = Path(urlparse(url).path).name
        target = self.download_dir / filename
        partial = target.with_suffix(target.suffix + ".part")
        downloaded = 0
        digest = hashlib.sha256()
        try:
            request = Request(url, headers={"User-Agent": f"LohnMail/{APP_VERSION}"})
            with self._opener(request, timeout=60) as response, partial.open("wb") as handle:
                response_size = int(response.headers.get("Content-Length", 0) or 0)
                total = expected_size or response_size
                while True:
                    chunk = response.read(256 * 1024)
                    if not chunk:
                        break
                    handle.write(chunk)
                    digest.update(chunk)
                    downloaded += len(chunk)
                    if progress:
                        progress(self._progress_state(downloaded, total))

            if expected_size and downloaded != expected_size:
                raise UpdateError("Die Größe der Update-Datei stimmt nicht mit dem Manifest überein.")
            actual_hash = digest.hexdigest()
            if actual_hash != expected_hash:
                raise UpdateError("Die Integritätsprüfung des Updates ist fehlgeschlagen.")
            partial.replace(target)
            return self._save_changes({
                "status": "ready",
                "progress": 100,
                "downloaded_bytes": downloaded,
                "total_bytes": expected_size or downloaded,
                "downloaded_path": str(target),
                "downloaded_sha256": actual_hash,
                "message": "Update wurde geprüft und ist zur Installation bereit.",
            })
        except Exception as exc:
            partial.unlink(missing_ok=True)
            return self._save_changes({
                "status": "error",
                "progress": 0,
                "downloaded_bytes": 0,
                "total_bytes": expected_size,
                "message": str(exc) or "Download fehlgeschlagen.",
            })

    def install_on_exit(self) -> dict:
        updates = dict(self._load_settings().get("updates", {}))
        if not updates.get("install_on_exit") or updates.get("status") != "ready":
            return {"ok": False, "started": False, "message": "Keine Installation beim Beenden geplant."}
        if self.platform != "win32":
            return {"ok": False, "started": False, "message": "Die automatische Installation ist nur unter Windows verfügbar."}

        path = Path(str(updates.get("downloaded_path", "") or ""))
        expected_hash = str(updates.get("downloaded_sha256", "") or "").lower()
        if not path.is_file() or path.suffix.lower() not in {".exe", ".msi"}:
            return {"ok": False, "started": False, "message": "Installationsdatei wurde nicht gefunden."}
        actual_hash = _sha256_file(path)
        if not expected_hash or actual_hash != expected_hash:
            return {"ok": False, "started": False, "message": "Installationsdatei ist nicht mehr gültig."}
        signature_valid, signature_message = self._signature_verifier(path)
        if not signature_valid:
            return {
                "ok": False,
                "started": False,
                "message": signature_message or "Die digitale Signatur der Installationsdatei ist ungültig.",
            }

        command = ["msiexec.exe", "/i", str(path), "/passive", "/norestart"] if path.suffix.lower() == ".msi" else [str(path), "/SILENT", "/NORESTART"]
        self._process_launcher(command, shell=False, close_fds=True)
        return {"ok": True, "started": True, "message": "Update-Installation wurde gestartet."}

    def _fetch_manifest(self) -> dict:
        parsed = urlparse(self.manifest_url)
        is_local = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
        if parsed.scheme != "https" and not (parsed.scheme == "http" and is_local):
            raise UpdateError("Der Update-Server muss über HTTPS erreichbar sein.")
        request = Request(self.manifest_url, headers={"Accept": "application/json", "User-Agent": f"LohnMail/{APP_VERSION}"})
        with self._opener(request, timeout=15) as response:
            raw = response.read(MAX_MANIFEST_BYTES + 1)
        if len(raw) > MAX_MANIFEST_BYTES:
            raise UpdateError("Das Update-Manifest ist zu groß.")
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise UpdateError("Der Update-Server hat kein gültiges Manifest geliefert.") from exc
        if not isinstance(data, dict):
            raise UpdateError("Ungültiges Update-Manifest.")
        if data.get("available") is False:
            return {"available": False}

        version = str(data.get("version", "") or "").strip()
        build = str(data.get("build", "") or "").strip()
        if not version or not build:
            raise UpdateError("Version oder Build fehlt im Update-Manifest.")
        download_url = _safe_download_url(data.get("download_url", ""))
        sha256 = str(data.get("sha256", "") or "").strip().lower()
        size = _safe_int(data.get("size", 0))
        if not download_url:
            raise UpdateError("Download-URL fehlt im Update-Manifest.")
        if not re.fullmatch(r"[0-9a-f]{64}", sha256):
            raise UpdateError("SHA-256 fehlt oder ist ungültig.")
        if size <= 0:
            raise UpdateError("Dateigröße fehlt im Update-Manifest.")
        notes = data.get("release_notes", [])
        if isinstance(notes, str):
            notes = [line.strip() for line in notes.splitlines() if line.strip()]
        if not isinstance(notes, list):
            notes = []
        required = data.get("required") is True
        required_reason = str(data.get("required_reason", "") or "").strip().lower()
        if not required or required_reason not in REQUIRED_REASONS:
            required_reason = ""
        return {
            "available": True,
            "version": version,
            "build": build,
            "download_url": download_url,
            "sha256": sha256,
            "size": size,
            "release_notes": [str(item)[:500] for item in notes[:20]],
            "required": required and bool(required_reason),
            "required_reason": required_reason,
        }

    @staticmethod
    def _verified_existing_download(updates: dict, manifest: dict) -> Path | None:
        if (
            str(updates.get("available_version", "")) != manifest["version"]
            or str(updates.get("available_build", "")) != manifest["build"]
            or str(updates.get("download_url", "")) != manifest["download_url"]
            or str(updates.get("sha256", "")).lower() != manifest["sha256"]
            or _safe_int(updates.get("size", 0)) != manifest["size"]
        ):
            return None

        path_value = str(updates.get("downloaded_path", "") or "").strip()
        if not path_value:
            return None
        path = Path(path_value)
        if (
            not path.is_file()
            or path.suffix.lower() not in {".exe", ".msi"}
            or path.stat().st_size != manifest["size"]
        ):
            return None
        if _sha256_file(path) != manifest["sha256"]:
            return None
        return path

    def _save_changes(self, changes: dict) -> dict:
        settings = self._load_settings()
        updates = dict(settings.get("updates", {}))
        updates.update(changes)
        settings["updates"] = updates
        self._save_settings(settings)
        return self._public_state(updates)

    @staticmethod
    def _progress_state(downloaded: int, total: int) -> dict:
        progress = round(downloaded * 100 / total) if total else 0
        return {
            "status": "downloading",
            "progress": min(100, max(0, progress)),
            "downloaded_bytes": downloaded,
            "total_bytes": total,
            "message": "Update wird heruntergeladen.",
        }

    def _public_state(self, updates: dict) -> dict:
        return {
            "installed_version": APP_VERSION,
            "installed_build": APP_BUILD,
            "last_checked_at": str(updates.get("last_checked_at", "") or ""),
            "auto_check": bool(updates.get("auto_check", True)),
            "status": str(updates.get("status", "idle") or "idle"),
            "available_version": str(updates.get("available_version", "") or ""),
            "available_build": str(updates.get("available_build", "") or ""),
            "required": bool(updates.get("required", False)),
            "progress": _safe_int(updates.get("progress", 0)),
            "downloaded_bytes": _safe_int(updates.get("downloaded_bytes", 0)),
            "total_bytes": _safe_int(updates.get("total_bytes", 0)),
            "release_notes": list(updates.get("release_notes", []) or []),
            "install_on_exit": bool(updates.get("install_on_exit", False)),
            "install_supported": self.platform == "win32",
            "required_reason": str(updates.get("required_reason", "") or ""),
            "message": str(updates.get("message", "") or ""),
        }

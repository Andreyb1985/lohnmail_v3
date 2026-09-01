from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


KEYCHAIN_SERVICE = "de.lohnmail.desktop.smtp"


class SecretStoreError(RuntimeError):
    pass


class SecretStore:
    """Store SMTP secrets in the operating system's protected credential store."""

    def __init__(self, windows_path: Path) -> None:
        self.windows_path = Path(windows_path)

    def set(self, secret_id: str, value: str) -> None:
        value = str(value or "")
        if not value:
            return
        if sys.platform == "win32":
            self._windows_set(secret_id, value)
            return
        if sys.platform == "darwin":
            self._macos_set(secret_id, value)
            return
        raise SecretStoreError("Das sichere Passwortspeichern wird auf diesem Betriebssystem nicht unterstützt.")

    def get(self, secret_id: str) -> str:
        if sys.platform == "win32":
            return self._windows_get(secret_id)
        if sys.platform == "darwin":
            return self._macos_get(secret_id)
        return ""

    def delete(self, secret_id: str) -> None:
        if sys.platform == "win32":
            data = self._windows_read()
            if secret_id in data:
                data.pop(secret_id, None)
                self._windows_write(data)
            return
        if sys.platform == "darwin":
            subprocess.run(
                ["security", "delete-generic-password", "-s", KEYCHAIN_SERVICE, "-a", secret_id],
                capture_output=True,
                text=True,
                check=False,
            )

    def _windows_read(self) -> dict[str, str]:
        if not self.windows_path.is_file():
            return {}
        try:
            data = json.loads(self.windows_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SecretStoreError("Das verschlüsselte SMTP-Passwort konnte nicht gelesen werden.") from exc
        return data if isinstance(data, dict) else {}

    def _windows_write(self, data: dict[str, str]) -> None:
        self.windows_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                prefix=f".{self.windows_path.name}.",
                suffix=".tmp",
                dir=self.windows_path.parent,
                delete=False,
            ) as temporary:
                json.dump(data, temporary, ensure_ascii=False, indent=2)
                temporary.flush()
                os.fsync(temporary.fileno())
                temporary_path = Path(temporary.name)
            os.replace(temporary_path, self.windows_path)
            temporary_path = None
        except OSError as exc:
            raise SecretStoreError("Das verschlüsselte SMTP-Passwort konnte nicht gespeichert werden.") from exc
        finally:
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError:
                    pass

    @staticmethod
    def _protect_windows(value: str) -> str:
        try:
            import win32crypt
        except ImportError as exc:
            raise SecretStoreError("Windows DPAPI ist nicht verfügbar. Bitte pywin32 installieren.") from exc
        try:
            encrypted = win32crypt.CryptProtectData(
                value.encode("utf-8"), "LohnMail SMTP", None, None, None, 0
            )
            return base64.b64encode(encrypted).decode("ascii")
        except Exception as exc:
            raise SecretStoreError("Windows konnte das SMTP-Passwort nicht verschlüsseln.") from exc

    @staticmethod
    def _unprotect_windows(value: str) -> str:
        try:
            import win32crypt
        except ImportError as exc:
            raise SecretStoreError("Windows DPAPI ist nicht verfügbar. Bitte pywin32 installieren.") from exc
        try:
            _description, decrypted = win32crypt.CryptUnprotectData(
                base64.b64decode(value), None, None, None, 0
            )
            return decrypted.decode("utf-8")
        except Exception as exc:
            raise SecretStoreError(
                "Das SMTP-Passwort gehört zu einem anderen Windows-Benutzer oder Computer. Bitte neu eingeben."
            ) from exc

    def _windows_set(self, secret_id: str, value: str) -> None:
        data = self._windows_read()
        data[secret_id] = self._protect_windows(value)
        self._windows_write(data)

    def _windows_get(self, secret_id: str) -> str:
        encrypted = self._windows_read().get(secret_id, "")
        return self._unprotect_windows(encrypted) if encrypted else ""

    @staticmethod
    def _macos_set(secret_id: str, value: str) -> None:
        try:
            subprocess.run(
                [
                    "security", "add-generic-password", "-U",
                    "-s", KEYCHAIN_SERVICE, "-a", secret_id, "-w", value,
                ],
                capture_output=True,
                text=True,
                check=True,
            )
        except (FileNotFoundError, subprocess.CalledProcessError) as exc:
            raise SecretStoreError("Das SMTP-Passwort konnte nicht im macOS-Schlüsselbund gespeichert werden.") from exc

    @staticmethod
    def _macos_get(secret_id: str) -> str:
        try:
            result = subprocess.run(
                ["security", "find-generic-password", "-w", "-s", KEYCHAIN_SERVICE, "-a", secret_id],
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError:
            return ""
        return result.stdout.rstrip("\r\n") if result.returncode == 0 else ""

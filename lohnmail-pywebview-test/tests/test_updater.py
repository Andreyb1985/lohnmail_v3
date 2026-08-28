from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from urllib.error import URLError

from ui_web.updater import UpdateService


class FakeResponse:
    def __init__(self, payload: bytes, *, content_length: int | None = None) -> None:
        self.payload = payload
        self.offset = 0
        self.headers = {}
        if content_length is not None:
            self.headers["Content-Length"] = str(content_length)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            size = len(self.payload) - self.offset
        chunk = self.payload[self.offset:self.offset + size]
        self.offset += len(chunk)
        return chunk


class SettingsStore:
    def __init__(self, updates: dict | None = None) -> None:
        self.data = {"updates": dict(updates or {})}

    def load(self) -> dict:
        return json.loads(json.dumps(self.data))

    def save(self, value: dict) -> None:
        self.data = json.loads(json.dumps(value))


class UpdateServiceTests(unittest.TestCase):
    def make_service(self, store: SettingsStore, directory: Path, **kwargs) -> UpdateService:
        return UpdateService(
            settings_loader=store.load,
            settings_saver=store.save,
            download_dir=directory,
            manifest_url="https://updates.example.test/windows/latest",
            **kwargs,
        )

    @staticmethod
    def manifest(payload: bytes, **overrides) -> bytes:
        data = {
            "available": True,
            "version": "9.0.0",
            "build": "2099.01.01",
            "download_url": "https://updates.example.test/LohnMailSetup.exe",
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size": len(payload),
            "release_notes": ["Sicherheits- und Stabilitätskorrekturen"],
            "required": False,
            "required_reason": "",
        }
        data.update(overrides)
        return json.dumps(data).encode("utf-8")

    def test_check_reports_optional_update(self) -> None:
        payload = b"signed-installer"
        store = SettingsStore()
        with tempfile.TemporaryDirectory() as temp_dir:
            service = self.make_service(
                store,
                Path(temp_dir),
                opener=lambda request, timeout: FakeResponse(self.manifest(payload)),
            )
            state = service.check()

        self.assertEqual(state["status"], "available")
        self.assertEqual(state["available_version"], "9.0.0")
        self.assertEqual(state["release_notes"], ["Sicherheits- und Stabilitätskorrekturen"])

    def test_check_preserves_verified_download_for_same_release(self) -> None:
        payload = b"signed-installer"
        digest = hashlib.sha256(payload).hexdigest()

        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            installer = directory / "LohnMailSetup.exe"
            installer.write_bytes(payload)
            store = SettingsStore({
                "status": "ready",
                "available": True,
                "available_version": "9.0.0",
                "available_build": "2099.01.01",
                "download_url": "https://updates.example.test/LohnMailSetup.exe",
                "sha256": digest,
                "size": len(payload),
                "downloaded_path": str(installer),
                "downloaded_sha256": digest,
                "progress": 100,
            })
            service = self.make_service(
                store,
                directory,
                opener=lambda request, timeout: FakeResponse(self.manifest(payload)),
            )
            state = service.check()

            self.assertEqual(store.data["updates"]["downloaded_path"], str(installer))
            self.assertNotIn("downloaded_path", state)

        self.assertEqual(state["status"], "ready")
        self.assertEqual(state["progress"], 100)
        self.assertEqual(store.data["updates"]["downloaded_sha256"], digest)

    def test_required_update_needs_flag_and_allowlisted_reason(self) -> None:
        payload = b"signed-installer"
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SettingsStore()
            service = self.make_service(
                store,
                Path(temp_dir),
                opener=lambda request, timeout: FakeResponse(
                    self.manifest(payload, required=True, required_reason="marketing")
                ),
            )
            self.assertEqual(service.check()["status"], "available")

            service._opener = lambda request, timeout: FakeResponse(
                self.manifest(payload, required=False, required_reason="critical_security")
            )
            self.assertEqual(service.check()["status"], "available")

            service._opener = lambda request, timeout: FakeResponse(
                self.manifest(payload, required=True, required_reason="critical_security")
            )
            state = service.check()
            self.assertEqual(state["status"], "required")
            self.assertTrue(state["required"])

    def test_no_release_and_offline_check_are_nonfatal(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SettingsStore()
            service = self.make_service(
                store,
                Path(temp_dir),
                opener=lambda request, timeout: FakeResponse(b'{"available": false}'),
            )
            self.assertEqual(service.check()["status"], "current")

            def offline(request, timeout):
                raise URLError("offline")

            service._opener = offline
            state = service.check()

        self.assertEqual(state["status"], "error")
        self.assertIn("offline", state["message"])

    def test_download_verifies_size_hash_and_reports_progress(self) -> None:
        payload = b"installer-data" * 4096
        store = SettingsStore({
            "status": "available",
            "download_url": "https://updates.example.test/LohnMailSetup.exe",
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size": len(payload),
        })
        progress = []
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            service = self.make_service(
                store,
                directory,
                opener=lambda request, timeout: FakeResponse(payload, content_length=len(payload)),
            )
            state = service.download(progress.append)
            target = directory / "LohnMailSetup.exe"

            self.assertTrue(target.is_file())
            self.assertEqual(target.read_bytes(), payload)

        self.assertEqual(state["status"], "ready")
        self.assertEqual(state["progress"], 100)
        self.assertTrue(progress)

    def test_bad_download_is_removed(self) -> None:
        expected = b"expected"
        actual = b"corrupt"
        store = SettingsStore({
            "status": "available",
            "download_url": "https://updates.example.test/LohnMailSetup.exe",
            "sha256": hashlib.sha256(expected).hexdigest(),
            "size": len(actual),
        })
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            service = self.make_service(
                store,
                directory,
                opener=lambda request, timeout: FakeResponse(actual),
            )
            state = service.download()

            self.assertFalse((directory / "LohnMailSetup.exe").exists())
            self.assertFalse((directory / "LohnMailSetup.exe.part").exists())

        self.assertEqual(state["status"], "error")
        self.assertIn("Integritätsprüfung", state["message"])

    def test_interrupted_operation_is_recovered_only_at_startup(self) -> None:
        store = SettingsStore({"status": "downloading", "progress": 45})
        with tempfile.TemporaryDirectory() as temp_dir:
            service = self.make_service(store, Path(temp_dir))
            self.assertEqual(service.current_state()["status"], "downloading")
            state = service.recover_interrupted_state()

        self.assertEqual(state["status"], "error")
        self.assertIn("unterbrochen", state["message"])

    def test_installer_requires_windows_hash_and_signature(self) -> None:
        payload = b"installer"
        launched = []
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "LohnMailSetup.exe"
            path.write_bytes(payload)
            updates = {
                "status": "ready",
                "install_on_exit": True,
                "downloaded_path": str(path),
                "downloaded_sha256": hashlib.sha256(payload).hexdigest(),
            }

            non_windows = self.make_service(SettingsStore(updates), Path(temp_dir), platform="darwin")
            self.assertFalse(non_windows.install_on_exit()["started"])

            invalid = self.make_service(
                SettingsStore(updates),
                Path(temp_dir),
                platform="win32",
                signature_verifier=lambda candidate: (False, "Ungültige Signatur"),
                process_launcher=lambda *args, **kwargs: launched.append((args, kwargs)),
            )
            self.assertFalse(invalid.install_on_exit()["started"])
            self.assertFalse(launched)

            valid = self.make_service(
                SettingsStore(updates),
                Path(temp_dir),
                platform="win32",
                signature_verifier=lambda candidate: (True, ""),
                process_launcher=lambda *args, **kwargs: launched.append((args, kwargs)),
            )
            result = valid.install_on_exit()

        self.assertTrue(result["started"])
        self.assertEqual(launched[0][0][0][0], str(path))
        self.assertFalse(launched[0][1]["shell"])

    def test_preferences_preserve_unrelated_user_configuration(self) -> None:
        store = SettingsStore({"auto_check": True, "install_on_exit": False})
        unrelated = {
            "companies": [
                {
                    "id": "gesob",
                    "name": "GeSoB GmbH",
                    "excel_path": "/data/stammdaten.xlsx",
                }
            ],
            "active_company_id": "gesob",
            "email": {"smtp_server": "smtp.example.test"},
            "paths": {"output": "/data/Gesob_Lohn"},
        }
        store.data.update(copy.deepcopy(unrelated))

        with tempfile.TemporaryDirectory() as temp_dir:
            service = self.make_service(store, Path(temp_dir))
            state = service.set_preferences(
                auto_check=False,
                install_on_exit=True,
            )

        self.assertFalse(state["auto_check"])
        self.assertTrue(state["install_on_exit"])
        for key, value in unrelated.items():
            self.assertEqual(store.data[key], value)


if __name__ == "__main__":
    unittest.main()

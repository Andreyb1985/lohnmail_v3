from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from urllib.error import HTTPError, URLError

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
            history_database=directory / "lohnmail_history.sqlite3",
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
        self.assertIn("Internetverbindung", state["message"])
        self.assertNotIn("offline", state["message"])

    def test_http_403_is_reported_without_technical_http_error(self) -> None:
        def forbidden(request, timeout):
            raise HTTPError(request.full_url, 403, "Forbidden", hdrs=None, fp=None)

        with tempfile.TemporaryDirectory() as temp_dir:
            store = SettingsStore()
            service = self.make_service(store, Path(temp_dir), opener=forbidden)
            check_state = service.check()

            store = SettingsStore({
                "status": "available",
                "download_url": "https://updates.example.test/LohnMailSetup.exe",
                "sha256": "a" * 64,
                "size": 10,
            })
            service = self.make_service(store, Path(temp_dir), opener=forbidden)
            download_state = service.download()

        for state in (check_state, download_state):
            self.assertEqual(state["status"], "error")
            self.assertIn("Firewall", state["message"])
            self.assertNotIn("403", state["message"])
            self.assertNotIn("Forbidden", state["message"])

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

    def test_successful_install_is_confirmed_on_next_start(self) -> None:
        from ui_web.version import APP_BUILD, APP_VERSION

        store = SettingsStore({
            "status": "installing",
            "available_version": APP_VERSION,
            "available_build": APP_BUILD,
            "install_on_exit": False,
        })
        with tempfile.TemporaryDirectory() as temp_dir:
            state = self.make_service(store, Path(temp_dir)).recover_interrupted_state()

        self.assertEqual(state["status"], "current")
        self.assertIn("erfolgreich installiert", state["message"])

    def test_failed_install_is_reported_after_rollback(self) -> None:
        store = SettingsStore({
            "status": "installing",
            "available_version": "99.0.0",
            "available_build": "2099.01.01",
        })
        with tempfile.TemporaryDirectory() as temp_dir:
            state = self.make_service(store, Path(temp_dir)).recover_interrupted_state()

        self.assertEqual(state["status"], "error")
        self.assertIn("wiederhergestellt", state["message"])

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

    def test_test_build_accepts_zip_only_with_manifest_test_flag(self) -> None:
        payload = b"test-update-zip"
        manifest = self.manifest(
            payload,
            download_url="https://updates.example.test/LohnMail-2.0.1.zip",
            test_mode=True,
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            enabled_store = SettingsStore()
            enabled = self.make_service(
                enabled_store,
                Path(temp_dir),
                opener=lambda request, timeout: FakeResponse(manifest),
                test_updates_enabled=True,
            )
            self.assertEqual(enabled.check()["status"], "available")
            self.assertTrue(enabled_store.data["updates"]["test_mode"])

            disabled = self.make_service(
                SettingsStore(),
                Path(temp_dir),
                opener=lambda request, timeout: FakeResponse(manifest),
                test_updates_enabled=False,
            )
            self.assertEqual(disabled.check()["status"], "error")

    def test_test_zip_install_skips_signature_and_starts_helper(self) -> None:
        payload = b"test-update-zip"
        launched = []
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "LohnMail-2.0.1.zip"
            path.write_bytes(payload)
            store = SettingsStore({
                "status": "ready",
                "install_on_exit": True,
                "test_mode": True,
                "downloaded_path": str(path),
                "downloaded_sha256": hashlib.sha256(payload).hexdigest(),
            })
            service = self.make_service(
                store,
                Path(temp_dir),
                platform="win32",
                test_updates_enabled=True,
                signature_verifier=lambda candidate: self.fail("ZIP must not use Authenticode"),
                process_launcher=lambda *args, **kwargs: launched.append((args, kwargs)),
            )
            result = service.install_on_exit()
            helper = Path(temp_dir) / "install-test-update.ps1"
            helper_text = helper.read_text(encoding="utf-8-sig")
            command = launched[0][0][0]

        self.assertTrue(result["started"])
        self.assertIn("powershell.exe", command)
        self.assertNotEqual(Path(launched[0][1]["cwd"]).name.casefold(), "app")
        self.assertIn("-ParentProcessId", command)
        self.assertIn("-TargetBuild", command)
        self.assertIn("-RuntimeExecutable", command)
        self.assertIn("-RuntimeEntry", command)
        self.assertIn("Wait-ForProcessExit", helper_text)
        self.assertNotIn("Wait-Process -Id", helper_text)
        self.assertIn("Set-Location -LiteralPath $RootDir", helper_text)
        self.assertIn("[switch]$NonInteractive", helper_text)
        self.assertIn("Move-AppToBackup", helper_text)
        self.assertIn("$Attempt -le 40", helper_text)
        self.assertIn("Copy-Item", helper_text)
        self.assertNotIn("Expand-Archive", helper_text)
        self.assertIn("Expand-UpdateArchive", helper_text)
        self.assertIn("--lohnmail-update-check-db", helper_text)
        self.assertIn("--lohnmail-update-extract", helper_text)
        self.assertIn("--lohnmail-update-selftest", helper_text)
        self.assertIn("Test-NewApplication", helper_text)
        self.assertIn("Invoke-UpdateRuntime", helper_text)
        self.assertIn("System.Diagnostics.ProcessStartInfo", helper_text)
        self.assertIn("WaitForExit()", helper_text)
        self.assertIn("$RuntimeExecutable $RuntimeEntry", helper_text)
        self.assertIn("Invoke-UpdateRuntime $NewRuntime $RuntimeArguments", helper_text)
        self.assertNotIn("@(& $Runtime", helper_text)
        self.assertIn("$FrozenBuild -and -not $SourceHasExecutable", helper_text)
        self.assertNotIn("sqlite-update-check.py", helper_text)
        self.assertNotIn("app-update-selftest.py", helper_text)
        self.assertNotIn("extract-update-archive.py", helper_text)
        self.assertNotIn("Python-Laufzeit fehlt", helper_text)
        self.assertIn("OldHistoryHash", helper_text)
        self.assertLess(
            helper_text.index("Test-HistoryDatabase $RuntimeExecutable"),
            helper_text.index("$OldHistoryHash = if (Test-Path $HistoryDb)"),
        )
        self.assertNotIn("required={'schema_meta'", helper_text)
        self.assertIn("SQLITE_CHECK_FAILED", helper_text)

    def test_windows_launcher_keeps_working_directory_outside_app(self) -> None:
        launcher = Path(__file__).resolve().parent.parent / "INSTALL-AND-START-WINDOWS.cmd"
        text = launcher.read_text(encoding="utf-8")

        self.assertIn('set "APP_DIR=%ROOT_DIR%App"', text)
        self.assertIn('cd /d "%ROOT_DIR%"', text)
        self.assertIn('if exist "%APP_DIR%\\LohnMail.exe"', text)
        self.assertIn('"%APP_DIR%\\LohnMail.exe"', text)
        self.assertIn('"%PYTHON_EXE%" "%APP_DIR%\\main.py"', text)
        self.assertNotIn('cd /d "%~dp0App"', text)
        self.assertNotIn('cd /d "%~dp0"', text)

    def test_windows_build_creates_exe_only_update_package(self) -> None:
        build_script = Path(__file__).resolve().parent.parent / "BUILD-WINDOWS.ps1"
        text = build_script.read_text(encoding="utf-8")

        self.assertIn('--onedir', text)
        self.assertIn('--contents-directory .', text)
        self.assertIn('-m pytest -q', text)
        self.assertIn('Es wird keine Windows-Version erstellt', text)
        self.assertIn('dist\\LohnMail\\*', text)
        self.assertIn('LohnMail.exe', text)
        self.assertIn('LohnMail/App/LohnMail.exe', text)
        self.assertIn('package_kind = "windows-pyinstaller-onedir"', text)
        self.assertIn('(Settings|Companies)', text)
        self.assertIn('Get-FileHash $UpdateZip -Algorithm SHA256', text)
        self.assertNotIn('Copy-Item -Recurse -Force ".\\*" $UpdatePackageApp', text)
        self.assertIn('windows_root_launcher.cs', text)
        self.assertIn('LohnMail.RootLauncher.exe', text)
        self.assertIn('Microsoft.NET\\Framework64\\v4.0.30319\\csc.exe', text)
        self.assertNotIn('-CompilerOptions', text)
        self.assertIn('[System.IO.File]::WriteAllText(', text)
        self.assertIn('System.Text.UTF8Encoding($false)', text)
        self.assertIn('(Join-Path $ReleaseRoot "LohnMail.exe")', text)

    def test_root_launcher_starts_replaceable_app_runtime(self) -> None:
        root = Path(__file__).resolve().parent.parent
        source = (root / "windows_root_launcher.cs").read_text(encoding="utf-8")
        self.assertIn('Path.Combine(rootDirectory, "App", "LohnMail.exe")', source)
        self.assertIn("UseShellExecute = true", source)
        runtime = (root / "pywebview_app.py").read_text(encoding="utf-8")
        self.assertIn("_install_windows_root_launcher()", runtime)
        self.assertIn('app_directory.parent / "LohnMail.exe"', runtime)

    def test_windows_native_caption_is_forced_to_light_application_colors(self) -> None:
        runtime = (Path(__file__).resolve().parent.parent / "pywebview_app.py").read_text(encoding="utf-8")
        self.assertIn('_windows_colorref("#f5f8fb")', runtime)
        self.assertIn('_windows_colorref("#0f172a")', runtime)
        self.assertIn("DwmSetWindowAttribute", runtime)

    def test_install_preflight_accepts_valid_older_sqlite_schema(self) -> None:
        import sqlite3
        from contextlib import closing

        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            database = directory / "lohnmail_history.sqlite3"
            with closing(sqlite3.connect(database)) as connection:
                connection.execute("CREATE TABLE legacy_history (id INTEGER PRIMARY KEY)")
                connection.commit()
            service = self.make_service(SettingsStore(), directory)
            ok, message = service._check_history_database()

        self.assertTrue(ok)
        self.assertEqual(message, "")

    def test_install_preflight_rejects_unreadable_sqlite_without_closing_app(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            (directory / "lohnmail_history.sqlite3").write_bytes(b"not-a-sqlite-database")
            service = self.make_service(SettingsStore(), directory)
            ok, message = service._check_history_database()

        self.assertFalse(ok)
        self.assertIn("LohnMail bleibt geöffnet", message)

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

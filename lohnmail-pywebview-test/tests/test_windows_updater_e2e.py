from __future__ import annotations

import sqlite3
import subprocess
import sys
import tempfile
import unittest
import venv
import zipfile
from contextlib import closing
from pathlib import Path

from ui_web.updater import UpdateService


@unittest.skipUnless(sys.platform == "win32", "real updater scenario requires Windows")
class WindowsUpdaterEndToEndTests(unittest.TestCase):
    def test_update_waits_for_locked_app_and_preserves_local_data(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "LohnMail"
            app = root / "App"
            settings = root / "Settings"
            companies = root / "Companies"
            updates = settings / "updates"
            for directory in (app, updates, companies):
                directory.mkdir(parents=True, exist_ok=True)

            (app / "main.py").write_text("print('old')\n", encoding="utf-8")
            venv.EnvBuilder(with_pip=False).create(app / ".venv")
            settings_json = settings / "settings.json"
            settings_json.write_text('{"companies": [], "selected_company_id": ""}\n', encoding="utf-8")
            company_file = companies / "keep-me.txt"
            company_file.write_text("local company data\n", encoding="utf-8")
            database = settings / "lohnmail_history.sqlite3"
            with closing(sqlite3.connect(database)) as connection:
                connection.execute("CREATE TABLE history (id INTEGER PRIMARY KEY, value TEXT)")
                connection.execute("INSERT INTO history(value) VALUES ('keep-me')")
                connection.commit()

            archive = updates / "LohnMail-2.0.3-test-update.zip"
            new_main = '''from __future__ import annotations
import sqlite3
import sys
from pathlib import Path

if "--lohnmail-update-selftest" in sys.argv:
    index = sys.argv.index("--lohnmail-update-selftest")
    if sys.argv[index + 1:index + 3] != ["2.0.3", "windows-e2e"]:
        raise SystemExit(2)
    if "--history-db" in sys.argv:
        database = Path(sys.argv[sys.argv.index("--history-db") + 1]).resolve()
        connection = sqlite3.connect(database.as_uri() + "?mode=rw", uri=True)
        try:
            if connection.execute("PRAGMA quick_check").fetchone() != ("ok",):
                raise SystemExit(3)
        finally:
            connection.close()
    raise SystemExit(0)
print("new")
'''
            with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as target:
                target.writestr("LohnMail/App/main.py", new_main)
                target.writestr("LohnMail/App/core/__init__.py", "")
                target.writestr("LohnMail/App/core/config.py", "")
                target.writestr("LohnMail/App/ui_web/__init__.py", "")
                target.writestr("LohnMail/App/ui_web/updater.py", "")
                target.writestr(
                    "LohnMail/App/ui_web/version.py",
                    'APP_VERSION = "2.0.3"\nAPP_BUILD = "windows-e2e"\n',
                )

            service = UpdateService(
                settings_loader=lambda: {"updates": {}},
                settings_saver=lambda value: None,
                download_dir=updates,
                history_database=database,
                platform="win32",
                test_updates_enabled=True,
            )
            helper = service._write_test_zip_installer(archive)

            lock_process = subprocess.Popen(
                ["cmd.exe", "/d", "/s", "/c", "ping -n 4 127.0.0.1 >nul"],
                cwd=app,
            )
            try:
                result = subprocess.run(
                    [
                        "powershell.exe",
                        "-NoProfile",
                        "-NonInteractive",
                        "-ExecutionPolicy",
                        "Bypass",
                        "-File",
                        str(helper),
                        "-Archive",
                        str(archive),
                        "-AppDir",
                        str(app),
                        "-RootDir",
                        str(root),
                        "-ProcessId",
                        "0",
                        "-ParentProcessId",
                        str(lock_process.pid),
                        "-TargetVersion",
                        "2.0.3",
                        "-TargetBuild",
                        "windows-e2e",
                        "-RuntimeExecutable",
                        sys.executable,
                        "-RuntimeEntry",
                        str(Path(__file__).resolve().parent.parent / "main.py"),
                        "-NonInteractive",
                    ],
                    cwd=root,
                    capture_output=True,
                    text=True,
                    timeout=120,
                    check=False,
                )
            finally:
                lock_process.wait(timeout=10)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('APP_VERSION = "2.0.3"', (app / "ui_web" / "version.py").read_text(encoding="utf-8"))
            self.assertEqual(settings_json.read_text(encoding="utf-8"), '{"companies": [], "selected_company_id": ""}\n')
            self.assertEqual(company_file.read_text(encoding="utf-8"), "local company data\n")
            with closing(sqlite3.connect(database)) as connection:
                self.assertEqual(connection.execute("PRAGMA quick_check").fetchone(), ("ok",))
                self.assertEqual(connection.execute("SELECT value FROM history").fetchone(), ("keep-me",))
            self.assertIn("SUCCESS version=2.0.3", (updates / "update-install.log").read_text(encoding="utf-8-sig"))
            self.assertFalse((root / "App.update-backup").exists())


if __name__ == "__main__":
    unittest.main()

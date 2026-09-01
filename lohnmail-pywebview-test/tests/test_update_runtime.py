from __future__ import annotations

import sqlite3
import stat
import tempfile
import unittest
import zipfile
from contextlib import closing
from pathlib import Path

from ui_web.update_runtime import (
    check_history_database,
    extract_update_archive,
    run_self_test,
    run_update_command,
)
from ui_web.version import APP_BUILD, APP_VERSION


class UpdateRuntimeTests(unittest.TestCase):
    def test_database_check_accepts_valid_database_and_closes_it(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "lohnmail_history.sqlite3"
            with closing(sqlite3.connect(database)) as connection:
                connection.execute("CREATE TABLE history (id INTEGER PRIMARY KEY)")
                connection.commit()

            check_history_database(database)
            renamed = database.with_suffix(".checked")
            database.replace(renamed)

        self.assertTrue(renamed.name.endswith(".checked"))

    def test_database_check_does_not_create_missing_database(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "missing.sqlite3"
            check_history_database(database)
            self.assertFalse(database.exists())

    def test_database_check_rejects_invalid_database(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "invalid.sqlite3"
            database.write_bytes(b"not sqlite")
            with self.assertRaises(sqlite3.DatabaseError):
                check_history_database(database)

    def test_archive_extraction_accepts_compiled_windows_layout(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            archive = directory / "update.zip"
            with zipfile.ZipFile(archive, "w") as target:
                target.writestr("LohnMail/App/LohnMail.exe", b"test-exe")
                target.writestr("LohnMail/App/_internal/module.pyd", b"test-module")

            destination = directory / "extracted"
            extract_update_archive(archive, destination)

            self.assertEqual(
                (destination / "LohnMail" / "App" / "LohnMail.exe").read_bytes(),
                b"test-exe",
            )

    def test_archive_extraction_rejects_parent_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            archive = directory / "unsafe.zip"
            with zipfile.ZipFile(archive, "w") as target:
                target.writestr("../outside.txt", "unsafe")

            with self.assertRaisesRegex(RuntimeError, "unsafe archive path"):
                extract_update_archive(archive, directory / "extracted")
            self.assertFalse((directory / "outside.txt").exists())

    def test_archive_extraction_rejects_symbolic_link(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            archive = directory / "symlink.zip"
            link = zipfile.ZipInfo("LohnMail/App/link")
            link.create_system = 3
            link.external_attr = (stat.S_IFLNK | 0o777) << 16
            with zipfile.ZipFile(archive, "w") as target:
                target.writestr(link, "LohnMail.exe")

            with self.assertRaisesRegex(RuntimeError, "symbolic links"):
                extract_update_archive(archive, directory / "extracted")

    def test_self_test_checks_version_build_and_sqlite(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "history.sqlite3"
            with closing(sqlite3.connect(database)) as connection:
                connection.execute("CREATE TABLE history (id INTEGER PRIMARY KEY)")
                connection.commit()

            run_self_test(APP_VERSION, APP_BUILD, database)
            with self.assertRaisesRegex(RuntimeError, "expected build"):
                run_self_test(APP_VERSION, "wrong-build", database)

    def test_command_router_returns_exit_codes_without_starting_ui(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "history.sqlite3"
            with closing(sqlite3.connect(database)) as connection:
                connection.execute("CREATE TABLE history (id INTEGER PRIMARY KEY)")
                connection.commit()

            self.assertEqual(
                run_update_command(["--lohnmail-update-check-db", str(database)]),
                0,
            )
            self.assertEqual(
                run_update_command(["--lohnmail-update-selftest", APP_VERSION, "wrong"]),
                1,
            )
            self.assertIsNone(run_update_command([]))


if __name__ == "__main__":
    unittest.main()

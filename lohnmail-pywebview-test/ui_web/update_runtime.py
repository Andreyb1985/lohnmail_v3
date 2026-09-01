from __future__ import annotations

import os
import sqlite3
import sys
import zipfile
from pathlib import Path


CHECK_DATABASE_FLAG = "--lohnmail-update-check-db"
EXTRACT_ARCHIVE_FLAG = "--lohnmail-update-extract"
SELF_TEST_FLAG = "--lohnmail-update-selftest"
HISTORY_DATABASE_FLAG = "--history-db"
UPDATE_FLAGS = {CHECK_DATABASE_FLAG, EXTRACT_ARCHIVE_FLAG, SELF_TEST_FLAG}


def check_history_database(database: Path) -> None:
    """Run a physical SQLite integrity check without creating a missing file."""
    database = database.expanduser().resolve()
    if not database.is_file():
        return
    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(
            database.as_uri() + "?mode=rw",
            uri=True,
            timeout=10,
        )
        connection.execute("PRAGMA busy_timeout=10000")
        result = connection.execute("PRAGMA quick_check").fetchall()
        connection.execute("SELECT name FROM sqlite_master LIMIT 1").fetchall()
        if result != [("ok",)]:
            raise sqlite3.DatabaseError(str(result))
    finally:
        if connection is not None:
            connection.close()


def extract_update_archive(archive: Path, target: Path) -> None:
    """Extract a ZIP after CRC, traversal and symlink validation."""
    archive = archive.expanduser().resolve()
    target = target.expanduser().resolve()
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "r") as source:
        broken_member = source.testzip()
        if broken_member:
            raise RuntimeError(f"CRC error in {broken_member}")
        for member in source.infolist():
            destination = (target / member.filename).resolve()
            try:
                inside_target = os.path.commonpath((str(target), str(destination))) == str(target)
            except ValueError:
                inside_target = False
            if not inside_target:
                raise RuntimeError(f"unsafe archive path: {member.filename}")
            file_type = (member.external_attr >> 16) & 0o170000
            if file_type == 0o120000:
                raise RuntimeError(f"symbolic links are not allowed: {member.filename}")
        source.extractall(target)


def run_self_test(
    expected_version: str,
    expected_build: str,
    history_database: Path | None = None,
) -> None:
    from ui_web.version import APP_BUILD, APP_VERSION

    if APP_VERSION != expected_version:
        raise RuntimeError(f"expected {expected_version}, installed {APP_VERSION}")
    if APP_BUILD != expected_build:
        raise RuntimeError(f"expected build {expected_build}, installed {APP_BUILD}")
    import core.config  # noqa: F401
    import ui_web.updater  # noqa: F401

    if history_database is not None:
        check_history_database(history_database)


def _history_argument(arguments: list[str]) -> Path | None:
    if HISTORY_DATABASE_FLAG not in arguments:
        return None
    index = arguments.index(HISTORY_DATABASE_FLAG)
    if index + 1 >= len(arguments):
        raise ValueError(f"{HISTORY_DATABASE_FLAG} requires a path")
    value = arguments[index + 1].strip()
    return Path(value) if value else None


def run_update_command(arguments: list[str] | None = None) -> int | None:
    """Handle updater-only commands before the desktop UI is imported."""
    values = list(sys.argv[1:] if arguments is None else arguments)
    selected = next((flag for flag in UPDATE_FLAGS if flag in values), None)
    if selected is None:
        return None
    try:
        index = values.index(selected)
        if selected == CHECK_DATABASE_FLAG:
            check_history_database(Path(values[index + 1]))
        elif selected == EXTRACT_ARCHIVE_FLAG:
            extract_update_archive(Path(values[index + 1]), Path(values[index + 2]))
        else:
            run_self_test(values[index + 1], values[index + 2], _history_argument(values))
        return 0
    except Exception as exc:
        if sys.stderr is not None:
            sys.stderr.write(f"{type(exc).__name__}: {exc}\n")
        return 1

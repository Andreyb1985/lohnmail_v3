import importlib.util
import os
import sys
from pathlib import Path


def ensure_project_python() -> None:
    """Use the project venv when LohnMail was started with another Python."""
    if importlib.util.find_spec("PySide6") is not None:
        return

    project_dir = Path(__file__).resolve().parent
    relative_python = Path("Scripts/python.exe") if os.name == "nt" else Path("bin/python")
    project_python = project_dir / ".venv" / relative_python
    if project_python.is_file():
        os.execv(str(project_python), [str(project_python), *sys.argv])


if __name__ == "__main__":
    ensure_project_python()

from core.config import ensure_settings_file


def run_widgets() -> int:
    from PySide6.QtWidgets import QApplication
    from ui.main_window import MainWindow

    ensure_settings_file()
    app = QApplication(sys.argv)
    app.setApplicationName("LohnMail")
    window = MainWindow()
    window.show()
    return app.exec()


def run_web() -> int:
    from ui_web.app import run
    return run()


def main() -> int:
    ui_mode = os.environ.get("LOHNMAIL_UI", "web").strip().lower()
    if ui_mode in {"widgets", "classic", "old"}:
        return run_widgets()
    try:
        return run_web()
    except Exception as exc:
        print(f"[LohnMail] Web UI konnte nicht gestartet werden: {exc}", file=sys.stderr)
        print("[LohnMail] Fallback auf Widgets UI. Setze LOHNMAIL_UI=web für WebEngine.", file=sys.stderr)
        return run_widgets()


if __name__ == "__main__":
    raise SystemExit(main())

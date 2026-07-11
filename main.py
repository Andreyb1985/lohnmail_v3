import os
import sys

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

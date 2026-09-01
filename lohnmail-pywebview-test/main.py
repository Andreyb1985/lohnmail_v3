from __future__ import annotations

from ui_web.update_runtime import run_update_command


if __name__ == "__main__":
    update_exit_code = run_update_command()
    if update_exit_code is not None:
        raise SystemExit(update_exit_code)

    from pywebview_app import run

    run()

from __future__ import annotations

import sys

from core.distribution import is_store_build
from core.logging_config import configure_logging, show_fatal_error
from ui_web.update_runtime import SELF_TEST_FLAG, run_update_command


if __name__ == "__main__":
    logger = configure_logging()
    if not is_store_build() or SELF_TEST_FLAG in sys.argv[1:]:
        update_exit_code = run_update_command()
        if update_exit_code is not None:
            raise SystemExit(update_exit_code)

    try:
        from pywebview_app import run

        run()
    except Exception:
        logger.exception("Unbehandelter Fehler beim Start")
        show_fatal_error()
        raise SystemExit(1)

from __future__ import annotations

import logging
import platform
import sys
from logging.handlers import RotatingFileHandler

from core.config import LOGS_DIR
from core.distribution import distribution_label
from ui_web.version import APP_BUILD, APP_VERSION


LOGGER_NAME = "lohnmail"


def configure_logging() -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    if logger.handlers:
        return logger
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        LOGS_DIR / "lohnmail.log",
        maxBytes=2 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.info(
        "LohnMail start version=%s build=%s distribution=%s platform=%s architecture=%s",
        APP_VERSION,
        APP_BUILD,
        distribution_label(),
        platform.system(),
        platform.machine(),
    )
    return logger


def show_fatal_error() -> None:
    message = (
        "LohnMail konnte nicht gestartet werden. Bitte starten Sie die Anwendung erneut. "
        "Falls das Problem bestehen bleibt, wenden Sie sich an den LohnMail-Support."
    )
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.user32.MessageBoxW(None, message, "LohnMail", 0x10)
            return
        except Exception:
            pass
    if sys.stderr is not None:
        sys.stderr.write(message + "\n")

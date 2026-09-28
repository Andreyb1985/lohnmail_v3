from __future__ import annotations

import mimetypes
import sys

from core.storage_paths import prepare_storage_or_exit

if __name__ == "__main__":
    prepare_storage_or_exit()

from ui_web.update_runtime import run_update_command


def _initialize_mimetypes_for_macos_sandbox() -> None:
    """Avoid probing system MIME files that the Mac App Sandbox cannot read."""
    if sys.platform != "darwin":
        return
    mimetypes.knownfiles = []
    mimetypes.init()


if __name__ == "__main__":
    _initialize_mimetypes_for_macos_sandbox()
    update_exit_code = run_update_command()
    if update_exit_code is not None:
        raise SystemExit(update_exit_code)

    from pywebview_app import run

    run()

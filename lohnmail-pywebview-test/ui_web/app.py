from __future__ import annotations


def run() -> int:
    """Backward-compatible entry point for the pywebview test application."""
    from pywebview_app import run as run_pywebview

    run_pywebview()
    return 0

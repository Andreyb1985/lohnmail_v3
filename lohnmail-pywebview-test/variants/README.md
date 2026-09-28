# LohnMail variants

The application code in `core/`, `ui_web/`, `web/`, `main.py`, and
`pywebview_app.py` is the single reference implementation. Product fixes are
made there first.

- `etalon/` starts the reference implementation directly with Python.
- `macos/` contains macOS preview and Mac App Store build entry points.
- `windows/` contains the Windows build entry point.

Platform folders contain only platform-specific launch/build configuration.
They must not contain copied customer data, settings, licenses, reports, or a
second copy of the application source.

# LohnMail v2 — WebEngine POC

This build introduces a proof-of-concept UI path using **PySide6 + QWebEngineView**.

## Goal

Render the approved Frozen Design visually with HTML/CSS inside the desktop app before reconnecting business logic.

## Run

Default:

```bash
python main.py
```

Fallback to the previous QWidget UI:

```bash
LOHNMAIL_UI=widgets python main.py
```

## Requirements

```bash
python -m pip install PySide6 PySide6-Addons
```

If WebEngine is unavailable, `main.py` falls back to the QWidget UI.

## Scope of this POC

Implemented:

- WebEngine desktop shell
- Sidebar
- Topbar
- Footer
- Dashboard visual layout
- Placeholder JS/Python bridge

Not implemented yet:

- Core business logic calls
- Real dashboard data
- Other pages
- File dialogs / processing / mail flow

The purpose of this build is visual validation only.

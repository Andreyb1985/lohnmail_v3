# LohnMail pywebview test

This is an isolated renderer prototype. The regular PySide6 application in the
parent directory is not changed.

## Start on macOS

```bash
cd /Users/strelok/Downloads/lm-13/lohnmail-pywebview-test
../.venv/bin/python pywebview_app.py
```

The window uses WKWebView on macOS. On Windows pywebview selects Edge WebView2
when the WebView2 Runtime is available.

Test settings, the SQLite history and generated company folders are isolated in
`~/Library/Application Support/LohnMailPywebviewTest` on macOS. They do not
modify the regular LohnMail data directory.

For the portable Windows test package, use this approved layout:

```text
LohnMail/
|-- App/        program files and requirements-windows.txt
|-- Settings/   settings.json, license data, history and saved sessions
`-- Companies/  Lohn_<company name>/ PDF, Excel and delivery reports
```

When the program starts from `LohnMail/App`, it automatically uses the sibling
`Settings` and `Companies` folders. `LOHNMAIL_DATA_DIR` can explicitly select a
different root when needed.

## Windows executable with the LohnMail taskbar icon

Running `python main.py` shows the Python interpreter icon because pywebview's
WinForms backend takes its Windows icon from the executable. Build the actual
LohnMail executable in PowerShell:

```powershell
.\BUILD-WINDOWS.ps1
```

The result is `dist\LohnMail\LohnMail.exe`. Its taskbar/window icon is embedded
from `web\assets\brand\LohnMail.ico`.

The runtime path no longer requires PySide6. Native file dialogs are provided
by pywebview, background jobs use Python threads and files/URLs are opened with
platform-native commands.

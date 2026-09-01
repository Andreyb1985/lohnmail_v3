# LohnMail Desktop

Production desktop client based on pywebview. It uses WKWebView on macOS and
Edge WebView2 on Windows.

## Start on macOS

```bash
cd /Users/strelok/Downloads/lm-13/lohnmail-pywebview-test
../.venv/bin/python pywebview_app.py
```

The window uses WKWebView on macOS. On Windows pywebview selects Edge WebView2
when the WebView2 Runtime is available.

On macOS, settings, SQLite history and generated company folders are stored in
`~/Library/Application Support/LohnMail`.

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

The runtime assigns the LohnMail icon to the native Windows window. For the
installed application and Windows file metadata, build the actual LohnMail
executable in PowerShell:

```powershell
.\BUILD-WINDOWS.ps1
```

The result is `dist\LohnMail\LohnMail.exe`. Its multi-resolution taskbar/window
icon is embedded from `web\assets\brand\LohnMail.ico`.

The script also creates the clean portable directory `release\LohnMail` with
`App`, `Settings` and `Companies`. It copies only `settings_template.json` as
the initial `Settings\settings.json` and fails if license data, a machine ID,
workflow sessions, SQLite history, company records or an SMTP password appear
in the release directory. Create the customer ZIP only from this verified
directory, never from a locally used `LohnMail` data folder.

The runtime path no longer requires PySide6. Native file dialogs are provided
by pywebview, background jobs use Python threads and files/URLs are opened with
platform-native commands.

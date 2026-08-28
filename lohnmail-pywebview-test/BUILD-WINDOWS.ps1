$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    py -m venv .venv
}

& ".venv\Scripts\python.exe" -m pip install --upgrade pip
& ".venv\Scripts\python.exe" -m pip install -r requirements-build-windows.txt

& ".venv\Scripts\python.exe" -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --onedir `
    --contents-directory . `
    --name LohnMail `
    --icon "web\assets\brand\LohnMail.ico" `
    --collect-all webview `
    --add-data "web;web" `
    --add-data "settings_template.json;." `
    main.py

Write-Host ""
Write-Host "Build fertig: dist\LohnMail\LohnMail.exe" -ForegroundColor Green

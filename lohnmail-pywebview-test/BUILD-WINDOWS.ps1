$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    # Use the interpreter selected by the caller/CI. The Windows `py` launcher
    # may otherwise silently choose a newer globally installed Python.
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "Die Windows-Build-Umgebung konnte nicht erstellt werden." }
}

& ".venv\Scripts\python.exe" -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "pip konnte nicht aktualisiert werden." }
& ".venv\Scripts\python.exe" -m pip install -r requirements-build-windows.txt
if ($LASTEXITCODE -ne 0) { throw "Die Windows-Build-Abhängigkeiten konnten nicht installiert werden." }

& ".venv\Scripts\python.exe" -m pytest -q
if ($LASTEXITCODE -ne 0) { throw "Die Tests sind fehlgeschlagen. Es wird keine Windows-Version erstellt." }

& ".venv\Scripts\python.exe" -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --onedir `
    --contents-directory . `
    --name LohnMail `
    --icon "web\assets\brand\LohnMail.ico" `
    --version-file "windows_version_info.txt" `
    --collect-all webview `
    --add-data "web;web" `
    --add-data "settings_template.json;." `
    main.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller konnte LohnMail.exe nicht erstellen." }

$ReleaseRoot = Join-Path $PSScriptRoot "release\LohnMail"
$ReleaseApp = Join-Path $ReleaseRoot "App"
$ReleaseSettings = Join-Path $ReleaseRoot "Settings"
$ReleaseCompanies = Join-Path $ReleaseRoot "Companies"

if (Test-Path $ReleaseRoot) {
    Remove-Item -Recurse -Force $ReleaseRoot
}

New-Item -ItemType Directory -Force $ReleaseApp, $ReleaseSettings, $ReleaseCompanies | Out-Null
Copy-Item -Recurse -Force "dist\LohnMail\*" $ReleaseApp
Copy-Item -Force "settings_template.json" (Join-Path $ReleaseSettings "settings.json")
Copy-Item -Force "INSTALL-AND-START-WINDOWS.cmd" (Join-Path $ReleaseRoot "INSTALL-AND-START-WINDOWS.cmd")
Copy-Item -Force "README-WINDOWS.txt" (Join-Path $ReleaseRoot "README-WINDOWS.txt")
New-Item -ItemType File -Force (Join-Path $ReleaseCompanies ".gitkeep") | Out-Null

$ForbiddenFiles = @(
    "license.json",
    "machine_id",
    "workflow_sessions.json",
    "lohnmail_history.sqlite3",
    "settings.before-legacy-import.json"
)
foreach ($ForbiddenFile in $ForbiddenFiles) {
    if (Get-ChildItem -Path $ReleaseRoot -Recurse -File -Filter $ForbiddenFile) {
        throw "Unsichere Release-Datei gefunden: $ForbiddenFile"
    }
}

$ReleaseSettingsData = Get-Content (Join-Path $ReleaseSettings "settings.json") -Raw | ConvertFrom-Json
if ($ReleaseSettingsData.companies.Count -ne 0 -or $ReleaseSettingsData.selected_company_id) {
    throw "Release-settings.json enthält Mandantendaten."
}
if ($ReleaseSettingsData.smtp.password) {
    throw "Release-settings.json enthält ein SMTP-Passwort."
}

$VersionSource = Get-Content "ui_web\version.py" -Raw
$VersionMatch = [regex]::Match($VersionSource, 'APP_VERSION\s*=\s*"([^"]+)"')
$BuildMatch = [regex]::Match($VersionSource, 'APP_BUILD\s*=\s*"([^"]+)"')
if (-not $VersionMatch.Success -or -not $BuildMatch.Success) {
    throw "Version oder Build konnte nicht aus ui_web\version.py gelesen werden."
}
$AppVersion = $VersionMatch.Groups[1].Value
$AppBuild = $BuildMatch.Groups[1].Value
$UpdatePackageRoot = Join-Path $PSScriptRoot "release\update-package"
$UpdatePackageApp = Join-Path $UpdatePackageRoot "LohnMail\App"
$UpdateZip = Join-Path $PSScriptRoot "release\LohnMail-$AppVersion-build-$AppBuild-exe-update.zip"
$UpdateManifest = Join-Path $PSScriptRoot "release\LohnMail-$AppVersion-build-$AppBuild-exe-update.json"
if (Test-Path $UpdatePackageRoot) { Remove-Item -Recurse -Force $UpdatePackageRoot }
if (Test-Path $UpdateZip) { Remove-Item -Force $UpdateZip }
New-Item -ItemType Directory -Force $UpdatePackageApp | Out-Null
Copy-Item -Recurse -Force "dist\LohnMail\*" $UpdatePackageApp
if (-not (Test-Path (Join-Path $UpdatePackageApp "LohnMail.exe"))) {
    throw "Das EXE-Update enthält keine LohnMail.exe."
}
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory(
    $UpdatePackageRoot,
    $UpdateZip,
    [System.IO.Compression.CompressionLevel]::Optimal,
    $false
)
$ZipFile = [System.IO.Compression.ZipFile]::OpenRead($UpdateZip)
try {
    $ExeEntry = $ZipFile.Entries | Where-Object { $_.FullName -eq "LohnMail/App/LohnMail.exe" } | Select-Object -First 1
    if (-not $ExeEntry) { throw "Das Update-Archiv enthält LohnMail/App/LohnMail.exe nicht." }
    $UnsafeEntry = $ZipFile.Entries | Where-Object {
        $_.FullName -match '(^|/)\.\.(/|$)' -or
        $_.FullName -match '(^|/)(Settings|Companies)(/|$)' -or
        $_.FullName -match '(license\.json|machine_id|lohnmail_history\.sqlite3|workflow_sessions\.json)'
    } | Select-Object -First 1
    if ($UnsafeEntry) { throw "Unsicherer Eintrag im Update-Archiv: $($UnsafeEntry.FullName)" }
} finally {
    $ZipFile.Dispose()
}
$UpdateHash = (Get-FileHash $UpdateZip -Algorithm SHA256).Hash.ToLowerInvariant()
$UpdateSize = (Get-Item $UpdateZip).Length
@{
    version = $AppVersion
    build = $AppBuild
    package_kind = "windows-pyinstaller-onedir"
    filename = (Split-Path $UpdateZip -Leaf)
    sha256 = $UpdateHash
    size = $UpdateSize
} | ConvertTo-Json | Set-Content -Path $UpdateManifest -Encoding UTF8
Remove-Item -Recurse -Force $UpdatePackageRoot

Write-Host ""
Write-Host "Build fertig: dist\LohnMail\LohnMail.exe" -ForegroundColor Green
Write-Host "Saubere portable Struktur: release\LohnMail" -ForegroundColor Green
Write-Host "EXE-Update: $UpdateZip" -ForegroundColor Green
Write-Host "SHA-256: $UpdateHash" -ForegroundColor Green

param(
    [switch]$SkipTests,
    [switch]$SkipDependencyInstall
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $ProjectRoot

if (-not $SkipDependencyInstall) {
    if (-not (Test-Path ".venv\Scripts\python.exe")) {
        python -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw "Die Windows-Build-Umgebung konnte nicht erstellt werden." }
    }
    & ".venv\Scripts\python.exe" -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { throw "pip konnte nicht aktualisiert werden." }
    & ".venv\Scripts\python.exe" -m pip install -r requirements-build-windows.txt
    if ($LASTEXITCODE -ne 0) { throw "Die Windows-Build-Abhängigkeiten konnten nicht installiert werden." }
}

if (-not $SkipTests) {
    & ".venv\Scripts\python.exe" -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw "Die Tests sind fehlgeschlagen. Es wird kein MSIX erstellt." }
}

& ".\variants\windows\build-standalone.ps1" -Distribution store
if ($LASTEXITCODE -ne 0) { throw "Die Store-Standalone-Sammlung ist fehlgeschlagen." }

$VersionSource = Get-Content "ui_web\version.py" -Raw
$VersionMatch = [regex]::Match($VersionSource, 'APP_VERSION\s*=\s*"([^"]+)"')
$BuildMatch = [regex]::Match($VersionSource, 'APP_BUILD\s*=\s*"([^"]+)"')
if (-not $VersionMatch.Success -or -not $BuildMatch.Success) {
    throw "Version oder Build konnte nicht aus ui_web\version.py gelesen werden."
}
$AppVersion = $VersionMatch.Groups[1].Value
$AppBuild = $BuildMatch.Groups[1].Value
$MsixVersion = if ($env:MSIX_VERSION) { [string]$env:MSIX_VERSION } else { "$AppVersion.0" }
if ($MsixVersion -notmatch '^\d+\.\d+\.\d+\.\d+$') {
    throw "MSIX_VERSION muss aus vier numerischen Teilen bestehen."
}

$IdentityName = if ($env:MSIX_IDENTITY_NAME) { [string]$env:MSIX_IDENTITY_NAME } else { "LohnMail.Test" }
$Publisher = if ($env:MSIX_PUBLISHER) { [string]$env:MSIX_PUBLISHER } else { "CN=LohnMail Development" }
$PublisherDisplayName = if ($env:MSIX_PUBLISHER_DISPLAY_NAME) { [string]$env:MSIX_PUBLISHER_DISPLAY_NAME } else { "LohnMail" }
$ApplicationId = if ($env:MSIX_APPLICATION_ID) { [string]$env:MSIX_APPLICATION_ID } else { "LohnMail" }

function Escape-Xml([string]$Value) {
    return [System.Security.SecurityElement]::Escape($Value)
}

$BuildRoot = Join-Path $ProjectRoot "build\store-msix"
$StageRoot = Join-Path $BuildRoot "staging"
$ValidationRoot = Join-Path $BuildRoot "validation"
$OutputRoot = Join-Path $ProjectRoot "dist\store"
$StandaloneRoot = Join-Path $OutputRoot "LohnMail"
$TemplatePath = Join-Path $PSScriptRoot "msix\AppxManifest.xml.in"
$AssetsSource = Join-Path $PSScriptRoot "msix\assets"
$ManifestPath = Join-Path $StageRoot "AppxManifest.xml"
$OutputMsix = Join-Path $OutputRoot "LohnMail_${MsixVersion}_x64.msix"

foreach ($RequiredPath in @($StandaloneRoot, $TemplatePath, $AssetsSource)) {
    if (-not (Test-Path $RequiredPath)) { throw "Erforderlicher Store-Build-Pfad fehlt: $RequiredPath" }
}
if (Test-Path $BuildRoot) { Remove-Item -Recurse -Force $BuildRoot }
New-Item -ItemType Directory -Force $StageRoot, $ValidationRoot, $OutputRoot | Out-Null
Copy-Item -Recurse -Force "$StandaloneRoot\*" $StageRoot
Copy-Item -Recurse -Force $AssetsSource (Join-Path $StageRoot "Assets")

$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$Manifest = [System.IO.File]::ReadAllText($TemplatePath, $Utf8NoBom)
$Manifest = $Manifest.Replace("@@IDENTITY_NAME@@", (Escape-Xml $IdentityName))
$Manifest = $Manifest.Replace("@@PUBLISHER@@", (Escape-Xml $Publisher))
$Manifest = $Manifest.Replace("@@PUBLISHER_DISPLAY_NAME@@", (Escape-Xml $PublisherDisplayName))
$Manifest = $Manifest.Replace("@@APPLICATION_ID@@", (Escape-Xml $ApplicationId))
$Manifest = $Manifest.Replace("@@MSIX_VERSION@@", $MsixVersion)
[System.IO.File]::WriteAllText($ManifestPath, $Manifest, $Utf8NoBom)

$RequiredStageFiles = @(
    "LohnMail.exe",
    "lohnmail_distribution.json",
    "AppxManifest.xml",
    "Assets\Square44x44Logo.png",
    "Assets\Square150x150Logo.png",
    "Assets\StoreLogo.png",
    "Assets\Wide310x150Logo.png",
    "Assets\SplashScreen.png"
)
foreach ($RelativePath in $RequiredStageFiles) {
    if (-not (Test-Path (Join-Path $StageRoot $RelativePath))) {
        throw "Die MSIX-Staging-Datei fehlt: $RelativePath"
    }
}

$Forbidden = Get-ChildItem -LiteralPath $StageRoot -Recurse -File | Where-Object {
    $_.Name -match '^(license\.json|machine_id|settings\.json|secrets\.dat|workflow_sessions\.json|lohnmail_history\.sqlite3(?:-wal|-shm)?)$' -or
    $_.FullName -match '[\\/](Settings|Companies|Reports?)[\\/]' -or
    $_.Extension -match '^\.(pdf|xlsx?|xlsm|csv)$'
} | Select-Object -First 1
if ($Forbidden) { throw "Benutzerdaten dürfen nicht im MSIX enthalten sein: $($Forbidden.FullName)" }

$WindowsKitsBin = Join-Path ${env:ProgramFiles(x86)} "Windows Kits\10\bin"
$MakeAppx = Get-Command MakeAppx.exe -ErrorAction SilentlyContinue
if (-not $MakeAppx -and (Test-Path $WindowsKitsBin)) {
    $MakeAppx = Get-ChildItem $WindowsKitsBin -Filter MakeAppx.exe -Recurse -File |
        Where-Object { $_.FullName -match '[\\/]x64[\\/]MakeAppx\.exe$' } |
        Sort-Object FullName -Descending |
        Select-Object -First 1
}
if (-not $MakeAppx) { throw "MakeAppx.exe aus dem Windows SDK wurde nicht gefunden." }
$MakeAppxPath = if ($MakeAppx.Source) { $MakeAppx.Source } else { $MakeAppx.FullName }

if (Test-Path $OutputMsix) { Remove-Item -Force $OutputMsix }
& $MakeAppxPath pack /d $StageRoot /p $OutputMsix /o
if ($LASTEXITCODE -ne 0 -or -not (Test-Path $OutputMsix)) { throw "MakeAppx konnte das MSIX nicht erstellen." }
& $MakeAppxPath unpack /p $OutputMsix /d $ValidationRoot /o
if ($LASTEXITCODE -ne 0) { throw "Das erzeugte MSIX konnte nicht validiert entpackt werden." }
foreach ($RelativePath in @("LohnMail.exe", "AppxManifest.xml", "lohnmail_distribution.json")) {
    if (-not (Test-Path (Join-Path $ValidationRoot $RelativePath))) {
        throw "MSIX-Validierung fehlgeschlagen, Datei fehlt: $RelativePath"
    }
}

$ValidatedManifestPath = Join-Path $ValidationRoot "AppxManifest.xml"
$ValidatedManifestText = [System.IO.File]::ReadAllText($ValidatedManifestPath, $Utf8NoBom)
[xml]$ValidatedManifest = $ValidatedManifestText
if ($ValidatedManifest.Package.Identity.Version -ne $MsixVersion) { throw "Die MSIX-Version stimmt nicht." }
if ($ValidatedManifest.Package.Identity.ProcessorArchitecture -ne "x64") { throw "Die MSIX-Architektur ist nicht x64." }
if ($ValidatedManifestText -notlike '*Lohnabrechnungen prüfen, schützen und sicher versenden*') {
    throw "Die UTF-8-Zeichen im MSIX-Manifest wurden beschädigt."
}

$Hash = (Get-FileHash $OutputMsix -Algorithm SHA256).Hash.ToLowerInvariant()
$HashPath = "$OutputMsix.sha256"
[System.IO.File]::WriteAllText($HashPath, "$Hash  $(Split-Path $OutputMsix -Leaf)`n", $Utf8NoBom)
Copy-Item -Force $ManifestPath (Join-Path $OutputRoot "AppxManifest.xml")

$Commit = if ($env:GITHUB_SHA) { [string]$env:GITHUB_SHA } else { (& git rev-parse HEAD).Trim() }
$BuildInfo = [ordered]@{
    version = $AppVersion
    msix_version = $MsixVersion
    build = $AppBuild
    channel = "store"
    architecture = "x64"
    commit = $Commit
    build_date = (Get-Date).ToUniversalTime().ToString("o")
    identity_name = $IdentityName
    publisher = $Publisher
    application_id = $ApplicationId
    sha256 = $Hash
    filename = (Split-Path $OutputMsix -Leaf)
}
$BuildInfoJson = $BuildInfo | ConvertTo-Json
[System.IO.File]::WriteAllText(
    (Join-Path $OutputRoot "build_info.json"),
    $BuildInfoJson,
    $Utf8NoBom
)

Write-Host "MSIX erstellt: $OutputMsix" -ForegroundColor Green
Write-Host "SHA-256: $Hash" -ForegroundColor Green

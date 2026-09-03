param(
    [switch]$RequireSignature
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$VersionSource = Get-Content "ui_web\version.py" -Raw
$VersionMatch = [regex]::Match($VersionSource, 'APP_VERSION\s*=\s*"([^"]+)"')
$BuildMatch = [regex]::Match($VersionSource, 'APP_BUILD\s*=\s*"([^"]+)"')
if (-not $VersionMatch.Success -or -not $BuildMatch.Success) {
    throw "Version oder Build konnte nicht aus ui_web\version.py gelesen werden."
}
$AppVersion = $VersionMatch.Groups[1].Value
$AppBuild = $BuildMatch.Groups[1].Value

$VersionInfo = Get-Content "windows_version_info.txt" -Raw
$NumericMatch = [regex]::Match($VersionInfo, "filevers=\((\d+),\s*(\d+),\s*(\d+),\s*(\d+)\)")
if (-not $NumericMatch.Success) {
    throw "Die numerische Windows-Version konnte nicht gelesen werden."
}
$AppNumericVersion = ($NumericMatch.Groups[1..4].Value -join ".")

$ReleaseRoot = Join-Path $PSScriptRoot "release\LohnMail"
$RequiredFiles = @(
    (Join-Path $ReleaseRoot "LohnMail.exe"),
    (Join-Path $ReleaseRoot "App\LohnMail.exe"),
    (Join-Path $ReleaseRoot "Settings\settings.json")
)
foreach ($RequiredFile in $RequiredFiles) {
    if (-not (Test-Path $RequiredFile)) {
        throw "Windows-Release fehlt. Zuerst BUILD-WINDOWS.ps1 ausführen: $RequiredFile"
    }
}

$IsccCandidates = @(
    (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"),
    (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe")
)
$Iscc = $IsccCandidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
if (-not $Iscc) {
    $IsccCommand = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($IsccCommand) { $Iscc = $IsccCommand.Source }
}
if (-not $Iscc) {
    throw "Inno Setup 6 wurde nicht gefunden. Bitte Inno Setup installieren."
}

$OutputDirectory = Join-Path $PSScriptRoot "release\store"
New-Item -ItemType Directory -Force $OutputDirectory | Out-Null
$OutputName = "LohnMail-$AppVersion-build-$AppBuild-Setup-x64.exe"
$OutputPath = Join-Path $OutputDirectory $OutputName
if (Test-Path $OutputPath) { Remove-Item -Force $OutputPath }

& $Iscc `
    "/DAppVersion=$AppVersion" `
    "/DAppBuild=$AppBuild" `
    "/DAppNumericVersion=$AppNumericVersion" `
    "windows-store-installer.iss"
if ($LASTEXITCODE -ne 0 -or -not (Test-Path $OutputPath)) {
    throw "Der Microsoft-Store-Installer konnte nicht erstellt werden."
}

$Signature = Get-AuthenticodeSignature $OutputPath
if ($RequireSignature -and $Signature.Status -ne "Valid") {
    throw "Der Microsoft-Store-Installer ist nicht gültig signiert."
}

$InstallerHash = (Get-FileHash $OutputPath -Algorithm SHA256).Hash.ToLowerInvariant()
$InstallerSize = (Get-Item $OutputPath).Length
$ManifestPath = Join-Path $OutputDirectory "LohnMail-$AppVersion-build-$AppBuild-Setup-x64.json"
$ManifestJson = @{
    version = $AppVersion
    build = $AppBuild
    architecture = "x64"
    filename = $OutputName
    sha256 = $InstallerHash
    size = $InstallerSize
    signature_status = [string]$Signature.Status
    silent_parameters = "/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-"
} | ConvertTo-Json
[System.IO.File]::WriteAllText(
    $ManifestPath,
    $ManifestJson,
    (New-Object System.Text.UTF8Encoding($false))
)

Write-Host ""
Write-Host "Store-Installer erstellt: $OutputPath" -ForegroundColor Green
Write-Host "Signaturstatus: $($Signature.Status)" -ForegroundColor Yellow
Write-Host "SHA-256: $InstallerHash" -ForegroundColor Green


param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("direct", "store")]
    [string]$Distribution
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $ProjectRoot

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    throw "Die Windows-Build-Umgebung fehlt."
}

$VersionSource = Get-Content "ui_web\version.py" -Raw
$VersionMatch = [regex]::Match($VersionSource, 'APP_VERSION\s*=\s*"([^"]+)"')
$BuildMatch = [regex]::Match($VersionSource, 'APP_BUILD\s*=\s*"([^"]+)"')
if (-not $VersionMatch.Success -or -not $BuildMatch.Success) {
    throw "Version oder Build konnte nicht aus ui_web\version.py gelesen werden."
}
$AppVersion = $VersionMatch.Groups[1].Value
$AppBuild = $BuildMatch.Groups[1].Value
$VersionParts = @($AppVersion.Split(".") | ForEach-Object { [int]$_ })
if ($VersionParts.Count -ne 3) {
    throw "APP_VERSION muss aus drei numerischen Teilen bestehen."
}
$NumericVersion = @($VersionParts[0], $VersionParts[1], $VersionParts[2], 0)

$BuildRoot = Join-Path $ProjectRoot "build\$Distribution"
$DistRoot = Join-Path $ProjectRoot "dist\$Distribution"
$GeneratedRoot = Join-Path $BuildRoot "generated"
$VersionInfoPath = Join-Path $GeneratedRoot "windows_version_info.txt"
$DistributionMarker = Join-Path $GeneratedRoot "lohnmail_distribution.json"
if (Test-Path $BuildRoot) { Remove-Item -Recurse -Force $BuildRoot }
if (Test-Path $DistRoot) { Remove-Item -Recurse -Force $DistRoot }
New-Item -ItemType Directory -Force $GeneratedRoot, $DistRoot, (Join-Path $BuildRoot "pyinstaller"), (Join-Path $BuildRoot "spec") | Out-Null

$VersionTuple = $NumericVersion -join ", "
$VersionDot = $NumericVersion -join "."
$VersionInfo = @"
VSVersionInfo(
  ffi=FixedFileInfo(filevers=($VersionTuple), prodvers=($VersionTuple), mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040704B0', [
      StringStruct('CompanyName', 'LohnMail'),
      StringStruct('FileDescription', 'LohnMail Enterprise Edition'),
      StringStruct('FileVersion', '$VersionDot'),
      StringStruct('InternalName', 'LohnMail'),
      StringStruct('LegalCopyright', '© 2026 Andrii Bakanov'),
      StringStruct('OriginalFilename', 'LohnMail.exe'),
      StringStruct('ProductName', 'LohnMail Enterprise Edition'),
      StringStruct('ProductVersion', '$VersionDot')
    ])]),
    VarFileInfo([VarStruct('Translation', [1031, 1200])])
  ]
)
"@
[System.IO.File]::WriteAllText($VersionInfoPath, $VersionInfo, (New-Object System.Text.UTF8Encoding($false)))

$StoreUri = if ($env:LOHNMAIL_STORE_URI) { [string]$env:LOHNMAIL_STORE_URI } else { "" }
$MarkerJson = @{ distribution = $Distribution; store_uri = $StoreUri } | ConvertTo-Json
[System.IO.File]::WriteAllText($DistributionMarker, $MarkerJson, (New-Object System.Text.UTF8Encoding($false)))

$PyInstallerArguments = @(
    "--noconfirm",
    "--clean",
    "--windowed",
    "--onedir",
    "--contents-directory", ".",
    "--name", "LohnMail",
    "--icon", "web\assets\brand\LohnMail.ico",
    "--version-file", $VersionInfoPath,
    "--collect-all", "webview",
    "--hidden-import", "win32crypt",
    "--hidden-import", "pythoncom",
    "--hidden-import", "pywintypes",
    "--hidden-import", "win32com.client",
    "--add-data", "web;web",
    "--add-data", "settings_template.json;.",
    "--add-data", "$DistributionMarker;.",
    "--distpath", $DistRoot,
    "--workpath", (Join-Path $BuildRoot "pyinstaller"),
    "--specpath", (Join-Path $BuildRoot "spec")
)

if ($Distribution -eq "direct") {
    $RootLauncherBuildDir = Join-Path $BuildRoot "launcher"
    $RootLauncher = Join-Path $RootLauncherBuildDir "LohnMail.RootLauncher.exe"
    New-Item -ItemType Directory -Force $RootLauncherBuildDir | Out-Null
    $LauncherIcon = (Resolve-Path "web\assets\brand\LohnMail.ico").Path
    $CSharpCompiler = Join-Path $env:WINDIR "Microsoft.NET\Framework64\v4.0.30319\csc.exe"
    if (-not (Test-Path $CSharpCompiler)) {
        $CSharpCompiler = Join-Path $env:WINDIR "Microsoft.NET\Framework\v4.0.30319\csc.exe"
    }
    if (-not (Test-Path $CSharpCompiler)) {
        throw "Der Windows-C#-Compiler für den Root-Launcher wurde nicht gefunden."
    }
    & $CSharpCompiler /nologo /target:winexe /optimize+ "/win32icon:$LauncherIcon" /reference:System.dll /reference:System.Windows.Forms.dll "/out:$RootLauncher" "windows_root_launcher.cs"
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $RootLauncher)) {
        throw "Der Windows-Root-Launcher konnte nicht erstellt werden."
    }
    $PyInstallerArguments += @("--add-binary", "$RootLauncher;.")
}

$PyInstallerArguments += "main.py"
& $Python -m PyInstaller @PyInstallerArguments
if ($LASTEXITCODE -ne 0) { throw "PyInstaller konnte LohnMail.exe nicht erstellen." }

$Executable = Join-Path $DistRoot "LohnMail\LohnMail.exe"
if (-not (Test-Path $Executable)) { throw "LohnMail.exe fehlt nach der Standalone-Sammlung." }
& $Executable --lohnmail-update-selftest $AppVersion $AppBuild
if ($LASTEXITCODE -ne 0) { throw "Der Standalone-Selbsttest ist fehlgeschlagen." }

Write-Host "Standalone ${Distribution}: $Executable" -ForegroundColor Green

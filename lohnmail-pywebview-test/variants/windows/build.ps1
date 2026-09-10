$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $ProjectRoot
& ".\BUILD-WINDOWS.ps1"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

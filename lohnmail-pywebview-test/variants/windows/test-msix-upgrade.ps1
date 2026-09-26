param(
    [Parameter(Mandatory = $true)] [string]$StagingDirectory,
    [Parameter(Mandatory = $true)] [string]$IdentityName,
    [Parameter(Mandatory = $true)] [string]$Publisher,
    [Parameter(Mandatory = $true)] [string]$ApplicationVersion,
    [Parameter(Mandatory = $true)] [string]$ApplicationBuild
)

$ErrorActionPreference = "Stop"
if ($env:GITHUB_ACTIONS -ne 'true') { throw 'This destructive install/uninstall test is restricted to disposable GitHub runners.' }
Add-Type @'
using System;
using System.Runtime.InteropServices;
[ComImport, Guid("45BA127D-10A8-46EA-8AB7-56EA9078943C")]
public class LohnMailActivationManager {}
[ComImport, Guid("2E941141-7F97-4756-BA1D-9DECDE894A3D"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface ILohnMailActivationManager {
    [PreserveSig] int ActivateApplication([MarshalAs(UnmanagedType.LPWStr)] string id,
        [MarshalAs(UnmanagedType.LPWStr)] string arguments, uint options, out uint processId);
}
public static class LohnMailPackageProbe {
    public static uint Launch(string id, string arguments) {
        var manager = (ILohnMailActivationManager)new LohnMailActivationManager();
        uint pid; int hr = manager.ActivateApplication(id, arguments, 0, out pid);
        Marshal.ThrowExceptionForHR(hr); return pid;
    }
}
'@
function Invoke-StorageProbe($Installed, [string]$Result, [string]$Workspace) {
    [xml]$Manifest = Get-Content (Join-Path $Installed.InstallLocation 'AppxManifest.xml') -Raw
    $AppId = [string]$Manifest.Package.Applications.Application.Id
    $Aumid = $Installed.PackageFamilyName + '!' + $AppId
    $Arguments = '--lohnmail-storage-probe "' + $Result + '" "' + $Workspace + '"'
    $ProcessId = [LohnMailPackageProbe]::Launch($Aumid, $Arguments)
    $Process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
    if ($Process -and -not $Process.WaitForExit(60000)) { throw 'Packaged storage probe timed out.' }
    if (-not (Test-Path -LiteralPath $Result)) { throw 'Package activation/storage API failed; no probe report.' }
    $Report = Get-Content -LiteralPath $Result -Raw | ConvertFrom-Json
    if ($Report.error) { throw ("Packaged storage probe failed: " + $Report.error + "`n" + $Report.traceback) }
    if ($Report.family -ne $Installed.PackageFamilyName) { throw 'Probe did not run with the installed package identity.' }
    if ($Report.workspace -ne $Workspace) { throw 'Unexpected workspace.' }
    if (-not $Report.state.Contains('\LocalState\')) { throw 'Settings are not in Windows LocalFolder.' }
    return $Report
}
$WindowsKitsBin = Join-Path ${env:ProgramFiles(x86)} "Windows Kits\10\bin"
function Find-SdkTool([string]$Name) {
    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    $tool = Get-ChildItem $WindowsKitsBin -Filter $Name -Recurse -File |
        Where-Object { $_.FullName -match "[\\/]x64[\\/]$([regex]::Escape($Name))$" } |
        Sort-Object FullName -Descending |
        Select-Object -First 1
    if (-not $tool) { throw "$Name wurde nicht gefunden." }
    return $tool.FullName
}

$MakeAppx = Find-SdkTool "MakeAppx.exe"
$SignTool = Find-SdkTool "SignTool.exe"
$TestRoot = Join-Path $env:RUNNER_TEMP "lohnmail-msix-upgrade"
$FirstStage = Join-Path $TestRoot "first"
$SecondStage = Join-Path $TestRoot "second"
$FirstPackage = Join-Path $TestRoot "LohnMail_2.0.0.0_x64.msix"
$SecondPackage = Join-Path $TestRoot "LohnMail_2.0.1.0_x64.msix"
if (Test-Path $TestRoot) { Remove-Item -Recurse -Force $TestRoot }
New-Item -ItemType Directory -Force $FirstStage, $SecondStage | Out-Null
Copy-Item -Recurse -Force "$StagingDirectory\*" $FirstStage
Copy-Item -Recurse -Force "$StagingDirectory\*" $SecondStage

foreach ($Pair in @(@($FirstStage, "2.0.0.0"), @($SecondStage, "2.0.1.0"))) {
    $ManifestPath = Join-Path $Pair[0] "AppxManifest.xml"
    $Content = (Get-Content $ManifestPath -Raw) -replace 'Version="\d+\.\d+\.\d+\.\d+"', "Version=`"$($Pair[1])`""
    [System.IO.File]::WriteAllText($ManifestPath, $Content, (New-Object System.Text.UTF8Encoding($false)))
}
& $MakeAppx pack /d $FirstStage /p $FirstPackage /o
if ($LASTEXITCODE -ne 0) { throw "Upgrade-Testpaket 2.0.0.0 konnte nicht erstellt werden." }
& $MakeAppx pack /d $SecondStage /p $SecondPackage /o
if ($LASTEXITCODE -ne 0) { throw "Upgrade-Testpaket 2.0.1.0 konnte nicht erstellt werden." }

$Certificate = New-SelfSignedCertificate -Type Custom -Subject $Publisher -KeyUsage DigitalSignature -FriendlyName "LohnMail MSIX CI Test" -CertStoreLocation "Cert:\CurrentUser\My" -TextExtension @("2.5.29.37={text}1.3.6.1.5.5.7.3.3")
$Password = ConvertTo-SecureString "LohnMail-CI-Temporary" -AsPlainText -Force
$PfxPath = Join-Path $TestRoot "test-signing.pfx"
$CerPath = Join-Path $TestRoot "test-signing.cer"
Export-PfxCertificate -Cert $Certificate -FilePath $PfxPath -Password $Password | Out-Null
Export-Certificate -Cert $Certificate -FilePath $CerPath | Out-Null
Import-Certificate -FilePath $CerPath -CertStoreLocation "Cert:\LocalMachine\TrustedPeople" | Out-Null
$DataSentinelsCreated = $false

try {
    foreach ($Package in @($FirstPackage, $SecondPackage)) {
        & $SignTool sign /fd SHA256 /f $PfxPath /p "LohnMail-CI-Temporary" $Package
        if ($LASTEXITCODE -ne 0) { throw "Das CI-Testpaket konnte nicht signiert werden." }
    }
    Get-AppxPackage -Name $IdentityName | Remove-AppxPackage -ErrorAction SilentlyContinue
    Add-AppxPackage -Path $FirstPackage
    $FirstInstalled = Get-AppxPackage -Name $IdentityName
    if (-not $FirstInstalled -or [string]$FirstInstalled.Version -ne "2.0.0.0") { throw "MSIX-Erstinstallation ist fehlgeschlagen." }
    # Activate through the package identity, not a direct executable path.
    $Workspace = Join-Path $TestRoot 'workspace'
    New-Item -ItemType Directory -Path $Workspace | Out-Null
    $FirstProbe = Invoke-StorageProbe $FirstInstalled (Join-Path $TestRoot 'first-storage.json') $Workspace
    $DataRoot = $FirstProbe.state
    $SettingsSentinel = Join-Path $DataRoot "Settings\msix-upgrade-sentinel.txt"
    $CompaniesSentinel = Join-Path $Workspace "Companies\msix-upgrade-sentinel.txt"
    $HistorySentinel = Join-Path $Workspace "History\msix-upgrade-sentinel.txt"
    New-Item -ItemType Directory -Force (Split-Path $SettingsSentinel), (Split-Path $CompaniesSentinel) | Out-Null
    Set-Content $SettingsSentinel "settings-must-survive"
    Set-Content $CompaniesSentinel "companies-must-survive"
    Set-Content $HistorySentinel 'history-must-survive'
    $DataSentinelsCreated = $true

    Add-AppxPackage -Path $SecondPackage -ForceApplicationShutdown
    $Installed = @(Get-AppxPackage -Name $IdentityName)
    if ($Installed.Count -ne 1 -or [string]$Installed[0].Version -ne "2.0.1.0") { throw "MSIX-Upgrade ist fehlgeschlagen." }
    $SecondProbe = Invoke-StorageProbe $Installed[0] (Join-Path $TestRoot 'second-storage.json') $Workspace
    if ($SecondProbe.state -ne $FirstProbe.state) { throw 'Data root changed after upgrade.' }
    if (-not (Test-Path $SettingsSentinel)) { throw "Settings wurden beim MSIX-Upgrade entfernt." }
    if (-not (Test-Path $CompaniesSentinel)) { throw "Companies wurden beim MSIX-Upgrade entfernt." }
    if ((Get-Content $SettingsSentinel) -ne 'settings-must-survive') { throw 'Settings changed.' }
    if ((Get-Content $CompaniesSentinel) -ne 'companies-must-survive') { throw 'Documents changed.' }
    if ((Get-Content $HistorySentinel) -ne 'history-must-survive') { throw 'History changed.' }
} finally {
    Get-AppxPackage -Name $IdentityName | Remove-AppxPackage -ErrorAction SilentlyContinue
    Remove-Item "Cert:\CurrentUser\My\$($Certificate.Thumbprint)" -Force -ErrorAction SilentlyContinue
    Remove-Item "Cert:\LocalMachine\TrustedPeople\$($Certificate.Thumbprint)" -Force -ErrorAction SilentlyContinue
}
if ($DataSentinelsCreated) {
    # LocalFolder settings belong to the package and may be removed on uninstall.
    if (-not (Test-Path $CompaniesSentinel)) { throw "Companies wurden bei der Deinstallation entfernt." }
    if (-not (Test-Path $HistorySentinel)) { throw 'Workspace history removed by uninstall.' }
}

Write-Host "MSIX install/upgrade test passed." -ForegroundColor Green

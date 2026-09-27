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
function Invoke-StorageProbe($Installed, [string]$Result, [string]$Workspace, [switch]$ExpectConflict) {
    [xml]$Manifest = Get-Content (Join-Path $Installed.InstallLocation 'AppxManifest.xml') -Raw
    $AppId = [string]$Manifest.Package.Applications.Application.Id
    $Aumid = $Installed.PackageFamilyName + '!' + $AppId
    $Arguments = '--lohnmail-storage-probe "' + $Result + '" "' + $Workspace + '"'
    $ProcessId = [LohnMailPackageProbe]::Launch($Aumid, $Arguments)
    $Process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
    if ($Process -and -not $Process.WaitForExit(180000)) { throw 'Packaged storage probe timed out.' }
    if (-not (Test-Path -LiteralPath $Result)) { throw 'Package activation/storage API failed; no probe report.' }
    $Report = Get-Content -LiteralPath $Result -Raw | ConvertFrom-Json
    if ($ExpectConflict) {
        if (-not $Report.error -or $Report.error -notmatch 'Unterschiedliche Datenbest') { throw 'Conflicting copies did not fail safely.' }
        return $Report
    }
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
$LegacyStage = Join-Path $TestRoot 'legacy'
$LegacyPackage = Join-Path $TestRoot 'LohnMail_legacy_fixture.msix'
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
Copy-Item -Recurse $FirstStage $LegacyStage
$Compiler = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
& $Compiler /nologo /target:winexe /platform:x64 "/out:$LegacyStage\LohnMail.exe" (Join-Path $PSScriptRoot 'LegacyStorageFixture.cs')
if ($LASTEXITCODE -ne 0) { throw 'Legacy-layout fixture compilation failed.' }
& $MakeAppx pack /d $LegacyStage /p $LegacyPackage /o
if ($LASTEXITCODE -ne 0) { throw 'Legacy-layout fixture packaging failed.' }

$Certificate = New-SelfSignedCertificate -Type Custom -Subject $Publisher -KeyUsage DigitalSignature -FriendlyName "LohnMail MSIX CI Test" -CertStoreLocation "Cert:\CurrentUser\My" -TextExtension @("2.5.29.37={text}1.3.6.1.5.5.7.3.3")
$Password = ConvertTo-SecureString "LohnMail-CI-Temporary" -AsPlainText -Force
$PfxPath = Join-Path $TestRoot "test-signing.pfx"
$CerPath = Join-Path $TestRoot "test-signing.cer"
Export-PfxCertificate -Cert $Certificate -FilePath $PfxPath -Password $Password | Out-Null
Export-Certificate -Cert $Certificate -FilePath $CerPath | Out-Null
Import-Certificate -FilePath $CerPath -CertStoreLocation "Cert:\LocalMachine\TrustedPeople" | Out-Null
$DataSentinelsCreated = $false

try {
    foreach ($Package in @($FirstPackage, $SecondPackage, $LegacyPackage)) {
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

    # Different OLD layout, not merely two versions of the current code.
    # Every source is synthetic; abort rather than touch pre-existing data.
    $Ordinary = Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'LohnMail'
    if (Test-Path -LiteralPath $Ordinary) { throw 'Runner already has ordinary LohnMail data; refusing fixture setup.' }
    foreach ($Case in @('empty', 'ordinary', 'redirected', 'both', 'conflict')) {
        Get-AppxPackage -Name $IdentityName | Remove-AppxPackage
        $CaseRoot = Join-Path $TestRoot "case-$Case"
        $CaseWorkspace = Join-Path $CaseRoot 'workspace'
        New-Item -ItemType Directory -Force $CaseWorkspace | Out-Null
        if ($Case -in @('ordinary', 'both', 'conflict')) {
            New-Item -ItemType Directory -Force (Join-Path $Ordinary 'Settings') | Out-Null
            Set-Content -LiteralPath (Join-Path $Ordinary 'Settings\ordinary-sentinel.txt') -Value 'ordinary-original'
        }
        try {
            Add-AppxPackage -Path $LegacyPackage
            $Old = Get-AppxPackage -Name $IdentityName
            [xml]$OldManifest = Get-Content (Join-Path $Old.InstallLocation 'AppxManifest.xml') -Raw
            $LegacyReport = Join-Path $CaseRoot 'legacy-family.txt'
            $FixtureId = [LohnMailPackageProbe]::Launch(($Old.PackageFamilyName + '!' + $OldManifest.Package.Applications.Application.Id), ('"' + $LegacyReport + '" ' + $Case))
            $Fixture = Get-Process -Id $FixtureId -ErrorAction SilentlyContinue
            if ($Fixture -and -not $Fixture.WaitForExit(60000)) { throw 'Legacy fixture timed out.' }
            if ((Get-Content -LiteralPath $LegacyReport -Raw) -ne $Old.PackageFamilyName) { throw 'Legacy writer had no package identity.' }
            $Virtual = Join-Path $env:LOCALAPPDATA "Packages\$($Old.PackageFamilyName)\LocalCache\Local\LohnMail"
            if ($Case -eq 'redirected' -and -not (Test-Path (Join-Path $Virtual 'Settings\license.json'))) { throw 'Fixture failed to reproduce redirection.' }
            if ($Case -in @('both', 'conflict')) {
                New-Item -ItemType Directory -Force (Join-Path $Virtual 'Companies\CI-Second') | Out-Null
                Set-Content -LiteralPath (Join-Path $Virtual 'Companies\CI-Second\result.pdf') 'second-physical-store'
            }
            if ($Case -eq 'conflict') {
                New-Item -ItemType Directory -Force (Join-Path $Virtual 'Settings') | Out-Null
                Set-Content -LiteralPath (Join-Path $Virtual 'Settings\license.json') '{"license_key":"CONFLICT-DO-NOT-OVERWRITE"}'
                Set-Content -LiteralPath (Join-Path $Ordinary 'Settings\license.json') '{"license_key":"OTHER-CONFLICT"}'
            }
            $Before = @{}
            foreach ($Source in @($Ordinary, $Virtual)) {
                if (Test-Path $Source) { Get-ChildItem $Source -Recurse -File | ForEach-Object { $Before[$_.FullName] = (Get-FileHash $_.FullName).Hash } }
            }
            Add-AppxPackage -Path $SecondPackage -ForceApplicationShutdown
            $New = Get-AppxPackage -Name $IdentityName
            $NewProbe = Invoke-StorageProbe $New (Join-Path $CaseRoot 'new.json') $CaseWorkspace -ExpectConflict:($Case -eq 'conflict')
            $Export = Join-Path $CaseWorkspace 'LohnMail-Legacy-Export\export.json'
            $ExportInfo = Get-Content -LiteralPath $Export -Raw | ConvertFrom-Json
            if ($ExportInfo.identity_result -ne 15700) { throw 'Export was not verified outside package identity.' }
            foreach ($Source in $Before.Keys) {
                if ((Get-FileHash -LiteralPath $Source).Hash -ne $Before[$Source]) { throw "Legacy original changed: $Source" }
            }
            if ($Case -eq 'conflict') {
                $StateRoot = Join-Path $env:LOCALAPPDATA "Packages\$($New.PackageFamilyName)\LocalState\LohnMail"
                if ((Test-Path (Join-Path $StateRoot 'Data')) -or (Test-Path (Join-Path $StateRoot 'storage-layout.json'))) { throw 'Conflict switched to empty/replaced state.' }
            } else {
                $Restart = Invoke-StorageProbe $New (Join-Path $CaseRoot 'restart.json') $CaseWorkspace
                if ($Restart.state -ne $NewProbe.state) { throw 'State changed on restart.' }
                if ($Case -ne 'empty') {
                    $License = Get-Content (Join-Path $NewProbe.state 'Settings\license.json') -Raw | ConvertFrom-Json
                    if ($License.license_key -ne 'SYNTHETIC-KEEP') { throw 'License reset during migration.' }
                    if ((Get-Content (Join-Path $CaseWorkspace 'Companies\CI-Legacy-Unique\result.pdf') -Raw) -ne 'SYNTHETIC-PDF') { throw 'Legacy document lost.' }
                    if ((Get-Content (Join-Path $NewProbe.state 'Settings\secrets.dat') -Raw) -ne 'SYNTHETIC-ENCRYPTED-NOT-A-PASSWORD') { throw 'Encrypted settings lost.' }
                }
            }
            Write-Host "Installed legacy migration scenario passed: $Case"
        } finally {
            # This exact folder was proved absent before fixtures were created.
            if (Test-Path -LiteralPath $Ordinary) { Remove-Item -LiteralPath $Ordinary -Recurse -Force }
        }
    }
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

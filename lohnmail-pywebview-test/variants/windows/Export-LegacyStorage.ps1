param(
    [Parameter(Mandatory = $true)][string]$PackageFamilyName,
    [Parameter(Mandatory = $true)][string]$Workspace
)
# Run in ordinary Windows PowerShell with LohnMail closed, never in its package.
# Copy only. No source is deleted/renamed; differing stores remain separate.
$ErrorActionPreference = 'Stop'
Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class LohnMailExportIdentity {
  [DllImport("kernel32.dll", CharSet=CharSet.Unicode)]
  public static extern int GetCurrentPackageFamilyName(ref uint length, IntPtr name);
}
'@
[uint32]$Length = 0
if ([LohnMailExportIdentity]::GetCurrentPackageFamilyName([ref]$Length, [IntPtr]::Zero) -ne 15700) {
    throw 'Start this script from ordinary Windows PowerShell, outside the MSIX package.'
}
if (Get-Process -Name LohnMail -ErrorAction SilentlyContinue) {
    throw 'Close all LohnMail windows before exporting.'
}
$Package = @(Get-AppxPackage | Where-Object { $_.PackageFamilyName -eq $PackageFamilyName })
if ($Package.Count -ne 1) { throw 'Select exactly one installed package family.' }
$Workspace = (Resolve-Path -LiteralPath $Workspace).Path.TrimEnd('\')
$Local = [Environment]::GetFolderPath('LocalApplicationData')
$AppData = Split-Path $Local
if ($Workspace -eq $AppData -or $Workspace.StartsWith($AppData + '\', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Workspace must be outside AppData.'
}
$Direct = Join-Path $Local 'Programs\LohnMail'
if ((Test-Path -LiteralPath (Join-Path $Direct 'Settings')) -or (Test-Path -LiteralPath (Join-Path $Direct 'Companies'))) {
    throw 'Additional direct-install data found under Programs\LohnMail. Contact support before merging three stores.'
}
$Sources = [ordered]@{
    ordinary = (Join-Path $Local 'LohnMail')
    redirected = (Join-Path $Local "Packages\$PackageFamilyName\LocalCache\Local\LohnMail")
}
function Inventory([string]$Root) {
    $Files = @{}
    if (-not (Test-Path -LiteralPath $Root)) { return $Files }
    $Pending = New-Object 'Collections.Generic.Stack[IO.FileSystemInfo]'
    $Pending.Push((Get-Item -LiteralPath $Root -Force))
    while ($Pending.Count) {
        $Item = $Pending.Pop()
        if ($Item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Link/reparse point found: $($Item.FullName)" }
        if ($Item.PSIsContainer) {
            foreach ($Child in (Get-ChildItem -LiteralPath $Item.FullName -Force)) { $Pending.Push($Child) }
        } else {
            $Relative = $Item.FullName.Substring($Root.TrimEnd('\').Length + 1).Replace('\', '/')
            $Files[$Relative] = (Get-FileHash -LiteralPath $Item.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        }
    }
    return $Files
}
function Assert-Same($A, $B) {
    if ($A.Count -ne $B.Count) { throw 'Copy verification failed. Originals retained.' }
    foreach ($Key in $A.Keys) { if ($B[$Key] -ne $A[$Key]) { throw "Copy verification failed: $Key" } }
}
$Target = Join-Path $Workspace 'LohnMail-Legacy-Export'
if (Test-Path -LiteralPath $Target) { throw 'An export already exists. Preserve it and choose another empty workspace.' }
$Stage = Join-Path $Workspace ('.lohnmail-export-' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $Stage | Out-Null
$Manifest = @{ format = 1; family = $PackageFamilyName; complete = $true; sources = @{} }
foreach ($Label in $Sources.Keys) {
    $Source = $Sources[$Label]
    $Before = Inventory $Source
    $Copy = Join-Path $Stage $Label
    New-Item -ItemType Directory -Path $Copy | Out-Null
    if (Test-Path -LiteralPath $Source) {
        Get-ChildItem -LiteralPath $Source -Force | Copy-Item -Destination $Copy -Recurse -Force
    }
    Assert-Same $Before (Inventory $Copy)
    Assert-Same $Before (Inventory $Source)
    $Manifest.sources[$Label] = @{ path = $Source; files = $Before }
}
# A completed manifest is published only after BOTH sources have been checked.
foreach ($Label in $Sources.Keys) { Assert-Same $Manifest.sources[$Label].files (Inventory $Sources[$Label]) }
$Json = $Manifest | ConvertTo-Json -Depth 12
[IO.File]::WriteAllText((Join-Path $Stage 'export.json'), $Json, (New-Object Text.UTF8Encoding($false)))
Move-Item -LiteralPath $Stage -Destination $Target
Write-Host "Verified backup: $Target. Originals unchanged. Restart LohnMail with this configured workspace."

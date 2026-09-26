# Windows

This folder owns the Windows build entry points. It builds from the canonical
source; it is not a separate product copy.

Direct build with the integrated LohnMail updater:

```powershell
.\variants\windows\build.ps1
```

Microsoft Store MSIX build:

```powershell
.\variants\windows\build-store.ps1
```

The Store build embeds `store` in `lohnmail_distribution.json`, disables the
direct updater. Settings/license/DPAPI ciphertext use the Windows package
LocalFolder returned by ApplicationDataManager for the current package family.
Virtualization stays enabled; no unvirtualizedResources capability is requested.
First launch uses Documents/LohnMail, resolved with Windows Known Folders.
Companies and History live there, not in the package cache. This path persists
across updates (including if Documents is subsequently redirected elsewhere).
Settings in LocalFolder may be removed when the package is uninstalled.
Existing legacy AppData requires a verified export from ordinary PowerShell
with the app closed: `Export-LegacyStorage.ps1 -PackageFamilyName <PFN> -Workspace <folder>`.
The script discovers both physical stores, hashes copies, and leaves originals.
Use the workspace path shown by LohnMail. Restart to import. Conflicts block
switching, not reset data.
Extra legacy direct-install data requires manual review; it is never merged silently.
The installed-package CI probe uses activation identity and checks LocalFolder,
workspace and upgrade preservation. It is not a Windows 10 GUI/manual test.
Do not publish until installed-MSIX storage and legacy migration tests pass.
The direct build embeds `direct` and keeps the existing update service.

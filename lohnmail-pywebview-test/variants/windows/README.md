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
Since 2.1.2 legacy AppData is exported automatically by the bundled copy-only
StorageExport helper before settings/licensing loads. It independently verifies
native NO_PACKAGE identity before reading both physical stores. No PowerShell
or elevation is required. SHA-256 verified snapshots/originals remain retained.
Existing snapshots are rechecked against live sources on retry, including
prepared-but-interrupted migration. Conflicts block switching, never reset data.
Export-LegacyStorage.ps1 remains a manual support tool, not a required user step.
Extra legacy direct-install data requires manual review; it is never merged silently.
The installed-package CI probe uses activation identity and checks LocalFolder,
workspace and upgrade preservation. It also upgrades an installed synthetic
legacy-layout writer: empty/ordinary/redirected/both/conflicting stores, retained
originals, license, encrypted settings, documents and restart. The CI-only writer
is NOT shipped. This is not the actual previous Store binary or a Windows 10 GUI
test. AppLocker/WDAC/S-mode and redirected/network Documents require separate
verification; blocked helper execution fails safely rather than starting empty.
Do not publish until installed-MSIX storage and legacy migration tests pass.
The direct build embeds `direct` and keeps the existing update service.

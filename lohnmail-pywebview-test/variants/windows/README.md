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
direct updater, and writes runtime data only below `%LOCALAPPDATA%\LohnMail`.
The direct build embeds `direct` and keeps the existing update service.

# Windows

This folder owns the Windows build entry point. It builds from the canonical
source; it is not a separate product copy.

From PowerShell on Windows x64:

```powershell
.\variants\windows\build.ps1
```

Windows-only behavior and packaging belong behind explicit platform checks or
in this folder. Shared product behavior must be corrected in the canonical
source first.

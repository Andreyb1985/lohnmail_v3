# Store 2.1.2: legacy upgrade correction

## Cause

2.1.1 correctly used Windows LocalFolder and Documents/LohnMail on a fresh
installation, but explicitly aborted when legacy AppData existed without a
manually produced export. Thus clean-install success did not prove an old-user
upgrade. The old native CI used two versions of the current layout only.

## Implementation

The storage bootstrap now requests a copy-only native export before reading
settings or licensing. The bundled `LohnMail.StorageExport.exe` is copied to an
isolated temporary workspace directory. Windows desktop-app process policy
allows descendants outside the package; the helper independently requires
`GetCurrentPackageFamilyName == APPMODEL_ERROR_NO_PACKAGE (15700)` before any
legacy AppData read. Failure is a safe stop, never an empty trial/reset fallback.
No PowerShell, shell command, administrator elevation or manifest capability
change is used.

The helper checks the supplied paths against Windows Known Folders and the
current package cache, rejects reparse points, refuses other LohnMail instances,
holds read-only file handles, copies ordinary and redirected stores separately,
and verifies SHA-256 and unchanged sources before publishing `export.json`.
Existing completed exports are revalidated against current sources on retry.
This recheck also runs when an interrupted migration already has prepared
destinations. If the user changed the old data meanwhile, no stale switch occurs.
Incomplete export directories and originals are retained. The existing Python
importer checks both snapshots, stages settings/documents/history, validates
JSON/SQLite, rewrites paths only in new copies and switches its layout pointer
last. Conflicts retain backup copies and stop; they are never silently resolved.

The main app retains virtualization, minimum Windows 10 build 17763 and only
internetClient/runFullTrust capabilities. Windows direct EXE and macOS data roots
are not changed. Windows version becomes 2.1.2 / build 2026.09.27.1.

API reference:
[Microsoft UpdateProcThreadAttribute / desktop app policy](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-updateprocthreadattribute).
Policy alone is not assumed to prove unvirtualized access; native identity and
separate-source preservation are mandatory test assertions.

## Verification scope

- Canonical full suite including final resume guard: 210 passed, 1 skipped, 6 warnings.
- Windows-source full suite including resume guard: 207 passed, 2 skipped, 6 warnings.
- Skips: unavailable separate license-server test; Windows updater E2E additionally
  skipped on macOS. All mail/license/network operations in tests are mocked.
- Import smoke checks, JS syntax, diff checks and tracked runtime/secret filename
  scans passed. Native Windows CI 36314771153 compiled the MSIX, passed the
  Python suite, clean activation/export and current-layout upgrade. Its legacy
  fixture aborted because AUMID activation does not inherit GITHUB_ACTIONS.
  Corrected the CI-only fixture environment guard and handling of unavailable
  AUMID exit codes. No application safety gate was disabled.
- Windows CI 36315089515 passed: 207 tests passed, 1 skipped, 1 warning;
  MSIX build, clean/current-layout upgrade and all five installed legacy cases
  (empty/ordinary/redirected/both/conflict), restart, original hashes, license,
  encrypted settings and documents passed.
- Final Windows CI [36315345767](https://github.com/Andreyb1985/lohnmail_v3/actions/runs/36315345767)
  succeeded at afe11e235f2f38ca13cac7267eb1162468d577f4: 208 passed, 1 skipped,
  1 warning. MSIX build, clean/current-layout upgrade and all five installed
  legacy cases passed again with the final prepared-resume guard and timestamp
  preservation. Branch pushed: feature/microsoft-store-installer.
- Downloaded artifact: `LohnMail-Windows-Store-2.1.2.0/LohnMail_2.1.2.0_x64.msix`,
  50,745,072 bytes, SHA-256
  `7405625c26ef97ef5a9b93c78bb4709f5924158a8d1012dddf4b47ceafea8d2c`.
  Both ZIP CRCs and all 349 block-map files / 1,752 block hashes verified.
  Three app web files and ICO match source; embedded storage helper orchestration,
  migration module and 2.1.2 / 2026.09.27.1 version checked. Native helper included;
  Store identity/marker, minimum build 17763 and capabilities unchanged. No
  customer/runtime files or legacy CI fixture. Unsigned Partner Center package;
  not a signed installer for direct local installation.
- Installed CI uses a separate, synthetic legacy writer package, not the released
  2.1.0 binary. It exercises real package identity/AppData virtualization, then
  upgrades to the current build and checks empty, ordinary, redirected, both,
  conflicts, restart, original hashes and retained license/documents/secrets.

## Still required before public submission

On Windows 10 19045.6456 with a disposable profile, install the real previous
Store build and create synthetic companies/documents. Update WITHOUT uninstall
or Reset. Verify startup, settings/license, send history, Explorer/PDF/Excel
opening, custom output selection, processing and restart. Also test a profile
which already encountered the 2.1.1 startup gate. Never send real payroll mail.

Windows 10 interactive GUI, actual Store delivery, S-mode/AppLocker/WDAC,
OneDrive/junction Documents, network workspaces and real power-loss recovery
are not covered by a Windows Server CI success. Policy-blocked helper execution,
conflicting source copies, a third direct-install data store, and reattaching a
workspace after uninstall must remain visible limitations, not be called fixed.

No Store submission or production update-server publication is authorized here.

## Changed files

Shared canonical code (identical scoped copies in the Windows git worktree):

- `lohnmail-pywebview-test/core/storage_paths.py`: automatic export hook, no
  empty-data fallback, prepared-resume source recheck.
- `lohnmail-pywebview-test/core/windows_storage.py`: native helper orchestration,
  verified response and failure handling, no shell/elevation.
- `lohnmail-pywebview-test/tests/test_storage_paths.py` and
  `tests/test_windows_storage_export.py`: migration and helper protocol regressions.

Windows branch `feature/microsoft-store-installer` only:

- `variants/windows/StorageExport.cs`: copy-only physical snapshot helper.
- `variants/windows/LegacyStorageFixture.cs`: CI-only old-layout writer.
- `variants/windows/build-standalone.ps1`: compile/bundle helper for Store only.
- `variants/windows/test-msix-upgrade.ps1`: installed legacy-upgrade matrix.
- `variants/windows/README.md`: updated migration behavior and limits.
- `ui_web/version.py`: 2.1.2 / 2026.09.27.1; canonical/macOS version unchanged.

Docs updated locally: this report, PROJECT_STATE.md and ARCHITECTURE.md.
Canonical pre-existing dirty files, macOS packaging, icons, production licenses
and the separate update/license server were not changed by this hotfix.

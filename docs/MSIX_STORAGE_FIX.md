# MSIX storage — Windows app-data model, 2026-09-25

## Status

Source changes, NOT a verified Windows release. No commit, push, build,
publication, user-data migration or actual Windows run performed in this task.
Canonical shared code is in lohnmail-pywebview-test. Scoped Windows changes are
also in /private/tmp/lohnmail-windows-icon-test at base 3b280bf.
The complete Windows diff is preserved in docs/msix-storage-windows.patch.
Unrelated dirty macOS/shared work was not copied into that worktree.

This revision REPLACES the earlier virtualization-opt-out proposal.
The manifest keeps virtualization enabled, runFullTrust/internetClient, and
minimum Windows 10 17763. It does not request unvirtualizedResources.

## Evidence / cause

The inspected original MSIX 2.1.0.0 manifest used Windows.FullTrustApplication
without virtualization opt-out. The old code treated LOCALAPPDATA/LohnMail as
both the app's logical storage and the path visible to Explorer.
Microsoft documents a merged AppData view, with private files preferred and
fallback to existing ordinary files. This explains the reported profile-dependent
behavior, but the exact sequence on the two customer PCs has not been reproduced.
The old open handler also created directories, treated an accepted shell command
as proof of opening, and classified drive-letter paths as generic URLs.
The output field opened the folder instead of allowing a replacement.

## Chosen layout

- Windows ApplicationDataManager.CreateForPackageFamily(current family) supplies
  LocalFolder and LocalCacheFolder. GetCurrentPackageFamilyName supplies the
  identity. No username, drive, package version or publisher suffix is embedded.
- LocalFolder/LohnMail/Data/Settings: preferences, companies' metadata,
  license, machine ID and unchanged DPAPI-encrypted SMTP secrets.
- LocalFolder/LohnMail/Data/logs: Windows application diagnostics.
- Windows Known Folder Documents/LohnMail/Companies: default enterprise outputs,
  PDFs, output_pages, audit XLSX and send reports.
- Documents/LohnMail/History: SQLite report/send history and workflow-session JSON.
- An individual company's output_dir may point to another writable folder outside
  AppData. It does not change the enterprise root or settings location.
- The resolved workspace path is recorded in LocalFolder/storage configuration
  once; an update or later Documents redirection does not silently relocate it.
- Input documents are not moved, except path references to migrated Companies
  content are updated in the new settings/history/index copies.
- Custom outputs elsewhere are NOT silently moved. A saved output inside AppData
  must be replaced through the folder chooser before new processing.
- Ordinary EXE/portable/macOS layouts remain unchanged.

Windows resolves Documents: it may be another drive, a network location or
OneDrive. This is the user's configured location, not a guessed home/Documents.
A company output choice remains available through the existing folder picker.

LocalFolder belongs to the app: uninstall/reset may remove settings and license
cache. Documents/workspace are outside the package and retained on uninstall,
but are NOT a substitute for a full backup. Reattaching a workspace after uninstall
is not yet automated; existing workspace metadata causes a safe stop, not
initialization over old data. DPAPI ciphertext is not portable across users/PCs.

## Legacy migration: deliberate safety gate

A packaged process's ordinary AppData view may already be merged. Resolving the
known-folder name with NO_PACKAGE_REDIRECTION does NOT disable file I/O redirection.
Therefore the app does not claim it can independently inspect both physical stores.

When legacy data is found, startup stops before logging/config/licensing loads.
Export-LegacyStorage.ps1 must run once in ordinary Windows PowerShell, with
ALL LohnMail instances closed. It verifies it has NO package identity, obtains
the selected installed package family, copies ordinary and private stores
separately, checks SHA-256 before/after, rejects reparse points, then publishes
a completed export manifest. No source is renamed or deleted.
If an additional Programs/LohnMail data store exists, the script stops for review
rather than implicitly merge a third store.

On restart, the app checks the export family and every hash, retains that export,
and merges only additional disposable copies. Differing same-name/case-colliding
files or incompatible SQLite/WAL/SHM snapshots block switching, with a conflict list.
JSON and SQLite checks run on copies. Known application path fields are remapped;
arbitrary customer documents and license/DPAPI bytes are not rewritten.

Settings, Companies and History are staged on their respective target volumes.
Hashes and a prepared journal are saved before directory renames. Restart completes
a prepared transfer; a failed copy retries in new staging and retains the failed
attempt. The layout pointer is written last. Existing changed targets are not
overwritten. No automatic newest-wins choice, deletion or license reset is used.
Only disposable staging duplicates of the relocated history files are removed;
the original stores and complete export remain recoverable.

After activation of the new layout, old stores are no longer imported. Do not
continue using an old executable against the legacy store: new data written there
will not automatically appear in the new workspace.

## Exact legacy-export procedure (Windows, app closed)

1. Run the new version once to see the resolved workspace path, then close it.
2. Open ordinary Windows PowerShell, not a shell launched from the application.
3. Resolve the installed package with Get-AppxPackage, select the Lohn-mail entry
   and copy its PackageFamilyName. Do not guess the publisher suffix.
4. Run from the source/support-tools directory:

    .\variants\windows\Export-LegacyStorage.ps1 -PackageFamilyName "<actual PFN>" -Workspace "<workspace shown by LohnMail>"

5. Require "Verified backup" and LohnMail-Legacy-Export/export.json in that
   workspace. Restart the new app. On a conflict, keep all originals/exports
   and resolve the conflict with support; do not delete folders to force startup.

The export itself is not automatic. This is a documented migration prerequisite,
not a claim that ambiguous live data can be safely migrated from inside MSIX.

## Folder selection / opening

Choose-folder and open-folder are separate controls. The picker starts in an
accessible user folder, never at the old unavailable/UNC output path. Cancellation
preserves settings. Selection checks write access and atomically saves only that
company's output setting. The UI is refreshed. A missing custom folder is not
recreated just by rendering the processing page.

Open targets must exist. Shell exceptions are returned as failure; success means
only "opening request handed to the system", not proof that Explorer/viewer opened
the folder. Missing targets show their path and direct the user to the existing
choose-another-folder control. New workspace paths are physical paths outside
AppData; inherited custom AppData outputs need explicit replacement.

## Verification

Both full suites run on macOS with isolated temporary LOHNMAIL_DATA_DIR and
existing network/mail mocks:
- Canonical final rerun: 195 passed, 1 skipped, 6 warnings.
- Windows source worktree final rerun: 182 passed, 1 skipped, 6 warnings.
- Direct EXE Windows x64 CI 36258305880: 183 passed, 0 skipped, 1 warning;
  build and command selftest passed (2.1.0 / 2026.09.26.2). Installed MSIX is
  NOT covered by that workflow. See PROJECT_STATE.md for artifact verification.
- Added synthetic coverage: source combinations, hash tampering, conflicting
  licenses, sidecars, interrupted transfer, missing workspace, Documents API,
  package-family API, retained credentials/history, path remapping, arbitrary
  document preservation, output persistence, dialog cancellation, write/open errors.
- Windows cp312/x64 PyWinRT 3.2.1 wheels/dependencies were resolved and downloaded
  successfully for inspection; they were not executed on this Mac.

The Windows CI script now ACTIVATES the installed package via
IApplicationActivationManager. A CLI probe requires real package identity and
rejects LOHNMAIL_DATA_DIR overrides; it reports actual LocalFolder/workspace.
CI checks settings, documents and history across package upgrade, then workspace
retention on uninstall. Merely starting the EXE from WindowsApps no longer counts.
This new CI script has NOT run yet. Native PowerShell parsing is also not verified
here (PowerShell is unavailable on this host).

## Installed-Windows release gate

Use Windows 10 19045.6456, x64, disposable profiles and synthetic documents only.
Do not send mail, contact production licenses for tests or reuse real payroll files.

1. Build Store MSIX with variants/windows/build-store.ps1 after all source tests.
   Run the revised installed-package CI test on a disposable GitHub Windows runner.
2. Clean profile: install/activate via Start menu. Check real Windows Documents/
   LohnMail/Companies and History, and package LocalFolder settings. No folder
   precreation by the tester. Create a uniquely named company.
3. Separate profiles: ordinary legacy only; private legacy only; both with
   non-conflicting records; both with differing settings/license or WAL snapshot.
   Export using the tool; verify originals/hashes, safe conflict stop, no new trial.
4. Process synthetic PDF/XLSX; inspect PDF/output_pages/audit/send reports physically
   from OUTSIDE the app. Open via app buttons in Explorer/Excel/PDF viewer.
5. Choose a company output folder, process, restart and repeat. The enterprise
   workspace must remain fixed; only that company's new outputs use the choice.
6. Close the app, rename its custom output folder, restart. Choose another folder
   without restoring the old one. Repeat with inaccessible UNC and cancellation.
7. Interrupt migration before and between target renames; restart, verify hashes,
   license/machine ID/DPAPI, company metadata, report/send history and links.
8. Upgrade actual old MSIX to the new package. Confirm no loss. Test ordinary EXE
   separately and confirm existing data roots; macOS source regression is separate.
9. Test Documents redirected to another drive/OneDrive/network, lost workspace,
   disk-full and access-denied. Test Explorer denied/association missing honestly.
10. Do not release until native APIs, frozen imports, PowerShell export/activation,
    Windows 10 behavior, real UNC and the above GUI scenarios are confirmed.

## Changed files

Shared: core/storage_paths.py, core/windows_storage.py, core/config.py,
core/jobs.py, main.py, pywebview_app.py, ui_web/bridge.py,
web/app.js, web/index.html, web/styles.css, tests/test_storage_paths.py,
requirements.txt, requirements-windows.txt.
Windows: variants/windows/Export-LegacyStorage.ps1, README.md,
build-standalone.ps1, test-msix-upgrade.ps1, tests/test_windows_store_msix.py.
The manifest opt-out diff was removed, restoring the original manifest.
Documentation: this report, PROJECT_STATE.md, ARCHITECTURE.md and Windows patch.

## Primary references

- [Application data versus user data](https://learn.microsoft.com/en-us/windows/apps/develop/data/store-and-retrieve-app-data)
- [ApplicationDataManager and full-trust access](https://learn.microsoft.com/en-us/uwp/api/windows.management.core.applicationdatamanager)
- [CreateForPackageFamily](https://learn.microsoft.com/en-us/uwp/api/windows.management.core.applicationdatamanager.createforpackagefamily)
- [LocalFolder lifecycle / backup eligibility](https://learn.microsoft.com/en-us/uwp/api/windows.storage.applicationdata.localfolder)
- [Known Folders flags](https://learn.microsoft.com/en-us/windows/win32/api/shlobj_core/ne-shlobj_core-known_folder_flag)
- [MSIX merged AppData behavior](https://learn.microsoft.com/en-us/windows/msix/desktop/flexible-virtualization)

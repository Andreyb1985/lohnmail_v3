# Windows 2.1.6 — reconnect retained workspace

Build: 2026.10.18.2. Based on verified 2.1.5 integration; transparent icon assets
and mail/diagnostics changes are unchanged.

## Cause and fix

Uninstall removes package LocalState, while Documents/LohnMail remains. The
bootstrap previously treated that retained workspace as an unsafe collision and
stopped before startup. Empty-folder fresh install and ordinary upgrade passed.

New startup offers Daten verwenden / Anderen Ordner wählen / Abbrechen.
Reuse first creates a complete sibling backup, verifies file hashes and SQLite,
recovers company identities from available settings/history, then commits a
package-local layout. Documents and History stay at their original location.
Partial commits resume; changed/corrupt/conflicting data are not overwritten.
Choosing another folder or canceling does not modify old business data.
An invalid alternative path can be corrected in the same choice flow.

Existing settings/license/DPAPI copies are preserved without weakening license
checks. Missing LocalState contents cannot be recovered from PDFs. A notice
explains reconfiguration/activation and gives the backup path. No automatic
selection of old AppData or stale legacy exports. Original custom output paths
remain. If only workflow IDs survive, their IDs are used as provisional names.

## Changed files

- core/storage_paths.py: bootstrap choice, commit resume, installed test probe.
- core/workspace_recovery.py: copy-first reconnect, identity/settings recovery.
- core/windows_storage.py: STA choice/folder picker and recovery notice.
- tests/test_workspace_recovery.py; tests/test_workspace_dialog_windows.py.
- variants/windows/test-msix-upgrade.ps1: installed uninstall/reinstall scenario.
- ui_web/version.py; documentation.

## Verification

Canonical macOS suite: 285 passed, 3 skipped, 6 warnings. Import and JS syntax pass.
Windows checkout macOS suite: 283 passed, 5 skipped, 6 warnings.
Windows CI [39169889588](https://github.com/Andreyb1985/lohnmail_v3/actions/runs/39169889588)
succeeded for source commit `69ee072424961cd46dafe3cef727112769ecc8ff`:
286 passed, 2 skipped, 1 dependency warning on Windows x64. Native STA dialog
reuse/cancel tests, frozen EXE build/self-test, packaged browser layout passed.
Installed MSIX activation/storage probes verified uninstall/reinstall with a
retained external workspace, full verified backup, company reconstruction and
restart; prior ordinary/redirected/both/conflicting legacy scenarios also passed.
The intermediate run 39169676399 was cancelled because the final commit added
the unknown-marker guard, not due to a failed test.

Downloaded artifact: `LohnMail_2.1.6.0_x64.msix`, SHA-256:
`4cc23a3370c71ed1ba440e6b8bd2ef24414a778d01e9d1bbb1a5a48154f0e8cc`.
Checked identity/version/Store marker, CRC, 315 entries and 1709 block hashes,
web-source equality, absence of runtime/customer data. Icon audit: 62 transparent
PNGs, 42 PRI mappings, nine embedded ICO sizes and transparent listing PNG pass.
Approved icon files are byte-identical to 2.1.5.

MSIX is unsigned for Partner Center upload. CI installed separate ephemeral
test-signed copies, not the distributed unsigned file. Actual Windows 10 Store
installation, native folder-picker interaction, full app processing after
reconnection and Windows Shell presentation still require manual acceptance.
Use a Store test flight or an explicitly test-signed package for that check;
the unsigned upload artifact is not directly installable on a normal PC.
No actual mail, production license calls or Store/server publication.

## Manual acceptance before Store submission

1. In a disposable Windows 10 profile install the prior MSIX; create a synthetic
   company and documents/history, close the app and uninstall it.
2. Keep Documents/LohnMail, install 2.1.6. Choose cancel: originals unchanged.
3. Restart; choose Daten verwenden. Verify the sibling backup, retained company
   results/history and missing-settings/license notice where applicable.
4. Configure synthetic inputs/test mail only; process/open PDF and Excel. Restart:
   same workspace and no repeated reconnect question.
5. Repeat with another empty folder; old files must remain untouched. Test invalid
   or unwritable paths, backup failure, cancel, and existing conflicting copies.
6. Confirm ordinary upgrade preserves LocalState settings/license, and verify
   approved transparent icons on the actual Windows 10 Shell/Store surfaces.

The backup requires enough free space for the complete workspace; it is not
deleted automatically. Windows Server CI is not a Windows 10 Store deployment.

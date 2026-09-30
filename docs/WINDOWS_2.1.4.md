# Windows 2.1.4 / 2026.09.30.1

## Scope

Canonical shipping-progress changes from main/d5339cd working tree (2026-09-29)
were applied as scoped hunks. Preparation/send operation IDs and snapshot revisions
prevent stale signals/Promise callbacks from hiding live delivery progress.
Threaded mocked worker and actual JS renderer regressions accompany the changes.
Store updater guards, Windows DPAPI, storage migration, Outlook and version
reporting remain intact. No user data, real delivery or macOS changes.

## Shell icons

The supplied desktop link properties identify an AppsFolder/package shortcut,
not a direct EXE link. Windows 10 Search and the desktop are separate surfaces
from the taskbar that the user already confirmed fixed in 2.1.3.

- Packaged runtime preserves Windows' native AUMID; only direct EXEs use
  LohnMail.Desktop.2. Identity query failures never override the Shell identity.
- 28 unplated/lightunplated images remain transparent and ICO is unchanged.
- 34 regular/base/scale/tile images and the manifest use light #F5F8FB instead
  of allowing transparent areas of plated icons to reveal the accent color.
- A build gate checks decoded pixels of all 62 packaged PNGs, 42 actual PRI
  target/form-to-path mappings, manifest color and nine ICO images inside EXE.
  Unit regressions reject corrupted image, PRI mapping, manifest and EXE.

This does NOT claim universally transparent Search icons. Microsoft documents
the Windows 10 Search plate as system behavior for UWP; LohnMail is full-trust
Win32/MSIX, so its installed rendering still needs direct verification.
Changing the manifest alone is not claimed to fix Search. Existing shortcut
caches may differ from newly created links. No automatic cache deletion, link
replacement or WindowsApps permissions change is performed.

References:
- https://learn.microsoft.com/en-us/answers/questions/1387295/why-are-windows-10-search-icons-of-uwp-apps-displa
- https://learn.microsoft.com/en-us/uwp/schemas/appxpackage/uapmanifestschema/element-uap-visualelements
- https://learn.microsoft.com/en-us/windows/apps/design/iconography/app-icon-construction

## Verification before CI

verify-lohnmail followed. Local targeted 37 passed, 6 warnings; canonical full
217 passed, 1 skipped, 6 warnings; Windows source on macOS full 219 passed,
2 skipped, 6 warnings. Skips: native Windows updater and separate license-server
repository test in the Windows worktree. Python imports, JS syntax, diff and
tracked runtime/secret scans passed. Light and transparent preview inspected.
An initial too-strict test compared unused RGB bytes of fully transparent
pixels; corrected the expected alpha-composite operation, product unchanged.

## Required before Store publication

Successful Windows x64 CI and artifact validation, then interactive Windows 10
19045 checks: existing and new desktop shortcuts, Search, Start, pinned/unpinned
taskbar, Alt-Tab and title bar, light/dark theme, 100/125/150/200% DPI.
Repeat after an in-place Store update without uninstall/data reset. Check mocked
or test-mail progress across preparation/send, partial failure and repeated runs.
Windows Server CI is not proof of these Windows 10 Shell visuals.
Do not publish merely because an ordinary EXE looks correct.

## Windows CI and downloaded artifact

Commit 93250682768640c364224050937267ec64e11ff0 was pushed to
feature/microsoft-store-installer. Run
https://github.com/Andreyb1985/lohnmail_v3/actions/runs/36720536287 succeeded.
Windows Server 2025 x64 / Python 3.12: 220 passed, 1 skipped, 1 warning.
Skip requires the separate license-server checkout. Native EXE/MSIX build,
icon payload gate, Edge empty/normal activity layout, installed synthetic upgrade
and five legacy data scenarios (empty, ordinary, redirected, both, conflict)
passed. The CI uses disposable synthetic fixtures, not the old published binary.

Downloaded MSIX: LohnMail_2.1.4.0_x64.msix, 49,756,776 bytes.
SHA-256: e8f61fe3ca498332d3ce0c444329058ed2fecfac16b8ca4eed9284163182f2bc.
ZIP CRC, 311 block-map files, 1,707 block hashes and 56 whole-file hashes verified.
Three shipped web files match source; marker is store; no runtime/customer files
or test certificates. All 28 transparent variants are pixel-identical to 2.1.3.
Actual Edge activity-log screenshot inspected. This is an unsigned Partner Center
submission artifact, NOT a double-click sideload installer. Store/update-server
publication was not performed. Existing user data and installed apps untouched.

## Changed files

- Shared shipping: ui_web/bridge.py, web/app.js, tests/test_pywebview_adapter.py,
  tests/test_shipping_progress_order.py.
- Windows identity: pywebview_app.py (Windows branch only),
  tests/test_windows_app_identity.py.
- Windows assets/build: variants/windows/build-msix-assets.py, verify-icons.py,
  build-store.ps1, msix/AppxManifest.xml.in; tests/test_msix_assets.py,
  tests/test_packaged_icons.py; .github/workflows/build-windows-store.yml.
- Windows version: ui_web/version.py. Documentation: this report and canonical
  docs/PROJECT_STATE.md.

verify-lohnmail shaped the scoped transfer, full-suite runs, no-real-mail policy,
artifact safety checks and separation of build evidence from Shell acceptance.

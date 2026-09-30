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

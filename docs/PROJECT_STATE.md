# LohnMail project state

Last reviewed: 2026-09-28

## Canonical Git snapshot — 2026-09-28

- Prepared current shared source, platform entry points and regression tests
  for main, compared against remote main/fe52aba. Summary in CHANGES-2026-09-28.md.
- Isolated full suite: 212 passed, 1 skipped, 6 warnings. JS syntax and diff
  checks passed. No generated builds or user/runtime data selected for commit.
- Separate license-server edits and platform release branches are outside this
  canonical-source push; no build or deployment is implied.

## Store 2.1.2 visual regression diagnosis — 2026-09-28 (not fixed)

- User screenshots show the empty processing activity title wrapping into a
  narrow column and a plated taskbar logo after Store upgrade.
- Verified in source and downloaded 2.1.2 MSIX: the three-child `.log-empty`
  markup is overridden by `.operation-log .log-list > div` with four columns
  (68px, 22px, title, detail). The empty title is auto-placed in the 22px column;
  `overflow-wrap:anywhere` explains the near-vertical text. Empty-state styling
  must be separated from regular timestamped entries.
- MSIX has only five base PNG assets, no targetsize/unplated/lightunplated
  variants and no resources.pri. Square44x44Logo visibly contains a white
  rounded background despite transparent corners. The separate EXE ICO has
  nine transparent representations; its earlier correction did not replace
  these Store assets. Microsoft icon documentation explains the taskbar
  backplate/scaling fallback when unplated variants are absent.
- Read-only source/artifact diagnosis; canonical responsive tests: 6 passed.
  Those tests do not exercise empty-log browser geometry or installed MSIX
  taskbar rendering. No full-suite rerun, new build, push, publication, user-data
  changes or product-code edits. Windows cache contribution and actual corrected
  rendering remain unverified. Only this diagnostic record was added.

## Store legacy-upgrade hotfix — 2026-09-27 (Windows CI verified, NOT released)

- User confirmed clean 2.1.1 installation works, but a Store update with legacy
  AppData fails before startup: the old safety gate required a manual export.
  The earlier native CI covered current-layout upgrades, not legacy migration.
- Implemented automatic copy-only export through a bundled Windows helper.
  It must verify APPMODEL_ERROR_NO_PACKAGE before reading both physical stores;
  the normal application keeps MSIX virtualization and Windows LocalFolder plus
  Documents/LohnMail. No new restricted capability or macOS change.
- Sources and verified export retained; differing copies still stop without a
  license reset/empty-data fallback. Existing exports rechecked against sources.
- Local targeted storage suite initially 43 passed, 6 warnings. Final full
  canonical: 210 passed, 1 skipped, 6 warnings; Windows source: 207 passed,
  2 skipped, 6 warnings. Includes helper protocol and prepared-resume tests.
- New CI installs a separate legacy-layout writer fixture and tests empty,
  ordinary, redirected, both and conflicting stores, then restart. This is a
  synthetic old-layout fixture, NOT the previously published 2.1.0 binary.
- Windows CI 36315089515 passed at 33468f6: 207 passed, 1 skipped, 1 warning;
  compiled MSIX, clean/current-layout upgrade, all five installed old-layout
  cases, restart and source-hash preservation passed. Earlier CI-only fixture
  environment/ExitCode issues corrected without weakening product safeguards.
- Final candidate afe11e2 rechecks originals even on prepared-journal resume
  and preserves copied file timestamps. Windows CI 36315345767 succeeded:
  208 passed, 1 skipped, 1 warning; MSIX install/upgrade and all five legacy
  scenarios passed. Actual Windows 10 / previous Store-binary upgrade remains
  a separate pre-publication check (see docs/MSIX_UPGRADE_2.1.2.md).
- Downloaded LohnMail-Windows-Store-2.1.2.0/LohnMail_2.1.2.0_x64.msix:
  50,745,072 bytes, SHA-256
  7405625c26ef97ef5a9b93c78bb4709f5924158a8d1012dddf4b47ceafea8d2c.
  CRC, 349 block-map files / 1,752 block hashes, three web-source files,
  unchanged ICO, embedded storage modules/version and Store marker checked.
  Helper present; no customer/runtime files or CI fixture. Unsigned Partner
  Center submission package; no Store or update-server publication performed.

## Windows Store 2.1.1 — 2026-09-26 (MSIX build verified in CI)

- Requested MSIX build from Windows etalon refresh 645cff1. App version raised
  to 2.1.1 / build 2026.09.26.4, producing MSIX 2.1.1.0 above previous 2.1.0.0.
- Previous automatic Store run 36261017724 built MSIX but failed installed
  storage activation with no probe report. Added failure diagnostics to the
  canonical shared probe and Windows CI consumer; no validation gate bypassed.
- Preparation commit 1a284fc pushed to feature/microsoft-store-installer.
  Local Windows-source suite: 194 passed, 2 skipped, 6 warnings; JS/diff and
  tracked runtime/secret checks passed.
- Diagnostic run 36263547375: build succeeded; installed probe correctly
  refused legacy data seeded by earlier unisolated source/EXE tests. Commit
  e991996 scopes LOHNMAIL_DATA_DIR to the CI build step only. Installed-package
  tests retain real package identity and no data override. Full local retest:
  194 passed, 2 skipped; canonical: 197 passed, 1 skipped (6 warnings each).
- Windows CI 36263894003 succeeded at e991996: 195 passed, 1 skipped,
  1 warning; EXE self-test, MakeAppx pack/unpack, installed AUMID activation,
  LocalFolder/workspace checks, synthetic package upgrade and preservation
  of Settings/Companies/History sentinels passed. Uninstall retained workspace.
  Skip: separate license-server repository test. CI uses Windows Server runner,
  not Windows 10/11 interactive GUI or a real legacy-user migration scenario.
- Downloaded LohnMail-Windows-Store-2.1.1.0/LohnMail_2.1.1.0_x64.msix:
  50,734,577 bytes; SHA-256
  b577610683479545b5fc41d5086a620e88f57f64b08bace74085fe7637e73db9.
  ZIP CRC, 348 block-map file entries / 1,751 block hashes checked. Source web
  files match after CRLF normalization; embedded version/TLS/Lifetime/storage
  verified. Real Store identity and marker, transparent icons and no customer
  data confirmed. Unsigned Partner Center submission package, not a locally
  signed sideload installer. CI test certificates were disposable and not shipped.
- No Store submission or update-server publication requested or performed.

## Windows etalon refresh — 2026-09-26 (test build complete)

- User requested rebuilding the Windows test/update package after canonical
  changes. Version 2.1.0 / 2026.09.26.3; commit
  645cff1 on feature/microsoft-store-installer. Windows CI 36261026152 succeeded.
- Imported canonical removal of the three horizontal workflow strips,
  neutral company placeholders, operation-log wrapping, shared verified TLS
  context and positive Lifetime normalization/UI indicators with regression tests.
- Preserved Windows Store updater guards/distribution metadata/privacy text,
  Outlook Classic, version reporting, DPAPI, MSIX storage fixes and transparent
  multi-size icons/caption. No macOS assets/entitlements/build scripts imported;
  no separate shared-code directory introduced. Canonical edits remain intact.
- Local targeted: 46 passed, 1 skipped. Full canonical: 196 passed, 1 skipped,
  6 warnings. Full Windows source on macOS: 193 passed, 2 skipped, 6 warnings
  (Windows-only E2E and separate license-server route test). JS/import/diff
  checks and tracked runtime/secret scans passed. All mail/license tests mock
  external requests; no real delivery or production-license mutation.
- Native Windows CI: 194 passed, 1 skipped, 1 warning; the skipped test requires
  the separate license-server repository. Windows updater E2E and EXE self-test
  passed. Downloaded artifact CRC, size, SHA-256 and payload comparison passed.
  Packaged HTML/JS/CSS match source; embedded version, TLS, Lifetime and storage
  modules verified. Both EXEs include all nine transparent ICO sizes.
- Clean template settings and empty Companies verified in the portable package;
  update ZIP contains only App, without customer data or runtime secrets.
  Output: LohnMail-Windows-2.1.0-build-2026.09.26.3-test/ (repository root).
  Update ZIP size: 48,942,511 bytes; SHA-256:
  4adb7bdbb1fd49ac2e1d8eb6c362edb6ed0e44e93c061dc5cf2aaa57986b8484.
- No Store or update-server publication performed. This is a direct portable
  EXE build, not an installed MSIX verification. Windows desktop visual checks,
  installed MSIX storage/migration and published update delivery remain unverified.

## Local macOS rebuild 202609048 — 2026-09-26

- Rebuilt canonical dirty main/fe52aba as ARM64 2.0.3 / 202609048,
  including removal of the three horizontal workflow strips.
- Full isolated suite: 195 passed, 1 skipped, 6 warnings. Imports,
  JS/shell syntax, dependency consistency and diff checks passed.
- Bundle deep/strict ad-hoc signature verified; packaged HTML/JS/CSS and
  approved ICNS byte-match source. No workflow-card sections or runtime/customer
  filenames found in artifact. Previous app/onedir retained under
  dist/local-archive-before-202609048; user data and installed app untouched.
- Changed only local build number and this record. GUI launch, production
  licensing, real mail and notarization were not tested in this rebuild.
  Output: lohnmail-pywebview-test/dist/LohnMail.app, local preview only.

## Workflow strip removal — 2026-09-26

- Removed the large horizontal six-step workflow strips from Verarbeitung,
  Prüfung and Versand in canonical web/index.html. Their sections no longer
  reserve layout space. Action buttons, progress and underlying workflow remain.
- Verification: 195 passed, 1 skipped, 6 warnings; JavaScript syntax and diff
  checks passed. No matching workflow-card sections remain in HTML.
- Native GUI and packaged builds were not exercised; no build/publication done.

## Local macOS licensing rebuild — 2026-09-26

- Built canonical dirty main/fe52aba as local ARM64 2.0.3 / 202609047.
  Only the local build number was changed; existing source changes preserved.
  Previous app/onedir retained in dist/local-archive-before-202609047.
- Full suite with isolated LOHNMAIL_DATA_DIR: 194 passed, 1 skipped, 6 warnings.
  Initial non-isolated invocation failed 17 tests on sandbox-denied settings
  writes; rerun used temporary data, without broadening user-data permissions.
  Imports, JS/shell syntax, diff check and dependency consistency passed.
- Ad-hoc deep/strict bundle signature verified. Packaged JS and approved white
  ICNS match source; PYZ contains lifetime normalization. Runtime/customer file
  scan clean (SQLite binary libraries are dependencies, not user databases).
- Native app opened. License screen subsequently reported connected server but
  existing license not found/invalid, with 14-day transition grace. This is not
  a successful production Lifetime activation; no license reset or activation
  performed. User data was not cleared; normal startup/check may update cache.
- Not an App Store/notarized release. Real mail/payments, complete workflow,
  and server-side license correction were not verified or performed.

## Windows MSIX storage and folder selection — 2026-09-25

- Added canonical shared storage migration, per-company output selection,
  atomic settings save, strict file-target checks and honest shell-request
  messages. Scoped equivalents are applied in Windows worktree
  `/private/tmp/lohnmail-windows-icon-test` at base `3b280bf`; no unrelated
  dirty macOS/shared changes were transferred.
- Revised per user decision: virtualization remains enabled; no opt-out or
  unvirtualizedResources capability. Original minimum Windows 10 17763 restored.
  Native ApplicationDataManager resolves package LocalFolder for settings/license;
  Windows Known Folders resolves Documents/LohnMail for Companies and History.
  Documents is the default without first-launch folder prompting. Per-company
  output choices remain separate. Ordinary EXE/macOS storage stays unchanged.
- Legacy data requires the verified Export-LegacyStorage.ps1 snapshot from an
  unpackaged PowerShell first: the packaged process cannot reliably distinguish
  both physical AppData stores. Originals retained; hash/conflict/SQLite checks,
  staged transfers, last-written layout pointer and restart recovery added.
  No silent merge/reset. Additional Programs/LohnMail data requires manual review.
- Windows installed-package CI test now activates by AUMID and requires verified
  package identity, LocalFolder and workspace paths. Tests upgrade and workspace
  retention on uninstall. This CI revision has not been run yet.
- Real existing MSIX 2.1.0.0 manifest inspected. Detailed diagnosis, path map,
  migration/conflict policy and installed-Windows test steps are recorded in
  `docs/MSIX_STORAGE_FIX.md`.
- Local synthetic isolated suites: canonical 194 passed, 1 skipped, 6 warnings;
  Windows source 181 passed, 1 skipped, 6 warnings. Windows x64 Python 3.12 API dependency
  wheels resolved/downloaded, not executed. No native Windows result is claimed.
- NOT verified: installed MSIX, Windows x64 build/CI, Explorer/Excel/PDF GUI,
  clean Windows profile, actual redirected-data upgrade, power loss, real UNC,
  Store approval or publication. No build/push/deployment/user-data migration
  was performed at that stage. Do not label this a verified Windows release.

## Windows EXE test build — 2026-09-26 (Windows CI verified)

- User requested a Windows build before Store upload; no Store/update-server
  publication is authorized. Final version 2.1.0, build 2026.09.26.2.
- Scoped Windows commit 2314d58 pushed to feature/microsoft-store-installer;
  GitHub Windows x64 CI 36258047898 dispatched. Includes the previously tested
  transparent/DPI icon and caption fixes plus the new storage/folder changes.
- Local Windows-source suite: 181 passed, 1 skipped, 6 warnings. JS syntax,
  import smoke from app directory, diff and tracked runtime/secret checks passed.
  An initial import check from repository root found the legacy core instead;
  corrected cwd passed. First Windows run: 182 passed, 1 warning; EXE selftest
  and build passed. This first artifact was not handed off.
- Final review fixed three storage metadata reads to explicit UTF-8; added an
  interrupted-transfer regression with a Unicode workspace and simulated cp1252
  default. Canonical 195 passed, 1 skipped, 6 warnings; Windows source 182 passed,
  1 skipped, 6 warnings on macOS. JS/import/diff checks passed.
- Final commit 4000cd73e45393b0d31a4068897c3d3506051dab pushed to the same feature
  branch. Windows x64 CI 36258305880 passed: 183 passed, 0 skipped, 1 warning;
  PyInstaller EXE build and command selftest succeeded. No GUI visual result is
  inferred from the selftest. Runner is Windows Server 2025, not Windows 10.
- Downloaded to LohnMail-Windows-2.1.0-build-2026.09.26.2-test. Both EXEs contain
  all nine exact transparent ICO representations. Packaged web content matches
  source after CRLF normalization. Update ZIP CRC, every payload byte, size and
  SHA256 verified; template-only settings, empty Companies, no customer documents,
  SQLite, secrets or licenses. WinRT binaries included; packaged API not invoked.
  ZIP: 48,941,336 bytes; SHA256
  1c5d3c006ff77d502b29201a4e72d2c19b2bea9f28fd7e84757cc4267338bf3d.
- Build log also contains PyInstaller warnings for Android/pycparser optional
  imports and Windows API-set DLL resolution. Build/EXE selftest passed; this
  does not prove WinRT execution under installed package identity on Windows 10.
- This workflow builds direct/portable EXE only. It does not exercise installed
  MSIX storage virtualization or the installed-package upgrade probe.
- No Store/update-server publication, no actual user-data migration or delivery.

## Trial to Lifetime conversion — 2026-09-25

- Confirmed two causes in local source: server type edits preserved positive
  Trial status and computed access from historical dates; client merged these
  dates into cached entitlement and UI state. Key prefixes do not determine rights.
- Server (separate `license-server` repository) now normalizes positive Lifetime
  statuses on admin edits and reads; access deadline/countdown are null while
  Trial history remains. Desktop applies the same positive-status normalization,
  ignores historical dates for Lifetime rights, and renders Aktiv / Lifetime /
  Unbefristet. Manual checks immediately refresh header/footer indicators too.
- Tests exercise real start-trial/admin-update/check route handlers with an
  in-memory SQL boundary, then feed their responses into the client. Also cover
  manual and scheduled checks, same key, restart, previous Trial expiry, renderer
  indicators, revocation, device mismatch, missing-license grace and the unchanged
  30-day Lifetime offline limit. No production records or payments are touched.
- Verification: desktop **160 passed, 1 skipped, 6 warnings**; separate server
  **51 passed, 0 skipped**. Actual JavaScript license renderer executed with DOM
  stubs; Python imports, JS syntax, both diff checks and tracked desktop
  runtime-data/secret scans passed. Native GUI appearance was not exercised.
- No deployment, packaged build or live production end-to-end test performed.

## Isolated macOS Windows-interface demo — 2026-09-24

- Follow-up repair, build **2026092402**: initial demo fixture omitted an
  entitlement expiry, so `require_action('processing')` denied work despite
  the active-looking trial label. Added a 60-day expiry only to the isolated
  fixture; production licensing is unchanged. New regression assertion failed
  before the fix and passed after. Extended subprocess test invokes real
  `WebBridge.startCheck()` with synthetic PDF/Excel and verifies completion and
  an audit XLSX (DNS mocked). Full suite: **150 passed, 1 skipped, 6 warnings**;
  Python/JS/shell syntax and diff checks passed.
- Rebuilt and verified ad-hoc deep/strict signature; runtime/customer filename
  scan clean. Previous app preserved in `previous-2026092401`; sibling UserData
  retained. Launched rebuilt bundle and clicked the actual check action with
  the user's selected demo PDF/Excel: **100%, 3 processed, 0 warnings, 0 errors**
  in the native UI. No email sent. Sending and complete tutorial flow remain
  outside this verification; external delivery remains deliberately blocked.

- Added standalone `variants/macos/windows_ui_demo.py` and its dedicated build
  script, plus a subprocess isolation/safety test. Production entry points,
  platform checks, license rules and existing dirty changes were not altered.
- Exposes Windows Outlook/update UI on macOS for tutorial use only. Real mail,
  Outlook connections, license HTTP/payment actions, update downloads/installation
  and external socket connections are blocked. Offline trial state is a demo
  fixture, not an activated production license; SMTP secrets stay in memory.
- Full suite: **150 passed, 1 skipped, 6 warnings**. Dedicated test: **1 passed**.
  Python compilation, JS/shell syntax and diff checks passed; tracked runtime-data
  and likely-live-secret scans returned no matches.
- Built native ARM64 `dist/windows-ui-demo-20260924/LohnMail Windows UI Demo.app`,
  bundle ID `de.lohnmail.windows-ui-demo`, build `2026092401`. Ad-hoc strict/deep
  signature verification passed. Approved bundle ICNS hash matched; artifact
  filename scan found no runtime/customer data, PDF or Excel documents.
- Launched actual bundle. UI showed empty tenant selection, no imported files,
  blank SMTP account, Outlook account control and Updates tab. Data is isolated
  in sibling `UserData`, not the existing application data directories.
- Not verified: complete tutorial workflow, actual Windows rendering, actual
  Outlook/SMTP delivery, App Store distribution or notarization. Native macOS
  window chrome and file dialogs remain macOS. Existing releases/data preserved.

## Windows caption/DPI test — 2026-09-22

- Applied Windows-only caption and icon corrections first to canonical
  `pywebview_app.py`, then the Windows worktree: explicit x64 ctypes argument
  signatures, DPI system icon metrics, before_show/shown configuration, frame
  invalidation. Original transparent artwork unchanged. Added four mocked DPI
  cases (100/125/150/200%). macOS-specific code/assets untouched.
- Canonical suite: 149 passed, 1 skipped, 6 warnings; Windows-branch local suite:
  147 passed, 1 skipped, 6 warnings. Initial canonical invocation from repository
  root imported legacy modules and failed collection; rerun from documented app
  directory passed. Python compilation, JS syntax and diff checks passed.
- Commit `3b280bf0f6b647edd2c55137873338a2bb656a69`, build 2.1.0/2026.09.22.2.
  Windows CI `35745721705`: 148 passed, 1 warning; EXE build/selftest succeeded.
  Downloaded artifact in `lohnmail-pywebview-test/dist/windows-caption-dpi-2026.09.22.2/`.
  ZIP CRC/size/hash, packaged icon equality and customer-data exclusion passed.
  SHA256: `7ba3c49c83cd9a42d1e9289ca102d37c5a6e742394142ca95d78e503b73b0976`.
- Actual first-frame caption and taskbar appearance on user's Windows/DPI remain
  unverified; no new artwork, MSIX, Store publication or updater deployment.

## Windows transparent EXE icon test — 2026-09-22 (Windows CI verified)

- Prepared in isolated worktree `/private/tmp/lohnmail-windows-icon-test`, based
  on Windows Store branch commit `75dd207`; canonical macOS changes preserved.
- Converted existing transparent artwork to ICO with 16/20/24/32/40/48/64/128/256
  representations; added alpha/corner/coverage regression test and repeatable
  Windows conversion script. Test build identifier: `2.1.0 / 2026.09.22.1`.
- Local suite: **143 passed, 1 skipped, 6 warnings**; JavaScript syntax and
  diff whitespace checks passed; tracked runtime-data and secret scans clean.
- After explicit user permission, pushed commit `ce9b897eb4f662d5f0ddc8279113cf3c0862bafd`
  to `feature/microsoft-store-installer`. Windows x64 CI run `35738113929`
  succeeded: **144 passed, 1 warning**, PyInstaller build and EXE selftest passed.
- Downloaded to `lohnmail-pywebview-test/dist/windows-transparent-icon-2026.09.22.1/`.
  Both root launcher and application EXE contain all nine exact ICO image
  resources; packaged ICO matches source. Settings contain no accounts/secrets,
  Companies contains only its empty marker; application has no runtime/customer
  database or document files. Update ZIP CRC, size and SHA-256 match metadata
  (`2f4e7bec2c5948f76f38e40174e7658398854856b861c8ebdb38619f64b45e54`).
- No Store/update-server publication occurred. Actual taskbar GUI appearance,
  MSIX unplated assets, signing, real mail and licensing remain unverified.
  This is an isolated icon test based on the Windows branch, not a merge of
  later uncommitted canonical macOS/shared changes.

## macOS local rebuild verification — 2026-09-19

- User requested a local rebuild with current etalon changes for testing; no publication or installed-app replacement requested.
- Source: shared `lohnmail-pywebview-test/`, branch `main`, HEAD `fe52aba` plus preserved existing working-tree changes. macOS local build number advanced to `202609046`.
- Targeted UI/macOS/adapter tests: **37 passed, 6 warnings**. Full suite: **145 passed, 1 skipped, 6 warnings**.
- JavaScript syntax, shell syntax, `git diff --check`, and Python import smoke checks passed. Tracked runtime/customer filename and likely-live-secret scans returned no matches.
- Native ARM64 local build **202609046** completed at `lohnmail-pywebview-test/dist/LohnMail.app`; ad-hoc signature passed `codesign --verify --deep --strict`. Existing local outputs were preserved under `dist/local-archive-before-202609046/`; installed and website distributions were not replaced.
- Packaged HTML, JavaScript and CSS byte-match current shared source, including the neutral company placeholders. The bundle ICNS byte-matches the approved macOS asset. Artifact filename scan found no Settings/Companies, runtime secrets/license/database files, customer PDF or Excel files.
- Launched the explicit new bundle path with native app control: dashboard rendered and remained running. This is a local preview, not an App Store or notarized website release. Startup may contact the license server; no end-to-end licensing claim is made.
- Real SMTP, production licensing/payments, full manual workflow, Windows, and App Store distribution were not verified in this rebuild.

## Current working version

- Branch: `main`
- HEAD: `fe52aba` (`docs: mark Windows build 2026.09.03.1 verified`)
- Desktop version: `2.0.3`
- Desktop build: `2026.09.03.1`
- `TEST_UPDATES_ENABLED = True`
- The source tree is not clean. Nine tracked files contain uncommitted macOS-preview changes, and three macOS build files are untracked. The exact list must be read with `git status --short` before new work.

The last documented Windows artifact for `2.0.3 / 2026.09.03.1` is verified in `lohnmail-pywebview-test/RELEASE-STATUS.md`: Windows CI passed, the production-channel package/hash/ZIP were checked, and a real Windows update was confirmed on 2026-09-03. The current dirty working tree is newer/different and is not covered by that release verification.

## Current architecture

The active app is Python + pywebview with a local HTML/CSS/JavaScript UI. Python handles local files, PDF/Excel processing, mail, SQLite history, licensing, and updates. The browser layer talks to Python through `ApiAdapter`/`WebBridge`. Details are in `docs/ARCHITECTURE.md`.

## Implemented functions confirmed in code

- PDF folder or combined-PDF scanning and personnel-number matching.
- Excel employee/e-mail import and validation, including duplicate handling and optional DNS/MX checks.
- Verified PDF merge, password protection, audit/missing-address/send reports, and per-company output folders.
- Selection-aware payroll sending and dry-run mode.
- SMTP and Windows Outlook Classic sending with user-facing error mapping.
- Mass messages with recipient validation and optional file attachments.
- Global and per-company mail settings; SMTP passwords protected outside JSON.
- Multiple companies, saved input paths, workflow sessions, and SQLite report/send history.
- Online trial/subscription/lifetime licensing, device binding, offline grace, deleted-license transition grace, Stripe checkout/invoice/customer-portal requests through the server.
- Windows update check/download/hash/signature validation, SQLite pre/post checks, backup, rollback, and relaunch.
- Responsive desktop UI, notifications, help, reports, settings, and license views.

## Active task

Prepare the first macOS App Store test upload from the current macOS source. Signed ARM64 build `202609042` exists and passed local structural/signature inspection; upload and TestFlight execution remain pending.

## Completed in this task

- 2026-09-17, removed a real company name and ID from the canonical company-
  creation placeholders and replaced them with the neutral examples
  `Musterunternehmen GmbH` / `musterunternehmen`. Added a UI contract test and
  confirmed that the active desktop source contains no remaining `VRWK` or
  `Verwaltung GmbH` references. Targeted tests: `29 passed, 6 warnings`; full
  suite: `145 passed, 1 skipped, 6 warnings`. JavaScript syntax, diff, tracked
  runtime-data, and secret scans passed. No build or publication was performed.
- 2026-09-16, German tutorial preparation only (no product/build changes):
  created `dist/tutorial-de-DE` with a synthetic three-employee workbook, a
  three-page clearly labelled demo PDF, a five-chapter outline, and an isolated
  source-session launcher. The launcher mocks licensing/DNS, keeps SMTP secrets
  in memory, blocks real sending and non-loopback socket connections. No real
  customer data or Keychain changes were made. Native demo window opened and
  accessibility inspection confirmed an empty company list. Workbook exported
  successfully; read-back confirmed leading-zero personnel IDs and real date
  values with date formats. Artifact renderer shows date serials in its preview,
  so that PNG is not a final tutorial visual. PDF first page was visually checked
  using PyMuPDF after bundled Poppler encountered fontconfig problems.
  No videos recorded: macOS recording-panel invocation via computer-use timed
  out. Published artifact, real SMTP, licensing, and full regression suite were
  not tested in this media-only task. Existing code changes were preserved.
- 2026-09-15, website build 202609045 started with separate white bundle and
  transparent runtime Dock icons. Source remains dirty on main/fe52aba;
  unrelated changes were preserved. Targeted tests: `31 passed, 6 warnings`;
  full suite: `144 passed, 1 skipped, 6 warnings`. JavaScript/shell syntax,
  import smoke and diff checks passed. Previous website output is preserved
  in `dist/website-archive-202609044`. User data and installed apps were not
  touched. Completed Developer ID signing and Apple notarization (Accepted,
  submission `f46fad0c-10aa-428b-b642-19d377fca818`); stapling/ticket validation
  and Gatekeeper passed. The read-only mounted DMG app passed strict deep
  signature verification and Gatekeeper (`Notarized Developer ID`). Both
  packaged icon hashes match their respective approved sources. Packaged
  bytecode inspection confirms the transparent Dock override is enabled for
  frozen apps. No customer/runtime filenames or quarantine attribute were
  found; the settings template is clean. Final ARM64-only artifact:
  `dist/website/LohnMail-2.0.3-202609045-macOS-arm64.dmg`, SHA-256
  `6dd7fb6d17d91e3b539440d16a1db5d8a212253c9f792ab75ad37fb6685d99e8`.
  The verification image was detached. GUI launch/Dock rendering, clean-Mac
  installation, real SMTP/license calls and website publication were not
  performed. Existing user data and installed app remain untouched.
- 2026-09-13, separated icon roles after user feedback on build 202609044:
  Finder/application-launcher keeps the white bundle ICNS; a running macOS app
  (source or frozen) now applies the original transparent PNG via the named
  `MACOS_DOCK_ICON_PATH`. In-app branding and Windows artwork are unchanged.
  No menu-bar tray/status-item implementation exists in the active source;
  the reported tray was interpreted as Dock and this assumption was stated.
  Tests cover frozen/source selection, missing-asset fallback, the original
  PNG hash, Windows isolation and white ICNS packaging. Targeted tests:
  `31 passed, 6 warnings`; full suite: `144 passed, 1 skipped, 6 warnings`.
  Import, JavaScript syntax and diff checks passed. No new DMG was built and
  no installed app or user data was changed. Actual Dock appearance remains
  unverified; before launch/after exit it may use the white bundle icon.
- 2026-09-13, website rebuild 202609044 preparation: full suite
  `142 passed, 1 skipped, 6 warnings`; shell/JavaScript syntax and diff checks
  passed. Previous website output moved to `dist/website-archive-202609043`.
  At the user's request, while LohnMail was not running, its website/source
  data directory was moved from
  `~/Library/Application Support/LohnMail-macOS-Test` to
  `~/Library/Application Support/LohnMail-macOS-Test-backup-before-202609044`
  (19 MiB). No customer data was deleted; Keychain credentials, external input
  documents, TestFlight containers and server-side licenses were not changed.
  The rebuilt application contains the pinned white ICNS, inspected visually.
  Completed Developer ID signing and notarization: Apple submission
  `b7ab1983-f956-4f6f-abc3-ed2d4b34a63f` was Accepted; stapling and ticket
  validation passed. Both the DMG and its read-only mounted application passed
  Gatekeeper (`Notarized Developer ID`); strict deep app signature verification
  passed. Mounted payload build is 202609044 and ICNS hash matches
  `0dda034b1d99ade7e2cb24daad219e1b4ab69c01f05f8da62518556934d57198`.
  No customer/runtime filenames or quarantine attribute were found in the
  application, and its settings template has no companies, license key or SMTP
  account. Final DMG: `dist/website/LohnMail-2.0.3-202609044-macOS-arm64.dmg`;
  SHA-256 `ac5c49f1668bfa2e7a685b9e1af7172db3f9efc9008f15265449bff156f83226`.
  ARM64 only. The image was detached after verification. The installed app was
  not replaced or launched, leaving the active data folder absent for the user's
  clean-start test. SMTP/online licensing, clean-Mac GUI execution and website
  publication were not performed.
- 2026-09-13, white macOS icon source update (no application rebuild):
  added `variants/macos/assets/LohnMail-white.png` and `LohnMail.icns`, with
  a repeatable `variants/macos/build-icon.sh` conversion. `BUILD-MACOS.sh`
  now pins the new assets, and frozen apps no longer replace their bundle icon
  with the transparent UI logo at startup. The canonical transparent PNG and
  Windows artwork are unchanged. ICNS extraction was visually inspected;
  structural tests confirm all 10 icon representations including 1024×1024.
  Targeted tests: `29 passed, 6 warnings`; full suite:
  `142 passed, 1 skipped, 6 warnings`. Shell/JavaScript syntax, Python import,
  and diff checks passed. ICNS SHA-256:
  `0dda034b1d99ade7e2cb24daad219e1b4ab69c01f05f8da62518556934d57198`.
  Existing signed/notarized DMG and installed application were not modified;
  final Finder/Dock rendering, new signing and notarization remain unverified.
- 2026-09-13, website artifact verification after the user completed signing:
  `dist/website/LohnMail-2.0.3-202609043-macOS-arm64.dmg` exists (43 MiB).
  Stapler ticket validation, DMG checksum validation, strict deep application
  signature verification, and Gatekeeper checks on both the DMG and its
  read-only mounted application passed (`Notarized Developer ID`, team
  `VUF387578P`). The approved ICNS hash matches, the settings template is empty
  of customer data, and no runtime/customer filenames were found in the app.
  SHA-256: `e1f8d06b75845d121c445d42e8c7cae1f87218af2bc0e94fd8d4cc7d8f9966ed`.
  ARM64 only; plist minimum macOS 13.0. GUI launch, clean-Mac installation,
  actual SMTP/licensing, and website publication were not tested in this step.
- 2026-09-13, macOS website distribution preparation: added a dedicated
  `variants/macos/build-website.sh` entry point and `BUILD-MACOS-WEBSITE.sh`.
  The pipeline builds from canonical source, removes App Store provisioning,
  applies Developer ID hardened-runtime signing, creates a DMG, and optionally
  submits/staples notarization through a named `notarytool` Keychain profile.
  Shell syntax, diff checks, JavaScript syntax, and the full suite passed
  (`137 passed, 1 skipped, 6 warnings`). The installed Developer ID Application
  identity was found, but the final signed/notarized artifact is pending because
  macOS requires the user to authorize private-key access and no
  `LohnMail-Notary` Keychain profile exists yet.
- 2026-09-13, separate Windows Store worktree/branch: captured 17 genuine Windows native-window PNGs (1786x993) with synthetic data using GitHub Actions run `34757644417`, commit `75dd207a973133e8bb62658f4ebdfcfda38f897d`. Windows suite: `143 passed, 1 warning`; local source suite: `142 passed, 1 skipped, 6 warnings`; Python/JavaScript syntax and diff checks passed. Only `.github/workflows/windows-store-screenshots.yml` and `tools/windows_store_screenshots.py` changed in that branch; canonical application source remains identical to Store commit `1a9af00`. Screenshots are under `lohnmail-pywebview-test/dist/store-listing-de-DE/screenshots-windows/`. All 17 were visually inspected; they show native Windows controls, no compositing/upscaling. Existing Help support-button layout issues and the General settings technical enum remain visible; these are not fixed or concealed. Capture runs source with pywebview EdgeChromium, not an installed MSIX; no new build, production update, real email/license transaction, or Store submission occurred. Earlier macOS screenshots must not be reused for the Windows listing.

- Fixed processing activity-log layout: long titles/details now wrap within constrained grid columns, and each row grows vertically instead of overlapping neighboring rows. Source checks passed (`137 passed, 1 skipped, 6 warnings`; JavaScript and diff checks passed). A new signed package is pending because the current environment rejected the Keychain signing step after the build-number increment to `202609043`.
- Built and signed macOS App Store package `2.0.3 (202609042)` with the latest shared-source changes. The payload includes App Sandbox client/server network entitlements, the bundled CA certificate used by licensing and SMTP TLS, and the approved icon (`LohnMail.icns` SHA-256 `ed33ebdf46e8a728626f6e01683445fc01f4fd721311705725941399fc596f02`). The expanded package passed deep strict code-signature verification with Keychain access; the installer signature chain passed; no quarantine attribute or customer/runtime data was found. Full suite: `137 passed, 1 skipped, 6 warnings`; JavaScript, shell syntax, and diff checks passed. Package SHA-256: `a11a039854a651e049de530cdc385f0db89ea1dd1b4f4d0563e352ec69c98843`.
- Added a three-entry variant layout without duplicating product source:
  `variants/etalon/run.py` runs the canonical Python implementation,
  `variants/macos/` owns local/App Store build entry points, and
  `variants/windows/` owns the Windows build entry point. Shared changes remain
  in the canonical source. Python compilation, macOS shell syntax, JavaScript,
  and diff checks passed; full suite: `137 passed, 1 skipped, 6 warnings`.
- Corrected update capability detection: the integrated updater is disabled only in a frozen macOS application, while Windows builds and source/Python runs retain it. The web UI now follows backend capabilities instead of `navigator.platform`, so SMTP-only macOS source runs no longer lose the Updates tab. Verification: `137 passed, 1 skipped, 6 warnings`; updater/UI target set `56 passed, 6 warnings`; JavaScript syntax and diff checks passed.
- Diagnosed the TestFlight build `202609036` startup hang from the macOS stackshot: pywebview's random-port probe bound to the hostname `localhost`, which entered DNS/mDNS resolution on the sandboxed main thread. The app now reserves a port using numeric `127.0.0.1` and passes it to pywebview. Added a regression test, rebuilt as `202609038`, and verified `135 passed, 1 skipped, 6 warnings`. The signed package contains only the bundle ICNS plus the approved UI PNG/SVG; SHA-256: `6b58105ba1490be50095ada9813fdc3b1cf791a9af4e6f4ea8163ac8874e6bab`.
- Rebuilt the signed macOS App Store package as build `202609036` after the user identified `web/assets/brand/lohnmail-app-icon-previous.png` as the approved icon. The packaged `LohnMail.icns` contains 10 layers including 1024x1024, matches the approved source configuration, and the build now stops if the approved PNG or ICNS hashes change unexpectedly.
- Verified build `202609036` on macOS: `134 passed, 1 skipped, 6 warnings`; JavaScript and both macOS shell scripts passed syntax checks; the distribution app and installer signatures passed with Keychain access; the expanded payload had no quarantine attribute or customer/runtime files. Package SHA-256: `e23a4d23bc843983233c3ccbe2a39aef1f5c619a715caeeaa941132664fe641c`.
- Re-verified the macOS preview before App Store preparation: `133 passed, 1 skipped, 6 warnings`.
- Passed `node --check web/app.js` and import smoke checks for the changed Python modules.
- Confirmed the macOS artifacts contain no settings, licenses, machine IDs, secrets, SQLite databases, PDF, or Excel customer/runtime files.
- Confirmed App ID `VUF387578P.lohnmail` and changed the macOS build Bundle ID from the temporary `de.lohnmail.app.macos-test` to `lohnmail`; `zsh -n BUILD-MACOS.sh` and `git diff --check` passed afterward.
- Verified the App Store provisioning profile `lohnmail.macos` for `VUF387578P.lohnmail`, restored its matching application identity, and confirmed the Mac Installer Distribution identity.
- Added App Sandbox entitlements and an App Store build/sign/package script.
- Built and signed `dist/LohnMail.app`, embedded the provisioning profile, and created the signed 40 MB ARM64 package `dist/LohnMail-2.0.3-macOS-AppStore.pkg`.
- `codesign --verify --deep --strict` passed; `pkgutil --check-signature` confirmed the Apple installer certificate chain. Artifact inspection found no settings, licenses, machine IDs, secrets, SQLite databases, PDFs, or Excel customer/runtime files.
- The App Store distribution-signed app was vetoed by Gatekeeper when launched directly (`errSecCSVetoed`); this is not a successful GUI smoke test. The previously ad-hoc-signed macOS preview remains the locally exercised artifact.
- Rebuilt that runnable preview separately as `dist/LohnMail-Local-Test.app`; its ad-hoc signature verified and macOS launched it successfully. The App Store `.pkg` was preserved.

- Inspected the active source tree, entry points, dependencies, tests, data layout, licensing, mail protection, and updater.
- Confirmed the current version/build and the distinction between the verified Windows release and the dirty working tree.
- Ran the current automated suite: `133 passed, 1 skipped, 6 warnings` on macOS with Python 3.14.
- Checked `web/app.js` with Node syntax validation.
- Checked the uncommitted `BUILD-MACOS.sh` with `zsh -n`.
- Parsed and validated the verification skill frontmatter and required fields with Ruby/Psych. The supplied Python `quick_validate.py` could not run because PyYAML is not installed in either available Python environment.

## Known bugs, risks, and debt

- The current working tree has uncommitted macOS-preview changes. Their ownership and intended final scope are not recorded in Git: **unconfirmed**.
- macOS preview data is currently isolated under `~/Library/Application Support/LohnMail-macOS-Test`; Outlook and the self-updater are disabled there. Production migration behavior is **unconfirmed**.
- The App Store package is ARM64 only; Intel/x86_64 support is **not included**. Build `202609042` has not yet been uploaded; server-side validation/processing, TestFlight installation, sandboxed license access, and real SMTP delivery are **not verified**.
- `TEST_UPDATES_ENABLED` is still true. A signed EXE/MSI-only production policy is therefore **not confirmed for the current working tree**.
- No first-party persistent application log was found for general runtime diagnostics; updater logging is separate.
- Root-level legacy UI/code and older architecture documents coexist with the active app and can mislead contributors.
- Numerous generated builds and screenshots are untracked at repository root, and build-output ignore coverage is incomplete. They must not enter commits or source archives.
- The dependency `PyPDF2` emits a deprecation warning and should eventually be replaced by `pypdf` after regression testing.
- A native Windows build, Windows GUI smoke test, macOS bundle smoke test, real SMTP/Outlook delivery, live Stripe flow, license-server deployment, and update deployment were not performed in this documentation task.

## Key decisions

- Active desktop source is `lohnmail-pywebview-test/` despite the historical directory name.
- User data stays separate from replaceable application files. Windows portable layout is `LohnMail.exe`, `App/`, `Settings/`, `Companies/`.
- SMTP credentials are OS-protected: DPAPI on Windows and Keychain on macOS.
- Real network side effects are never part of default automated verification.
- Windows build truth comes from Windows x64 CI or a Windows machine, not from a macOS source check.
- Release notes must separate a verified published artifact from an uncommitted working tree.

## Next step

Resolve and commit or discard the existing macOS-preview working-tree changes as a dedicated task. Then run the verification skill and produce target-platform artifacts only from a clean, identified commit.

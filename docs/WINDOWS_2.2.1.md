# Windows Store 2.2.1 / 2026.11.25.1

Based on verified Windows Store 2.2.0 commit `5f8d067`, with the current
canonical working-source corrections of 2026-11-25. MSIX: 2.2.1.0, x64.

- DATEV social-insurance forms: reconnect displaced personnel headings and
  adjacent values; invalid or conflicting identities remain blocked.
- Folder processing retains clearly identified documents without an Excel
  recipient in the no-email paper bundle. Such documents are not emailed.
- New company IDs transliterate German umlauts and sharp s consistently in
  Python and JavaScript. Existing IDs and company display names stay unchanged.
- Previous prepared results must be checked/prepared again (recognition v3 and
  folder-paper-bundle-v1). Existing reports and delivered messages are preserved.

Changed application files: core/pdf_content.py, core/pdf_filename.py,
core/input_scan.py, core/orchestrator.py, ui_web/bridge.py, web/app.js and
ui_web/version.py. Synthetic regression tests accompany the fixes.
Approved Windows icons, package identity, storage recovery and DPAPI unchanged.
Canonical updater flag remains enabled; MSIX internal updater remains disabled.
No macOS packaging files changed and no customer data included.

Local verification: 110 targeted tests passed; complete Windows-source suite
451 passed, 5 skipped, 6 dependency warnings. JavaScript syntax, changed Python
imports, diff and secret/runtime-data scans passed. Shared fixes and tests match
canonical source. Mail delivery is mocked; documents are synthetic.

Windows CI, installed-package tests and final artifact audit pending.
No Microsoft Store submission or real delivery performed.

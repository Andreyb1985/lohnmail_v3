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

Windows verification completed:
https://github.com/Andreyb1985/lohnmail_v3/actions/runs/45627212047

- Source commit: 9238089f4a998dee0b37f21962c6d1a81d048ed2.
- Windows x64 suite: 450 passed, 6 skipped, 1 dependency warning.
- MSIX build and packaged activity-log browser layout passed.
- Installed test-signed MSIX copies passed install/upgrade, uninstall/reinstall
  with retained workspace and verified backup, and legacy storage scenarios:
  empty, ordinary, redirected, both and conflicting copies.
- Local PDF-rules browser test passed with the real Python bridge and synthetic
  documents, including folder/content modes, save, company isolation and restart
  at widths 760/1180/1586. External network/mail blocked.
- Artifact: LohnMail_2.2.1.0_x64.msix, 49,967,369 bytes.
- SHA-256: 79c1d3469ce916d82ac77089409acefbdfb72096aaf7a136a47c1916513d7946.
- Downloaded artifact verified: ZIP CRC, SHA-256, 1713 block hashes, 317 entries,
  39 matching web resources; no customer/runtime files.
- Icons: 62 transparent PNGs, 42 PRI mappings, 9 embedded ICO sizes and
  transparent Store listing icon match approved artwork.

Not verified: interactive Windows 10 Shell appearance, real SMTP/Outlook,
production license/payment services or delivery through Microsoft Store.
The upload MSIX is unsigned; only separate disposable CI test copies were
temporarily signed. No Store submission performed.

Next: upload the MSIX to Partner Center. After updating, check and prepare
documents again; obsolete prepared results are invalidated intentionally.

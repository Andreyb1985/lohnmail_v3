# Windows Store 2.2.0 / 2026.11.23.1

Integrates shared application changes from canonical checkpoint `d39e5ef`
onto Windows Store baseline `1a858d3`. MSIX version: `2.2.0.0`, x64.

- Company-specific PDF filename/content matching and Excel preview.
- Conservative personnel recognition, birth-date consistency and protected PDF validation.
- Actionable per-employee shipping errors, partial-result reporting and diagnostics UI.
- Shared version metadata. Windows Store retains its disabled internal updater.
- Approved transparent Windows icons, package identity, DPAPI, storage recovery
  and Documents workspace remain unchanged. No macOS packaging files changed.

Local verification: 409 passed, 5 skipped, 6 dependency warnings. JavaScript
syntax and diff checks passed. Browser regressions passed for PDF rules using
a real Python bridge with synthetic documents; shipping failures/partial results;
diagnostics; version metadata. Tests blocked external network and real mail.
No tracked runtime/customer data or live-secret markers found.

Windows verification completed in CI run 45216055097:
https://github.com/Andreyb1985/lohnmail_v3/actions/runs/45216055097

- Source commit: 42e51e93fe2da4a07ff78f85b862f85e92c5b8f4.
- Windows x64 suite: 408 passed, 6 skipped, 1 dependency warning.
- Build, packaged activity-log browser layout and installed MSIX tests passed.
- Test-signed CI copies: clean install, upgrade, uninstall/reinstall with retained
  workspace and verified backup, legacy empty/ordinary/redirected/both/conflict.
  These are synthetic install/upgrade fixtures, not a published Store rollout.
- Local artifact audit: ZIP CRC, SHA-256, 1713 block hashes, 317 entries,
  39 web resources matching source; no customer/runtime documents or secrets.
- 62 transparent PNGs, 42 PRI target mappings, 9 embedded ICO sizes and separate
  transparent Store listing icon verified against approved artwork.
- File: LohnMail_2.2.0.0_x64.msix, 49,946,187 bytes.
- SHA-256: 6b97491aa8cce63704d642461fb8607528a288d37dda7e30af2bb6d5ed25878b.

The initial CI attempt failed because one diagnostics test read UTF-8 HTML using
the Windows system encoding. Explicit UTF-8 fixed the test in both canonical
source and the Windows branch. Canonical full suite after that test-only change:
449 passed, 3 skipped, 6 dependency warnings. Canonical TEST_UPDATES_ENABLED
remains True; Store has no internal updater.

Not verified: interactive Windows 10 Shell appearance, real mail/Outlook
delivery, production licensing/payment, actual Microsoft Store update delivery.
No Microsoft Store submission was performed. The upload MSIX is unsigned;
temporary CI test certificates are not included. Upload this MSIX to Partner
Center, and use store-listing/Lohn-mail-Store-300x300.png for the listing icon.

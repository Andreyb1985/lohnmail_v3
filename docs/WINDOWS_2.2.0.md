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

Windows CI, installed MSIX upgrade and final artifact audit pending. This file
does not claim Windows 10 visual validation or Microsoft Store publication.

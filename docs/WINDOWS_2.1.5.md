# Windows 2.1.5 — build 2026.10.18.1

Integrated on user approval from canonical main `3f8acc5` into Store base
`532aad5`. This is a Windows release candidate, not a Store publication.

## Included

- Latest canonical shipping progress/event ordering, preflight and retry behavior.
- Optional, consent-controlled technical diagnostics; no automatic transmission
  without consent. Real mail and production services are not used in tests.
- Approved transparent ICO and PNG artwork pinned by SHA-256; all 62 MSIX images,
  42 PRI mappings and nine EXE icon layers verified at packaging time. Both MSIX
  background attributes are transparent. Separate transparent 300x300 listing PNG.
- Preserved Windows storage bootstrap/migration, Documents workspace, DPAPI,
  Outlook Classic, native package AppID and Store/direct updater separation.
- Preserved online privacy link and runtime version/distribution labels.

No macOS packaging files/assets, user data, licenses, or mail credentials changed.
Dynamic license-client version also fixed in canonical source (no policy change).

## Verification before CI

- Canonical full suite: 265 passed, 1 skipped, 6 dependency warnings.
- Integrated Windows checkout on macOS: 263 passed, 3 skipped, 6 warnings,
  including the final privacy/version UI regression test. Windows CI pending.
- JavaScript syntax, Python compilation, diff whitespace and tracked runtime-data /
  live-secret filename scans passed.
- Skips concern separate server repo tests and native Windows updater on macOS.

Windows 10 installed-package Shell appearance, existing shortcut caches, Store
listing rendering and actual Store upgrade remain manual checks. Transparent file
pixels alone are not proof of all Shell surfaces. No Store/server publication.

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
  including the final privacy/version UI regression test.
- JavaScript syntax, Python compilation, diff whitespace and tracked runtime-data /
  live-secret filename scans passed.
- Skips concern separate server repo tests and native Windows updater on macOS.

## Windows build and downloaded artifact

- Source commit: `84a0629c96270fe82c4f6389abf410a1b9c53b98`.
- [Windows CI 39163529543](https://github.com/Andreyb1985/lohnmail_v3/actions/runs/39163529543)
  completed successfully on Windows Server 2025 x64 / Python 3.12.
- Full Windows suite: **264 passed, 2 skipped, 1 dependency warning**. The two
  skipped tests require the separate ignored license-server repository.
- Frozen EXE self-test, MakePRI/MakeAppx pack/unpack, packaged icon verification
  and actual installed-package activation/storage probes passed.
- Signed disposable CI fixtures: installation/upgrade preserve Settings,
  Companies and History; legacy cases empty / ordinary / redirected / both /
  conflict passed. Fixtures are not the published 2.1.4 binary.
- Packaged activity-log browser checks passed for empty and populated rows.
  Local synthetic browser diagnostics passed at 1180/1440 widths: cancel,
  manual-send consent, compact errors, details, copy and Escape; no network.
- Downloaded `LohnMail_2.1.5.0_x64.msix`: 315 archive entries, 1709 block hashes
  and whole-file hashes checked; ZIP CRC and metadata SHA-256 match. Identity,
  version, Store marker and packaged web files match the approved source.
- SHA-256: `916a1e63ffdd80d39ca56fda80fbff4131f6b9cc81d1d220aae59d585e368e1a`.
- Re-ran icon verifier against downloaded MSIX: 62 transparent PNGs, 42 PRI
  target mappings, nine embedded ICO layers, listing PNG exact pixel match.
- No Settings, Companies, credentials, SQLite, PDF, Excel or customer payloads.
- Artifact directory: `LohnMail-Windows-Store-2.1.5.0/` (local, not tracked).

## Boundaries and handoff

The MSIX is the unsigned Partner Center upload artifact, not a signed sideload
installer. No new direct-channel EXE/update ZIP was built in this run. Windows
native updater automated tests passed, but a full direct-channel UI run was not
performed. No real SMTP/Outlook mail, diagnostics upload, license mutation or
Store submission was performed. Existing canonical working changes remain intact.

Windows 10 installed-package Shell appearance, existing shortcut caches, Store
listing rendering and actual Store upgrade remain manual checks. Transparent file
pixels alone are not proof of all Shell surfaces. No Store/server publication.
Replace Partner Center's custom listing icon separately with
`store-listing/Lohn-mail-Store-300x300.png`; installing the MSIX cannot change an
existing manually uploaded Store listing image. Test before public submission.

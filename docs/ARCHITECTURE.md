# LohnMail architecture

This document describes only behavior confirmed in the current source tree as reviewed on 2026-09-07.

## Repository boundaries

`lohnmail-pywebview-test/` is the active desktop application. Root-level `main.py`, `ui/`, `ui_web/`, and related files are older prototypes and are not the current desktop entry path. `lohnmail-original-site/` is a separate website. `license-server/` is a separate ignored Git repository and is not part of the desktop source archive.

Within the active application, `core/`, `ui_web/`, `web/`, `main.py`, and
`pywebview_app.py` are the single reference implementation. Platform entry
points live under `variants/`: `etalon/` runs that source directly with Python,
`macos/` owns macOS/App Store packaging, and `windows/` owns Windows packaging.
Platform folders do not duplicate the reference source.

## Runtime structure

`lohnmail-pywebview-test/main.py` first delegates updater command-line handling to `ui_web.update_runtime`, then starts `pywebview_app.run()`. `pywebview_app.py` creates a native pywebview window for `web/index.html`, installs platform identity/icon behavior, creates `WebBridge`, exposes `ApiAdapter` to JavaScript, and forwards backend signals into the page.

The UI is static HTML/CSS/vanilla JavaScript in `web/`. It calls Python methods through pywebview. `ui_web/bridge.py` is the application-facing bridge and coordinates background work, settings, companies, reports, licenses, update state, dialogs, and shell integration.

## Domain modules

- `core/config.py`: defaults, JSON settings, data-directory resolution, company folders, and SMTP-secret hydration/stripping.
- `core/secret_store.py`: Windows DPAPI-encrypted `secrets.dat`; macOS Keychain service `de.lohnmail.desktop.smtp`.
- `core/input_scan.py`: PDF discovery and personnel-number extraction.
- `core/excel_io.py`: employee/e-mail workbook loading and normalization.
- `core/email_validation.py`: address-format, duplicate, and optional DNS/MX validation.
- `core/orchestrator.py`: check/send orchestration, PDF validation/merge/protection, selection handling, reports, and delivery.
- `core/jobs.py`: high-level payroll and mass-message jobs, including attachment dispatch.
- `core/mailer.py`: SMTP and Outlook Classic adapters plus user-facing error conversion.
- `core/report.py`: XLSX audit and send reports.
- `core/license_manager.py`: local license state, hardware-derived device ID, server calls, grace periods, and action gating.
- `ui_web/report_history.py`: SQLite report/send history.
- `ui_web/workflow_store.py`: persisted workflow sessions.
- `ui_web/updater.py` and `ui_web/update_runtime.py`: update metadata, download verification, installation helper, validation, rollback, and relaunch.

## Data flow

1. The user selects PDF input and an employee Excel workbook in the web UI.
2. JavaScript invokes the Python bridge.
3. Input modules scan PDF documents and normalize Excel employee records.
4. Validation maps documents and e-mail addresses to personnel numbers and records warnings/errors.
5. A check run writes audit outputs without delivering mail.
6. A send run processes only the selected/allowed personnel numbers, prepares verified password-protected PDFs, then uses the selected mail adapter unless dry-run is active.
7. Generated reports and delivery metadata are persisted locally and surfaced back to the UI.

Mass messages load non-empty recipients, validate them again immediately before sending, reject invalid or duplicate addresses, optionally attach selected files, and send through the configured SMTP or Outlook adapter.

## Local storage

MSIX revision (source, 2026-09-25; installed Windows verification pending):
package identity is resolved natively. ApplicationDataManager provides LocalFolder
for settings/license/DPAPI; Windows Known Folders provides Documents/LohnMail as
the default Companies/History workspace. Virtualization remains enabled. The
workspace path persists in package-local layout metadata. Per-company output
overrides do not change this root. Legacy imports require an unpackaged verified
export; the 2.1.2 hotfix bundles a copy-only native helper and automatically
requests this export before settings/license initialization. The helper checks
native NO_PACKAGE identity and hashes both physical stores; originals stay
untouched and conflicts stop import. See MSIX_UPGRADE_2.1.2.md for verification
and remaining release gates; MSIX_STORAGE_FIX.md describes the earlier layout.
Uninstall may remove LocalFolder settings; external documents/history remain.
The layouts below continue to describe non-MSIX operation.

`LOHNMAIL_DATA_DIR` overrides the data root. In a portable Windows layout, a frozen executable inside `App/` uses its parent directory when sibling `Settings/` and `Companies/` exist. Otherwise Windows uses `%LOCALAPPDATA%/LohnMail` (or `%APPDATA%` fallback). The current uncommitted macOS preview uses `~/Library/Application Support/LohnMail-macOS-Test`. Other systems use `$XDG_CONFIG_HOME/LohnMail` or `~/.config/LohnMail`.

The data root contains:

- `Settings/settings.json`: non-secret configuration.
- `Settings/secrets.dat`: Windows DPAPI ciphertext; macOS stores passwords in Keychain instead.
- `Settings/license.json` and `Settings/machine_id`: cached license state and diagnostic device ID.
- `Settings/lohnmail_history.sqlite3`: report and send history using schema version 1 and WAL mode.
- `Companies/Lohn_<company>/`: company-specific generated outputs.

Exact workflow-session filenames and future migration policy are implementation details; consult the current bridge/store code before changing them.

## Licensing and Stripe boundary

The desktop defaults to `https://license-server-lm.vercel.app`. It starts/checks/activates/deactivates licenses through HTTP endpoints and opens checkout, invoice-subscription, or customer-portal sessions returned by the server. Stripe credentials and webhook processing are not present in the desktop code.

The device ID is a UUID derived from an OS/hardware seed: Windows `MachineGuid`, macOS `IOPlatformUUID`, Linux machine-id, or a platform/node/hostname/MAC fallback. Raw hardware seeds are not sent. When a cached license key is bound to a different current ID, the app returns `device_mismatch` and blocks licensed actions.

Online checks are normally scheduled every seven days. Subscription/internal rules use cached entitlement dates where available; otherwise subscription offline grace is seven days and lifetime/internal grace is thirty days after a successful check. A server-confirmed missing license receives one persistent fourteen-day transition period before becoming invalid.

The license server implementation, Stripe webhook behavior, production environment variables, and database schema are outside this repository boundary and are **not confirmed by this document**.

## Updates

The Windows updater reads the production manifest from `https://license-server-lm.vercel.app/api/updates/windows/latest` unless overridden. It compares version/build, requires HTTPS, verifies size and SHA-256, and in normal production mode accepts only signed EXE/MSI packages. ZIP installation is available only when test updates are enabled and the manifest explicitly identifies test mode.

For test ZIP updates, the helper runs outside the replaceable `App` directory, waits for the app to exit, checks SQLite read/write health without mutating its contents, stages the new app, backs up the old `App`, replaces only `App`, performs version/build/database checks, rolls back on failure, and relaunches. `Settings` and `Companies` are outside the replaced directory.

The current dirty macOS preview disables the in-app updater and presents App Store guidance. A production macOS update/distribution mechanism is **unconfirmed**.

## Build and release

Windows x64 CI uses Python 3.12 and runs `BUILD-WINDOWS.ps1`. The script installs build requirements, runs pytest, builds a stable root launcher with the .NET C# compiler, creates a PyInstaller onedir app, produces the clean portable layout, validates forbidden customer/runtime files, and creates an update ZIP plus JSON metadata.

The uncommitted macOS preview script uses PyInstaller to create `dist/LohnMail.app`, adjusts bundle version metadata, and applies only an ad-hoc signature. Notarization, distribution signing, entitlements, installer packaging, and App Store packaging are **not verified**.

## External side effects and trust boundaries

- Local reads/writes: selected PDFs/Excel files, settings, protected secrets, SQLite history, reports, and generated PDFs.
- Network: license/update server, optional DNS/MX checks, SMTP, and server-created Stripe URLs.
- Platform APIs: Windows DPAPI, Outlook COM, Windows Authenticode/PowerShell updater, macOS Keychain and application icon APIs.
- Browser opening: checkout/customer portal URLs returned by the server.

Tests must replace these boundaries with fakes/mocks unless a separately authorized integration test explicitly requires a real service.

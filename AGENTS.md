# LohnMail contributor guide

## Purpose and source of truth

LohnMail is a desktop application for checking payroll PDFs against employee Excel data, preparing password-protected documents, and sending them by SMTP or Outlook Classic. The active desktop source is `lohnmail-pywebview-test/`; current code and tests override older root-level design notes.

Do not treat generated folders, ZIP files, screenshots, `license-server/`, or the root-level legacy Qt/UI prototypes as the current desktop implementation. `license-server/` is a separate ignored repository.

## Stack and important paths

- Python desktop backend: `lohnmail-pywebview-test/core/`, `lohnmail-pywebview-test/ui_web/`
- pywebview entry points: `lohnmail-pywebview-test/main.py`, `lohnmail-pywebview-test/pywebview_app.py`
- HTML/CSS/vanilla JS UI: `lohnmail-pywebview-test/web/`
- Tests: `lohnmail-pywebview-test/tests/`
- Windows build/update packaging: `lohnmail-pywebview-test/BUILD-WINDOWS.ps1`
- Windows CI: `.github/workflows/build-windows.yml`
- Version/build: `lohnmail-pywebview-test/ui_web/version.py`
- Detailed state and boundaries: `docs/PROJECT_STATE.md`, `docs/ARCHITECTURE.md`

## Commands

Run from the repository root unless stated otherwise.

```bash
# Install a local development environment
python3 -m venv .venv
.venv/bin/python -m pip install -r lohnmail-pywebview-test/requirements.txt "pytest>=8"

# Start from source on macOS/Linux
cd lohnmail-pywebview-test
../.venv/bin/python main.py

# Run the complete automated suite
../.venv/bin/python -m pytest -q

# Check browser JavaScript syntax
node --check web/app.js
```

On Windows, source startup is available through `lohnmail-pywebview-test/INSTALL-AND-START-WINDOWS.cmd`. Build and test on Windows x64 with:

```powershell
cd lohnmail-pywebview-test
.\BUILD-WINDOWS.ps1
```

The uncommitted `BUILD-MACOS.sh` is currently a preview build path only. It produces an ad-hoc-signed app and is not proof of distribution signing, notarization, or App Store readiness.

## Configuration, data, and security

- Never commit or package `Settings/`, `Companies/`, real `.env` files, `settings.json`, `license.json`, `machine_id`, `secrets.dat`, SQLite/WAL/SHM files, reports, or customer documents. A reviewed placeholder-only `.env.example` is allowed.
- SMTP passwords must not be written to settings JSON. `core/secret_store.py` uses Windows DPAPI and macOS Keychain.
- Keep real e-mail delivery disabled during tests. Automated tests must mock SMTP, Outlook, DNS, browser opening, license calls, Stripe calls, and update downloads.
- The desktop client contains no Stripe secret. Stripe operations go through the license server.
- A Windows update replaces only `App`; `Settings` and `Companies` stay outside it. Preserve SHA-256/signature checks, SQLite checks, backup, rollback, and relaunch behavior.
- A license containing a key is machine-bound. Do not weaken the current hardware-ID mismatch block or offline-grace rules.

## Completion rules

After a significant change, follow `.agents/skills/verify-lohnmail/SKILL.md`. At minimum inspect the diff, run affected tests plus the full suite, perform syntax/import checks, and state exactly what was and was not verified. A build is verified only on its target operating system; a release is verified only after its published artifact and update path have been checked. Never claim real e-mail, Stripe payment, Windows build, code signing, notarization, or deployment without direct evidence.

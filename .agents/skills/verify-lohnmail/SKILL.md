---
name: verify-lohnmail
description: Verify the LohnMail desktop application after significant changes, before test builds or releases, and after PDF, mail, licensing, Stripe, data-layout, or updater changes. Use it to inspect the diff, run safe automated checks, prevent secrets or customer data from entering artifacts, and report exactly what is and is not verified.
---

# Verify LohnMail

Run this workflow from the repository root. Do not alter product behavior while verifying. Never send real mail, create real Stripe charges, mutate production licenses, or publish an update unless the user explicitly requests that separate action.

## 1. Establish scope

Read `AGENTS.md`, `docs/PROJECT_STATE.md`, and `docs/ARCHITECTURE.md`. Record the branch, commit, version, build, and dirty state:

```bash
git status --short
git diff --stat
git diff -- lohnmail-pywebview-test
sed -n '1,80p' lohnmail-pywebview-test/ui_web/version.py
```

Classify changed files: UI, PDF/Excel, mail, licensing/Stripe, storage/SQLite, updater/build, or documentation. Preserve unrelated user changes.

## 2. Check safety before execution

- Confirm tests use `dry_run` or mocks for SMTP, Outlook, DNS, browser opening, license HTTP calls, Stripe URLs, and update downloads.
- Search tracked file names for runtime/customer data:

```bash
git ls-files | rg '(^|/)(Settings|Companies)(/|$)|(^|/)(license\.json|machine_id|secrets\.dat|.*\.sqlite3(-wal|-shm)?|settings\.json)$'
```

- Search for likely live secrets without printing values; report only matching file names:

```bash
git grep -IlE 'sk_live_|rk_live_|whsec_|BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY|smtp[^[:space:]]*password[^[:space:]]*=' -- . ':!*.md'
```

Expected result is no customer/runtime files and no live-secret matches. Inspect any match before continuing. Do not paste secret contents into output.

For Stripe-related desktop changes, confirm that the client still delegates checkout, invoice, portal, and license state to the license server and contains no Stripe secret. For changes inside the separate `license-server` repository, use that repository's own instructions and test environment; do not infer server verification from desktop tests.

## 3. Run safe automated checks

From `lohnmail-pywebview-test/`:

```bash
../.venv/bin/python -m pytest -q
node --check web/app.js
```

If `.venv` is absent, create it from the repository root and install the documented dependencies before testing:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r lohnmail-pywebview-test/requirements.txt "pytest>=8"
```

Run targeted tests first when the affected subsystem is clear:

- PDF/Excel/selection: `tests/test_pdf_merge_integrity.py tests/test_pdf_password.py tests/test_send_selection_audit.py tests/test_email_validation.py`
- Mail/mass message: `tests/test_mailer_errors.py tests/test_mailer_sender.py tests/test_outlook_errors.py tests/test_mass_message_validation.py`
- License/Stripe-facing client: `tests/test_license_offline.py tests/test_pywebview_adapter.py`
- SQLite/session storage: `tests/test_report_history.py tests/test_workflow_sessions.py tests/test_data_layout.py`
- Updater/build/UI contract: `tests/test_updater.py tests/test_update_runtime.py tests/test_update_ui_contract.py tests/test_windows_updater_e2e.py tests/test_github_workflow.py`
- Responsive UI: `tests/test_web_responsive_contract.py tests/test_update_ui_contract.py`

Run an import smoke check for changed Python modules without starting the GUI. If a GUI smoke test is needed, start `../.venv/bin/python main.py`, inspect the affected screen, then close it normally. Record that an online license check may occur at startup; it is not proof of the license server or Stripe end-to-end flow.

## 4. Build only on the target platform

For Windows x64, run on Windows or GitHub Actions:

```powershell
cd lohnmail-pywebview-test
.\BUILD-WINDOWS.ps1
```

Confirm tests passed, `release/LohnMail/LohnMail.exe` exists, `release/LohnMail/App/LohnMail.exe` exists, `Settings/settings.json` is clean, `Companies/` is empty, and exactly one update ZIP and JSON manifest were produced. Inspect the archive entry names and ensure it contains `LohnMail/App/LohnMail.exe` but no `Settings`, `Companies`, licenses, machine IDs, secrets, SQLite files, reports, or customer documents.

If testing the current macOS preview and `BUILD-MACOS.sh` is present, first run `zsh -n BUILD-MACOS.sh`, then build only when requested. An ad-hoc signature is a local test result, not distribution signing, notarization, or App Store readiness.

## 5. Regression and end-to-end checks

Match manual checks to the changed area:

- PDF: single file/folder modes, multi-page merge integrity, unreadable/password-protected input, output password, duplicate personnel numbers.
- Mail: dry-run, invalid/duplicate/missing addresses, sender validation, attachments, SMTP failure mapping, Outlook availability.
- License: first trial, cached/offline state, deleted-license grace, expired grace, device mismatch, server unreachable versus license missing.
- Updater: no update, newer update, download progress, checksum/signature rejection, SQLite read/write check, app exit, replacement of only `App`, rollback, relaunch, preserved settings/companies.
- UI: supported minimum window size, narrow layout, long paths/text, disabled/loading states, error messages, keyboard focus, and platform-specific controls.

Never perform a real delivery, payment, production-license mutation, or production update publication as an incidental regression check.

## 6. Report and update state

Update `docs/PROJECT_STATE.md` after each completed verification stage. Use exact outcomes, for example `133 passed, 1 skipped, 6 warnings`; do not write “all tests passed” if anything was skipped or not run.

Final report headings:

- Result
- Changed files
- Verification
- Not verified
- Risks/limits
- Next step

Distinguish source verification, target-platform build verification, artifact inspection, deployment, and real end-to-end service verification. Never claim a build or release when it was not performed.

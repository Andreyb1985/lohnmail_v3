from __future__ import annotations

import json
import re
from copy import deepcopy
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, Slot, Signal, QThread, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFileDialog, QInputDialog, QWidget

from core.config import (
    GESOB_DIR,
    get_company_email_excel_file,
    get_company_name,
    load_settings,
    save_settings,
)
from core.license_manager import LicenseManager


class ProcessingWorker(QObject):
    progress = Signal(str)
    finished = Signal(dict)
    error = Signal(str)

    def __init__(
        self,
        mode: str,
        pdf_input: Path,
        excel_path: Path,
        settings: dict,
        dry_run: bool,
        selected_persnr: set[str] | None = None,
    ) -> None:
        super().__init__()
        self.mode = mode
        self.pdf_input = pdf_input
        self.excel_path = excel_path
        self.settings = settings
        self.dry_run = dry_run
        self.selected_persnr = selected_persnr

    @Slot()
    def run(self) -> None:
        try:
            from core.jobs import run_main_job

            result = run_main_job(
                mode=self.mode,
                pdf_input=self.pdf_input,
                excel_path=self.excel_path,
                settings=self.settings,
                dry_run=self.dry_run,
                selected_persnr=self.selected_persnr,
                progress_cb=self.progress.emit,
            )
            self.finished.emit(result)
        except Exception as exc:
            self.error.emit(self._friendly_error(exc))

    @staticmethod
    def _friendly_error(exc: Exception) -> str:
        message = str(exc)
        if "Directory 'static/' does not exist" in message:
            return (
                "PDF Engine ist falsch installiert: Python lädt das Paket 'fitz' statt 'PyMuPDF'. "
                "Bitte im aktiven venv 'fitz' entfernen und 'PyMuPDF' installieren."
            )
        return message


class MassMessageWorker(QObject):
    progress = Signal(str)
    finished = Signal(dict)
    error = Signal(str)

    def __init__(
        self,
        settings: dict,
        company_id: str,
        subject_template: str,
        body_template: str,
        recipients: list[dict],
    ) -> None:
        super().__init__()
        self.settings = settings
        self.company_id = company_id
        self.subject_template = subject_template
        self.body_template = body_template
        self.recipients = recipients

    @Slot()
    def run(self) -> None:
        try:
            from core.jobs import run_mass_message_job

            result = run_mass_message_job(
                settings=self.settings,
                company_id=self.company_id,
                subject_template=self.subject_template,
                body_template=self.body_template,
                recipients=self.recipients,
                progress_cb=self.progress.emit,
            )
            self.finished.emit(result)
        except Exception as exc:
            self.error.emit(ProcessingWorker._friendly_error(exc))


class WebBridge(QObject):
    """Bridge for the WebEngine UI.

    Keep this layer thin: it may persist UI input paths and invoke existing
    core jobs, but business rules stay in core modules.
    """

    pageChanged = Signal(str)
    processingStateChanged = Signal(str)
    processingProgress = Signal(str)
    processingFinished = Signal(str)
    processingError = Signal(str)
    shippingStateChanged = Signal(str)
    shippingProgress = Signal(str)
    shippingFinished = Signal(str)
    shippingError = Signal(str)
    massMessageStateChanged = Signal(str)
    massMessageProgress = Signal(str)
    massMessageFinished = Signal(str)
    massMessageError = Signal(str)

    REPORT_FILES = {
        "audit": "audit_check.xlsx",
        "missing": "ohne_email_gesamt.pdf",
        "send": "send_report.xlsx",
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._dialog_parent = parent
        self.worker_thread: QThread | None = None
        self.worker: ProcessingWorker | MassMessageWorker | None = None
        self._processing_running = False
        self._processing_status = self._idle_processing_status()
        self._validation_state = self._empty_validation_state()
        self._shipping_running = False
        self._shipping_status = self._idle_shipping_status()
        self._shipping_rows: list[dict] = []
        self._shipping_source_rows: list[dict] = []
        self._mass_message_running = False
        self._mass_message_status = self._idle_mass_message_status()
        self._mass_message_preview = self._empty_mass_message_preview()
        self._license_manager = LicenseManager(load_settings())

    @Slot(str)
    def navigate(self, page: str) -> None:
        self.pageChanged.emit(page)

    @Slot(result=str)
    def appVersion(self) -> str:
        return "v2.0.0-web-poc"

    @Slot(result=str)
    def getDashboardState(self) -> str:
        settings = load_settings()
        ui_settings = settings.get("ui", {})
        smtp_settings = settings.get("smtp", {})
        license_payload = self._license_payload(settings, refresh=True)
        license_status = str(license_payload.get("status", "") or "unregistered").strip().lower()
        license_active = bool(license_payload.get("active"))

        smtp_server = str(smtp_settings.get("server", "") or "").strip()
        smtp_from = str(smtp_settings.get("from_email", "") or smtp_settings.get("username", "") or "").strip()
        mail_configured = bool(smtp_server and smtp_from)

        reports = {
            "audit": self._report_state("audit_check.xlsx"),
            "missing": self._report_state("ohne_email_gesamt.pdf"),
            "send": self._report_state("send_report.xlsx"),
        }

        processing_status = self._processing_status
        payload = {
            "version": self.appVersion(),
            "company": get_company_name(settings),
            "license": license_payload,
            "mail": {
                "mode": str(settings.get("mail_mode", "smtp") or "smtp"),
                "configured": mail_configured,
                "label": "Konfiguriert" if mail_configured else "Nicht konfiguriert",
            },
            "paths": {
                "last_pdf_dir": str(ui_settings.get("last_pdf_dir", "") or ""),
                "last_excel_file": str(ui_settings.get("last_excel_file", "") or ""),
                "output_dir": str(GESOB_DIR),
            },
            "metrics": {
                "employees": int(processing_status.get("employees_total", 0) or 0),
                "sent": 0,
                "missing_email": int(processing_status.get("missing_email", 0) or 0),
                "errors": int(processing_status.get("errors", 0) or 0),
            },
            "system": {
                "ready": True,
                "processing": "Läuft" if processing_status.get("running") else "Bereit",
                "pdf": "Bereit",
                "excel": "Bereit",
                "mail": "Bereit" if mail_configured else "Offen",
                "license": "Bereit" if license_active else "Offen",
                "filesystem": "Bereit" if GESOB_DIR.exists() else "Offen",
            },
            "reports": reports,
        }
        return json.dumps(payload, ensure_ascii=False)

    @Slot(result=str)
    def getProcessingState(self) -> str:
        settings = load_settings()
        return json.dumps(self._processing_payload(settings), ensure_ascii=False)

    @Slot(result=str)
    def getValidationState(self) -> str:
        return json.dumps(self._validation_state, ensure_ascii=False)

    @Slot(result=str)
    def getShippingState(self) -> str:
        return json.dumps(self._shipping_payload(load_settings()), ensure_ascii=False)

    @Slot(result=str)
    def getMassMessageState(self) -> str:
        return json.dumps(self._mass_message_payload(self._settings_with_company_mail(load_settings())), ensure_ascii=False)

    @Slot(result=str)
    def getCompanyState(self) -> str:
        return json.dumps(self._company_payload(load_settings()), ensure_ascii=False)

    @Slot(result=str)
    def getLicenseState(self) -> str:
        return json.dumps(self._license_payload(load_settings(), refresh=True), ensure_ascii=False)

    @Slot(result=str)
    def checkLicense(self) -> str:
        manager = LicenseManager(load_settings())
        state = manager.refresh(force=True, start_trial=True)
        return json.dumps(self._license_payload(load_settings(), state=state), ensure_ascii=False)

    @Slot(result=str)
    def buyLicense(self) -> str:
        settings = load_settings()
        manager = LicenseManager(settings)
        try:
            response = manager.purchase_session(company_name=get_company_name(settings))
            if response.get("already_active"):
                state = manager.load_state()
                return json.dumps(
                    {
                        "ok": True,
                        "message": response.get("message", "Für diese Installation ist bereits eine aktive Lizenz vorhanden."),
                        "state": self._license_payload(settings, state=state),
                    },
                    ensure_ascii=False,
                )
            url = str(response.get("url") or "")
            if not url:
                raise ValueError("Stripe Checkout URL konnte nicht erstellt werden.")
            QDesktopServices.openUrl(QUrl(url))
            state = manager.load_state()
            return json.dumps(
                {"ok": True, "message": "Stripe Checkout wurde geöffnet.", "state": self._license_payload(settings, state=state)},
                ensure_ascii=False,
            )
        except Exception as exc:
            return json.dumps({"ok": False, "message": str(exc), "state": self._license_payload(settings)}, ensure_ascii=False)

    @Slot(result=str)
    def openCustomerPortal(self) -> str:
        settings = load_settings()
        manager = LicenseManager(settings)
        try:
            url = manager.portal_url()
            if not url:
                raise ValueError("Kundenportal URL konnte nicht erstellt werden.")
            QDesktopServices.openUrl(QUrl(url))
            return json.dumps({"ok": True, "message": "Stripe Kundenportal wurde geöffnet.", "state": self._license_payload(settings)}, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"ok": False, "message": str(exc), "state": self._license_payload(settings)}, ensure_ascii=False)

    @Slot(str, result=str)
    def activateLicenseKey(self, license_key: str) -> str:
        settings = load_settings()
        manager = LicenseManager(settings)
        try:
            state = manager.activate(str(license_key or "").strip())
            settings.setdefault("license", {})["key"] = str(state.get("license_key", "") or "")
            settings["license"]["status"] = str(state.get("status", "") or "")
            save_settings(settings)
            return json.dumps({"ok": True, "message": state.get("last_message", "Lizenz wurde aktiviert."), "state": self._license_payload(load_settings(), state=state)}, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"ok": False, "message": str(exc), "state": self._license_payload(settings)}, ensure_ascii=False)

    @Slot(result=str)
    def promptActivateLicenseKey(self) -> str:
        self._activate_dialog_parent()
        license_key, accepted = QInputDialog.getText(self._dialog_parent, "Lizenzschlüssel eingeben", "Lizenzschlüssel:")
        if not accepted:
            return json.dumps({"ok": False, "message": "Aktivierung abgebrochen.", "state": self._license_payload(load_settings())}, ensure_ascii=False)
        return self.activateLicenseKey(license_key)

    @Slot(result=str)
    def deactivateLicense(self) -> str:
        settings = load_settings()
        manager = LicenseManager(settings)
        try:
            state = manager.deactivate()
            settings.setdefault("license", {})["key"] = ""
            settings["license"]["status"] = str(state.get("status", "") or "unregistered")
            save_settings(settings)
            return json.dumps({"ok": True, "message": state.get("last_message", "Lizenz wurde deaktiviert."), "state": self._license_payload(load_settings(), state=state)}, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"ok": False, "message": str(exc), "state": self._license_payload(settings)}, ensure_ascii=False)

    @Slot(result=str)
    def getSettingsState(self) -> str:
        return json.dumps(self._settings_payload(load_settings()), ensure_ascii=False)

    @Slot(str, result=str)
    def saveCompanyState(self, payload: str) -> str:
        try:
            data = json.loads(payload or "{}")
            if not isinstance(data, dict):
                raise ValueError("Ungültige Mandantendaten.")

            settings = load_settings()
            selected_company_id = str(settings.get("selected_company_id", "") or "").strip()
            company = self._selected_company(settings)
            if not selected_company_id or company is None:
                raise ValueError("Bitte zuerst ein Unternehmen auswählen.")

            name = str(data.get("name", "") or "").strip()
            if not name:
                raise ValueError("Bitte Unternehmensname eingeben.")
            company["name"] = name

            mail_scope = str(data.get("mail_scope", "global") or "global").strip().lower()
            if mail_scope not in {"global", "custom"}:
                mail_scope = "global"
            mail_settings = company.setdefault("mail_settings", {})
            mail_settings["scope"] = mail_scope

            smtp_data = data.get("smtp") if isinstance(data.get("smtp"), dict) else {}
            smtp = mail_settings.setdefault("smtp", {})
            for key in ["server", "security", "username", "from_email", "from_name"]:
                if key in smtp_data:
                    smtp[key] = str(smtp_data.get(key) or "").strip()
            if "port" in smtp_data:
                smtp["port"] = max(1, min(65535, int(smtp_data.get("port") or 587)))
            if "timeout_sec" in smtp_data:
                smtp["timeout_sec"] = max(5, min(300, int(smtp_data.get("timeout_sec") or 30)))
            if "password" in smtp_data and str(smtp_data.get("password") or ""):
                smtp["password"] = str(smtp_data.get("password") or "")

            save_settings(settings)
            settings = load_settings()
            self.processingStateChanged.emit(json.dumps(self._processing_payload(settings), ensure_ascii=False))
            self.shippingStateChanged.emit(json.dumps(self._shipping_payload(settings), ensure_ascii=False))
            self.massMessageStateChanged.emit(json.dumps(self._mass_message_payload(self._settings_with_company_mail(settings)), ensure_ascii=False))
            return json.dumps(
                {
                    "ok": True,
                    "message": "Mandant wurde gespeichert.",
                    "state": self._company_payload(settings),
                },
                ensure_ascii=False,
            )
        except Exception as exc:
            return json.dumps(
                {
                    "ok": False,
                    "message": f"Mandant konnte nicht gespeichert werden: {exc}",
                    "state": self._company_payload(load_settings()),
                },
                ensure_ascii=False,
            )

    @Slot(result=str)
    def getOutlookAccounts(self) -> str:
        try:
            from core.mailer import list_outlook_accounts

            return json.dumps({"ok": True, "accounts": list_outlook_accounts()}, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"ok": False, "message": str(exc), "accounts": []}, ensure_ascii=False)

    @Slot(result=str)
    def testMailConnection(self) -> str:
        try:
            settings = load_settings()
            mail_mode = str(settings.get("mail_mode", "smtp") or "smtp").strip().lower()
            smtp_settings = settings.get("smtp", {})
            if mail_mode == "outlook":
                from core.mailer import test_outlook_connection

                test_outlook_connection(str(smtp_settings.get("from_email", "") or "").strip())
                return json.dumps({"ok": True, "message": "Outlook-Verbindung ist bereit."}, ensure_ascii=False)

            from core.mailer import test_smtp_connection

            test_smtp_connection(smtp_settings)
            return json.dumps({"ok": True, "message": "SMTP-Verbindung ist bereit."}, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"ok": False, "message": str(exc)}, ensure_ascii=False)

    @Slot(result=str)
    def testCompanyMailConnection(self) -> str:
        try:
            settings = self._settings_with_company_mail(load_settings())
            mail_mode = str(settings.get("mail_mode", "smtp") or "smtp").strip().lower()
            smtp_settings = settings.get("smtp", {})
            if mail_mode == "outlook":
                from core.mailer import test_outlook_connection

                test_outlook_connection(str(smtp_settings.get("from_email", "") or "").strip())
                return json.dumps({"ok": True, "message": "Mandant-Outlook-Verbindung ist bereit."}, ensure_ascii=False)

            from core.mailer import test_smtp_connection

            test_smtp_connection(smtp_settings)
            return json.dumps({"ok": True, "message": "Mandant-SMTP-Verbindung ist bereit."}, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"ok": False, "message": str(exc)}, ensure_ascii=False)

    @Slot(str, str, result=str)
    def previewMassMessage(self, subject: str, body: str) -> str:
        settings = self._settings_with_company_mail(load_settings())
        try:
            preview = self._build_mass_message_preview(settings, subject, body)
            self._mass_message_preview = preview
            self._mass_message_status = {
                **self._idle_mass_message_status(),
                "preview_ready": True,
                "message": f"{preview['total_count']} Empfänger geladen. Vorschau ist bereit.",
            }
        except Exception as exc:
            self._mass_message_preview = self._empty_mass_message_preview()
            self._mass_message_status = {
                **self._idle_mass_message_status(),
                "failed": True,
                "message": f"Vorschau fehlgeschlagen: {exc}",
            }
        serialized = json.dumps(self._mass_message_payload(settings), ensure_ascii=False)
        self.massMessageStateChanged.emit(serialized)
        return serialized

    @Slot(str, str, result=str)
    def startMassMessage(self, subject: str, body: str) -> str:
        if self._processing_running or self._shipping_running or self._mass_message_running:
            return self._emit_mass_message_payload(self._settings_with_company_mail(load_settings()))

        settings = self._settings_with_company_mail(load_settings())
        allowed, license_state = LicenseManager(settings).require_action("shipping")
        if not allowed:
            self._mass_message_status = {
                **self._idle_mass_message_status(),
                "failed": True,
                "message": license_state.get("last_message", "Bitte aktivieren Sie eine gültige Lizenz."),
            }
            return self._emit_mass_message_payload(settings)

        try:
            preview = self._build_mass_message_preview(settings, subject, body)
        except Exception as exc:
            self._mass_message_status = {
                **self._idle_mass_message_status(),
                "failed": True,
                "message": f"Nachricht kann nicht gestartet werden: {exc}",
            }
            return self._emit_mass_message_payload(settings)

        self._mass_message_preview = preview
        self._mass_message_running = True
        self._mass_message_status = {
            **self._idle_mass_message_status(),
            "running": True,
            "preview_ready": True,
            "current_step": "Nachricht wird gesendet",
            "progress": 8,
            "total_count": int(preview.get("total_count", 0) or 0),
            "message": "Nachricht-Versand wurde gestartet.",
        }
        self._emit_mass_message_payload(settings)

        request_settings = deepcopy(settings)
        request_settings["selected_company_id"] = preview["company_id"]

        self.worker_thread = QThread(self)
        self.worker = MassMessageWorker(
            settings=request_settings,
            company_id=preview["company_id"],
            subject_template=subject,
            body_template=body,
            recipients=preview["recipients"],
        )
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.run)
        self.worker.progress.connect(self._on_mass_message_progress)
        self.worker.finished.connect(self._on_mass_message_finished)
        self.worker.error.connect(self._on_mass_message_error)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.error.connect(self.worker_thread.quit)
        self.worker_thread.finished.connect(self._cleanup_worker)
        self.worker_thread.start()

        return json.dumps(self._mass_message_payload(settings), ensure_ascii=False)

    @Slot(str, result=str)
    def saveSettingsState(self, payload: str) -> str:
        try:
            data = json.loads(payload or "{}")
            if not isinstance(data, dict):
                raise ValueError("Ungültige Einstellungen.")
            settings = load_settings()
            smtp = settings.setdefault("smtp", {})
            mail_text = settings.setdefault("mail_text", {})
            pdf_password = settings.setdefault("pdf_password", {})
            period = settings.setdefault("period", {})
            ui_settings = settings.setdefault("ui", {})
            notifications = settings.setdefault("notifications", {})

            if "mail_mode" in data:
                settings["mail_mode"] = str(data.get("mail_mode") or "smtp").strip() or "smtp"

            smtp_data = data.get("smtp") if isinstance(data.get("smtp"), dict) else {}
            for key in ["server", "security", "username", "from_email", "from_name"]:
                if key in smtp_data:
                    smtp[key] = str(smtp_data.get(key) or "").strip()
            if "port" in smtp_data:
                smtp["port"] = max(1, min(65535, int(smtp_data.get("port") or 587)))
            if "timeout_sec" in smtp_data:
                smtp["timeout_sec"] = max(5, min(300, int(smtp_data.get("timeout_sec") or 30)))
            if "password" in smtp_data and str(smtp_data.get("password") or ""):
                smtp["password"] = str(smtp_data.get("password") or "")

            text_data = data.get("mail_text") if isinstance(data.get("mail_text"), dict) else {}
            for key in ["subject", "body", "body_html"]:
                if key in text_data:
                    mail_text[key] = str(text_data.get(key) or "")

            password_data = data.get("pdf_password") if isinstance(data.get("pdf_password"), dict) else {}
            if "enabled" in password_data:
                pdf_password["enabled"] = bool(password_data.get("enabled"))
            for key in ["prefix", "suffix"]:
                if key in password_data:
                    pdf_password[key] = str(password_data.get(key) or "")

            period_data = data.get("period") if isinstance(data.get("period"), dict) else {}
            if "mode" in period_data:
                period["mode"] = str(period_data.get("mode") or "automatic_current_month")
            if "month" in period_data:
                period["month"] = max(1, min(12, int(period_data.get("month") or 1)))
            if "year" in period_data:
                period["year"] = max(2020, min(2100, int(period_data.get("year") or datetime.now().year)))

            ui_data = data.get("ui") if isinstance(data.get("ui"), dict) else {}
            for key in ["dry_run_default", "remember_last_paths"]:
                if key in ui_data:
                    ui_settings[key] = bool(ui_data.get(key))

            notification_data = data.get("notifications") if isinstance(data.get("notifications"), dict) else {}
            for key in [
                "show_badge",
                "workflow_warnings",
                "validation_warnings",
                "processing_errors",
                "delivery_events",
                "auto_open_on_start",
            ]:
                if key in notification_data:
                    notifications[key] = bool(notification_data.get(key))

            save_settings(settings)
            settings = load_settings()
            self.processingStateChanged.emit(json.dumps(self._processing_payload(settings), ensure_ascii=False))
            self.shippingStateChanged.emit(json.dumps(self._shipping_payload(settings), ensure_ascii=False))
            return json.dumps({"ok": True, "message": "Einstellungen wurden gespeichert.", "state": self._settings_payload(settings)}, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"ok": False, "message": f"Einstellungen konnten nicht gespeichert werden: {exc}"}, ensure_ascii=False)

    @Slot(str, result=str)
    def selectCompany(self, company_id: str) -> str:
        settings = load_settings()
        requested_id = str(company_id or "").strip()
        known_ids = {
            str(company.get("id", "") or "").strip()
            for company in settings.get("companies", [])
            if isinstance(company, dict)
        }
        if requested_id in known_ids:
            settings["selected_company_id"] = requested_id
            save_settings(settings)
            settings = load_settings()
            self.processingStateChanged.emit(json.dumps(self._processing_payload(settings), ensure_ascii=False))
            self.shippingStateChanged.emit(json.dumps(self._shipping_payload(settings), ensure_ascii=False))
        return json.dumps(self._company_payload(settings), ensure_ascii=False)

    @Slot(str, result=str)
    def createCompany(self, payload: str) -> str:
        try:
            data = json.loads(payload or "{}")
            if not isinstance(data, dict):
                raise ValueError("Ungültige Mandantendaten.")

            name = str(data.get("name", "") or "").strip()
            requested_id = str(data.get("id", "") or "").strip()
            choose_excel = bool(data.get("choose_excel"))
            if not name:
                raise ValueError("Bitte Unternehmensname eingeben.")

            settings = load_settings()
            companies = settings.setdefault("companies", [])
            if not isinstance(companies, list):
                companies = []
                settings["companies"] = companies

            existing_ids = {
                str(company.get("id", "") or "").strip().lower()
                for company in companies
                if isinstance(company, dict)
            }
            company_id = self._normalize_company_id(requested_id or name)
            if not company_id:
                company_id = "mandant"
            base_id = company_id
            suffix = 2
            while company_id.lower() in existing_ids:
                company_id = f"{base_id}-{suffix}"
                suffix += 1

            companies.append({"id": company_id, "name": name, "email_excel_file": "", "mail_settings": {"scope": "global"}})
            settings["selected_company_id"] = company_id
            save_settings(settings)

            if choose_excel:
                self.chooseExcelInput()

            settings = load_settings()
            self.processingStateChanged.emit(json.dumps(self._processing_payload(settings), ensure_ascii=False))
            self.shippingStateChanged.emit(json.dumps(self._shipping_payload(settings), ensure_ascii=False))
            return json.dumps(
                {
                    "ok": True,
                    "message": f"Mandant '{name}' wurde erstellt.",
                    "state": self._company_payload(settings),
                },
                ensure_ascii=False,
            )
        except Exception as exc:
            return json.dumps(
                {
                    "ok": False,
                    "message": f"Mandant konnte nicht erstellt werden: {exc}",
                    "state": self._company_payload(load_settings()),
                },
                ensure_ascii=False,
            )

    @Slot(result=str)
    def chooseCompanyExcelInput(self) -> str:
        self.chooseExcelInput()
        return json.dumps(self._company_payload(load_settings()), ensure_ascii=False)

    @Slot(result=str)
    def openCompanyExcel(self) -> str:
        settings = load_settings()
        path = Path(str(get_company_email_excel_file(settings) or "")).expanduser()
        if not path.is_file():
            return json.dumps({"ok": False, "message": "Excel-Datei wurde noch nicht ausgewählt.", "path": ""}, ensure_ascii=False)
        opened = QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
        return json.dumps(
            {
                "ok": bool(opened),
                "message": "Excel-Datei geöffnet." if opened else "Excel-Datei konnte nicht geöffnet werden.",
                "path": str(path),
            },
            ensure_ascii=False,
        )

    @Slot(result=str)
    def openOutputFolder(self) -> str:
        if not GESOB_DIR.exists():
            return json.dumps({"ok": False, "message": "Ausgabeordner existiert nicht.", "path": str(GESOB_DIR)}, ensure_ascii=False)
        opened = QDesktopServices.openUrl(QUrl.fromLocalFile(str(GESOB_DIR)))
        return json.dumps(
            {
                "ok": bool(opened),
                "message": "Ausgabeordner geöffnet." if opened else "Ausgabeordner konnte nicht geöffnet werden.",
                "path": str(GESOB_DIR),
            },
            ensure_ascii=False,
        )

    @Slot(str, str, result=str)
    def exportValidationCsv(self, csv_text: str, filename: str) -> str:
        allowed, state = LicenseManager(load_settings()).require_action("export")
        if not allowed:
            return json.dumps({"ok": False, "message": state.get("last_message", "Lizenz erforderlich."), "path": ""}, ensure_ascii=False)

        safe_name = "".join(ch for ch in filename if ch.isalnum() or ch in {"-", "_", "."}).strip()
        if not safe_name.lower().endswith(".csv"):
            safe_name = f"{safe_name or 'lohnmail_pruefung'}.csv"

        export_dir = GESOB_DIR / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        export_path = export_dir / safe_name
        export_path.write_text(csv_text, encoding="utf-8-sig")
        return json.dumps({"ok": True, "path": str(export_path)}, ensure_ascii=False)

    @Slot(str, result=str)
    def openReport(self, kind: str) -> str:
        filename = self.REPORT_FILES.get(str(kind or "").strip())
        if not filename:
            return json.dumps({"ok": False, "message": "Unbekannter Bericht.", "path": ""}, ensure_ascii=False)

        report = self._report_state(filename)
        path = Path(str(report.get("path", "") or ""))
        if not report.get("exists") or not path.is_file():
            return json.dumps({"ok": False, "message": "Bericht wurde noch nicht erstellt.", "path": ""}, ensure_ascii=False)

        opened = QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
        return json.dumps(
            {
                "ok": bool(opened),
                "message": "Bericht geöffnet." if opened else "Bericht konnte nicht geöffnet werden.",
                "path": str(path),
            },
            ensure_ascii=False,
        )

    @Slot(result=str)
    def choosePdfInput(self) -> str:
        settings = load_settings()
        ui_settings = settings.get("ui", {})
        pdf_input_mode = self._pdf_input_mode(settings)
        start_path = self._dialog_start_path(str(ui_settings.get("last_pdf_dir", "") or ""))
        self._activate_dialog_parent()
        if pdf_input_mode == "single_pdf":
            selected, _ = QFileDialog.getOpenFileName(
                self._dialog_parent,
                "Gesamt-PDF auswählen",
                start_path,
                "PDF-Dateien (*.pdf);;Alle Dateien (*)",
            )
        else:
            selected = QFileDialog.getExistingDirectory(
                self._dialog_parent,
                "PDF-Ordner auswählen",
                start_path,
            )

        if selected:
            settings.setdefault("ui", {})["last_pdf_dir"] = selected
            settings["ui"]["last_pdf_input_mode"] = pdf_input_mode
            save_settings(settings)
            self._processing_status = self._idle_processing_status()

        payload = self._processing_payload(load_settings())
        serialized = json.dumps(payload, ensure_ascii=False)
        self.processingStateChanged.emit(serialized)
        return serialized

    @Slot(str, result=str)
    def setPdfInputMode(self, mode: str) -> str:
        resolved_mode = mode if mode in {"folder", "single_pdf"} else "folder"
        settings = load_settings()
        settings.setdefault("ui", {})["last_pdf_input_mode"] = resolved_mode
        save_settings(settings)
        self._processing_status = self._idle_processing_status()
        payload = self._processing_payload(load_settings())
        serialized = json.dumps(payload, ensure_ascii=False)
        self.processingStateChanged.emit(serialized)
        return serialized

    @Slot(result=str)
    def chooseExcelInput(self) -> str:
        settings = load_settings()
        ui_settings = settings.get("ui", {})
        start_path = self._dialog_start_path(
            str(get_company_email_excel_file(settings) or ui_settings.get("last_excel_file", "") or "")
        )
        self._activate_dialog_parent()
        selected, _ = QFileDialog.getOpenFileName(
            self._dialog_parent,
            "Mitarbeiter Excel auswählen",
            start_path,
            "Excel-Dateien (*.xlsx *.xls *.xlsm);;Alle Dateien (*)",
        )

        if selected:
            self._set_company_excel_file(settings, selected)
            settings.setdefault("ui", {})["last_excel_file"] = selected
            save_settings(settings)
            self._processing_status = self._idle_processing_status()

        payload = self._processing_payload(load_settings())
        serialized = json.dumps(payload, ensure_ascii=False)
        self.processingStateChanged.emit(serialized)
        return serialized

    @Slot(result=str)
    def startCheck(self) -> str:
        if self._processing_running or self._shipping_running or self._mass_message_running:
            return self._emit_processing_payload(load_settings())

        settings = load_settings()
        allowed, license_state = LicenseManager(settings).require_action("processing")
        if not allowed:
            self._processing_status = {
                **self._idle_processing_status(),
                "can_check": False,
                "current_step": "Lizenz erforderlich",
                "errors": 1,
                "message": license_state.get("last_message", "Bitte aktivieren Sie eine gültige Lizenz."),
            }
            return self._emit_processing_payload(settings)

        ui_settings = settings.get("ui", {})
        pdf_input = Path(str(ui_settings.get("last_pdf_dir", "") or "")).expanduser()
        excel_path = Path(str(get_company_email_excel_file(settings) or ui_settings.get("last_excel_file", "") or "")).expanduser()
        pdf_expected = "pdf" if self._pdf_input_mode(settings) == "single_pdf" else "folder"
        pdf_state = self._path_state(str(pdf_input), expected=pdf_expected)
        excel_state = self._path_state(str(excel_path), expected="excel")

        if not pdf_state["valid"] or not excel_state["valid"]:
            self._processing_status = {
                **self._idle_processing_status(),
                "can_check": False,
                "current_step": "Eingaben prüfen",
                "warnings": 1,
                "message": "Bitte zuerst gültigen PDF-Eingang und eine Excel-Datei auswählen.",
            }
            return self._emit_processing_payload(settings)

        self._processing_running = True
        self._processing_status = {
            **self._idle_processing_status(),
            "running": True,
            "can_check": False,
            "current_step": "Prüfung läuft",
            "progress": 8,
            "message": "Prüfung läuft. Core-Verarbeitung wurde gestartet.",
        }
        self._emit_processing_payload(settings)

        self.worker_thread = QThread(self)
        self.worker = ProcessingWorker(
            mode="check",
            pdf_input=pdf_input,
            excel_path=excel_path,
            settings=settings,
            dry_run=bool(ui_settings.get("dry_run_default", True)),
        )
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.run)
        self.worker.progress.connect(self._on_processing_progress)
        self.worker.finished.connect(self._on_processing_finished)
        self.worker.error.connect(self._on_processing_error)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.error.connect(self.worker_thread.quit)
        self.worker_thread.finished.connect(self._cleanup_worker)
        self.worker_thread.start()

        return json.dumps(self._processing_payload(settings), ensure_ascii=False)

    @Slot(result=str)
    def startShippingDryRun(self) -> str:
        return self._start_shipping(dry_run=True)

    @Slot(result=str)
    def startShippingSend(self) -> str:
        return self._start_shipping(dry_run=False)

    @Slot(str, result=str)
    def startSelectedShippingSend(self, selected_json: str) -> str:
        return self._start_shipping(dry_run=False, selected_persnr=self._parse_selected_persnr(selected_json))

    @Slot(result=str)
    def previewShippingSend(self) -> str:
        return self._preview_shipping_send(selected_persnr=None)

    @Slot(str, result=str)
    def previewSelectedShippingSend(self, selected_json: str) -> str:
        return self._preview_shipping_send(selected_persnr=self._parse_selected_persnr(selected_json))

    def _preview_shipping_send(self, selected_persnr: set[str] | None) -> str:
        settings = self._settings_with_company_mail(load_settings())
        rows = self._shipping_source_rows
        try:
            if self._shipping_running or self._processing_running or self._mass_message_running:
                raise ValueError("Bitte warten, bis der aktuelle Lauf abgeschlossen ist.")
            if not self._shipping_status.get("finished") or not rows:
                raise ValueError("Bitte zuerst Versand vorbereiten.")

            from core.message_templates import (
                build_mail_context,
                build_send_preview_data,
                format_message_template,
            )

            preview = build_send_preview_data(
                settings=settings,
                table_rows=rows,
                dry_run=False,
                summary={
                    "missing_email_count": sum(1 for row in rows if row.get("Status") == "Keine E-Mail"),
                    "missing_files_count": sum(1 for row in rows if row.get("Status") == "Keine Dateien"),
                },
                selected_persnr=selected_persnr,
            )
            preview_rows = preview.get("preview_rows", [])
            if not preview_rows:
                raise ValueError("Es gibt keine sendbaren Einträge mit E-Mail und PDF-Anhang.")

            sample_persnr = str(preview_rows[0].get("PersNr", "") or "")
            context = build_mail_context(
                settings,
                sample_persnr,
                company_id=str(settings.get("selected_company_id", "") or "").strip() or None,
            )
            mail_text = settings.get("mail_text", {})
            body_template = str(mail_text.get("body", "") or "")
            body_html_template = str(mail_text.get("body_html", "") or "")
            body_preview = format_message_template(body_template, context) if body_template else ""
            body_html_preview = (
                format_message_template(body_html_template, context)
                if body_html_template
                else ""
            )
            if not body_preview and body_html_preview:
                body_preview = re.sub(r"<[^>]+>", " ", body_html_preview)
                body_preview = " ".join(body_preview.split())
            smtp_settings = settings.get("smtp", {})
            return json.dumps(
                {
                    "ok": True,
                    "message": "Versand-Vorschau ist bereit.",
                    "mail_mode": str(settings.get("mail_mode", "smtp") or "smtp"),
                    "from_email": str(smtp_settings.get("from_email", "") or ""),
                    "from_name": str(smtp_settings.get("from_name", "") or ""),
                    "summary_lines": preview.get("summary_lines", []),
                    "subject_preview": preview.get("subject_preview", ""),
                    "body_preview": body_preview,
                    "body_html_preview": body_html_preview,
                    "rows": preview_rows,
                    "total_count": len(preview_rows),
                },
                ensure_ascii=False,
            )
        except Exception as exc:
            return json.dumps({"ok": False, "message": str(exc)}, ensure_ascii=False)

    def _start_shipping(self, dry_run: bool, selected_persnr: set[str] | None = None) -> str:
        if self._shipping_running or self._processing_running or self._mass_message_running:
            return self._emit_shipping_payload(self._settings_with_company_mail(load_settings()))

        settings = self._settings_with_company_mail(load_settings())
        allowed, license_state = LicenseManager(settings).require_action("shipping")
        if not allowed:
            self._shipping_status = {
                **self._idle_shipping_status(),
                "can_send": False,
                "current_step": "Lizenz erforderlich",
                "errors": 1,
                "message": license_state.get("last_message", "Bitte aktivieren Sie eine gültige Lizenz."),
            }
            return self._emit_shipping_payload(settings)

        ui_settings = settings.get("ui", {})
        pdf_input = Path(str(ui_settings.get("last_pdf_dir", "") or "")).expanduser()
        excel_path = Path(str(get_company_email_excel_file(settings) or ui_settings.get("last_excel_file", "") or "")).expanduser()
        pdf_expected = "pdf" if self._pdf_input_mode(settings) == "single_pdf" else "folder"
        pdf_state = self._path_state(str(pdf_input), expected=pdf_expected)
        excel_state = self._path_state(str(excel_path), expected="excel")

        if not pdf_state["valid"] or not excel_state["valid"]:
            self._shipping_status = {
                **self._idle_shipping_status(),
                "can_send": False,
                "current_step": "Eingaben prüfen",
                "errors": 1,
                "message": "Bitte zuerst gültigen PDF-Eingang und eine Excel-Datei auswählen.",
            }
            return self._emit_shipping_payload(settings)

        self._shipping_running = True
        self._shipping_status = {
            **self._idle_shipping_status(),
            "running": True,
            "can_send": False,
            "current_step": "Versand wird vorbereitet" if dry_run else "E-Mails werden gesendet",
            "progress": 8,
            "dry_run": dry_run,
            "message": "Dry-Run läuft. Anhänge und Versandbericht werden vorbereitet." if dry_run else "E-Mail Versand läuft. Verbindung und Anhänge werden geprüft.",
        }
        self._emit_shipping_payload(settings)

        self.worker_thread = QThread(self)
        self.worker = ProcessingWorker(
            mode="send",
            pdf_input=pdf_input,
            excel_path=excel_path,
            settings=settings,
            dry_run=dry_run,
            selected_persnr=selected_persnr,
        )
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.run)
        self.worker.progress.connect(self._on_shipping_progress)
        self.worker.finished.connect(self._on_shipping_finished)
        self.worker.error.connect(self._on_shipping_error)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.error.connect(self.worker_thread.quit)
        self.worker_thread.finished.connect(self._cleanup_worker)
        self.worker_thread.start()

        return json.dumps(self._shipping_payload(settings), ensure_ascii=False)

    def _processing_payload(self, settings: dict) -> dict:
        ui_settings = settings.get("ui", {})

        pdf_input_mode = self._pdf_input_mode(settings)

        pdf_input = str(ui_settings.get("last_pdf_dir", "") or "").strip()
        excel_file = str(
            get_company_email_excel_file(settings)
            or ui_settings.get("last_excel_file", "")
            or ""
        ).strip()

        pdf_state = self._path_state(
            pdf_input,
            expected="pdf" if pdf_input_mode == "single_pdf" else "folder",
        )
        excel_state = self._path_state(excel_file, expected="excel")
        output_state = self._path_state(str(GESOB_DIR), expected="folder")
        can_check = bool(pdf_state["valid"] and excel_state["valid"] and output_state["valid"])
        status = {**self._processing_status}
        if not status.get("running"):
            status["can_check"] = can_check
            if not status.get("finished") and not status.get("failed"):
                status["current_step"] = "Bereit" if can_check else "Eingaben prüfen"
                status["warnings"] = 0 if can_check else 1
                status["message"] = (
                    "Eingaben bereit. Prüfung kann gestartet werden."
                    if can_check
                    else "Bitte gültigen PDF-Eingang und eine Excel-Datei auswählen."
                )

        return {
            "company": {
                "id": str(settings.get("selected_company_id", "") or ""),
                "name": get_company_name(settings),
            },
            "mode": pdf_input_mode,
            "dry_run_default": bool(ui_settings.get("dry_run_default", True)),
            "inputs": {
                "pdf": pdf_state,
                "excel": excel_state,
                "output": output_state,
            },
            "status": status,
        }

    def _emit_processing_payload(self, settings: dict) -> str:
        serialized = json.dumps(self._processing_payload(settings), ensure_ascii=False)
        self.processingStateChanged.emit(serialized)
        return serialized

    def _shipping_payload(self, settings: dict) -> dict:
        rows = self._shipping_rows or self._shipping_rows_from_validation()
        status = {**self._shipping_status}
        inputs_ready = self._inputs_ready(settings)
        ready_count = sum(1 for row in rows if row.get("status") in {"Bereit", "Dry-Run", "Gesendet"})
        sent_count = sum(1 for row in rows if row.get("status") == "Gesendet")
        dry_run_count = sum(1 for row in rows if row.get("status") == "Dry-Run")
        skipped_count = sum(1 for row in rows if row.get("status") in {"Keine E-Mail", "Keine Dateien"})
        error_count = sum(1 for row in rows if row.get("status") == "Fehler")

        if not status.get("running"):
            status["can_send"] = bool(inputs_ready)
            if not status.get("finished") and not status.get("failed"):
                status["current_step"] = "Bereit" if inputs_ready else "Eingaben prüfen"
                status["message"] = (
                    "Versand kann als Dry-Run vorbereitet werden."
                    if inputs_ready
                    else "Bitte PDF-Eingang und Excel-Datei in Verarbeitung auswählen."
                )

        return {
            "status": status,
            "metrics": {
                "ready": ready_count,
                "sent": sent_count,
                "queued": max(0, ready_count - sent_count),
                "errors": error_count,
                "exported": dry_run_count,
                "skipped": skipped_count,
                "total": len(rows),
            },
            "rows": rows,
            "reports": {"send": self._report_state("send_report.xlsx")},
        }

    @staticmethod
    def _parse_selected_persnr(selected_json: str) -> set[str] | None:
        try:
            raw_values = json.loads(str(selected_json or "[]"))
        except Exception:
            raw_values = []
        if not isinstance(raw_values, list):
            return None
        selected = {
            str(value or "").strip()
            for value in raw_values
            if str(value or "").strip()
        }
        return selected if selected else set()

    @staticmethod
    def _selected_company(settings: dict) -> dict | None:
        selected_company_id = str(settings.get("selected_company_id", "") or "").strip()
        for company in settings.get("companies", []):
            if not isinstance(company, dict):
                continue
            if str(company.get("id", "") or "").strip() == selected_company_id:
                return company
        return None

    @staticmethod
    def _company_mail_settings(company: dict | None) -> dict:
        if not isinstance(company, dict):
            return {"scope": "global", "smtp": {}}
        mail_settings = company.get("mail_settings")
        if not isinstance(mail_settings, dict):
            return {"scope": "global", "smtp": {}}
        scope = str(mail_settings.get("scope", "global") or "global").strip().lower()
        if scope not in {"global", "custom"}:
            scope = "global"
        smtp = mail_settings.get("smtp") if isinstance(mail_settings.get("smtp"), dict) else {}
        return {"scope": scope, "smtp": smtp}

    def _settings_with_company_mail(self, settings: dict) -> dict:
        effective = deepcopy(settings)
        company = self._selected_company(effective)
        mail_settings = self._company_mail_settings(company)
        if mail_settings.get("scope") != "custom":
            return effective

        effective["mail_mode"] = "smtp"
        effective_smtp = effective.setdefault("smtp", {})
        for key, value in mail_settings.get("smtp", {}).items():
            if key == "password":
                if str(value or ""):
                    effective_smtp[key] = str(value)
                continue
            effective_smtp[key] = value
        return effective

    def _company_payload(self, settings: dict) -> dict:
        selected_company_id = str(settings.get("selected_company_id", "") or "").strip()
        companies = []
        for company in settings.get("companies", []):
            if not isinstance(company, dict):
                continue
            company_id = str(company.get("id", "") or "").strip()
            excel_file = str(company.get("email_excel_file", "") or "").strip()
            mail_settings = self._company_mail_settings(company)
            companies.append(
                {
                    "id": company_id,
                    "name": str(company.get("name", "") or company_id),
                    "selected": company_id == selected_company_id,
                    "excel": self._path_state(excel_file, expected="excel"),
                    "mail_scope": mail_settings.get("scope", "global"),
                }
            )

        selected_company = self._selected_company(settings)
        company_mail = self._company_mail_settings(selected_company)
        effective_settings = self._settings_with_company_mail(settings)
        smtp_settings = effective_settings.get("smtp", {})
        license_settings = settings.get("license", {})
        period_settings = settings.get("period", {})
        selected_excel = str(get_company_email_excel_file(settings) or "").strip()
        smtp_server = str(smtp_settings.get("server", "") or "").strip()
        smtp_from = str(smtp_settings.get("from_email", "") or smtp_settings.get("username", "") or "").strip()
        license_status = str(license_settings.get("status", "") or "unregistered").strip().lower()

        return {
            "selected_company_id": selected_company_id,
            "selected_company_name": get_company_name(settings),
            "companies": companies,
            "selected_excel": self._path_state(selected_excel, expected="excel"),
            "output": self._path_state(str(GESOB_DIR), expected="folder"),
            "smtp": {
                "server": smtp_server,
                "from": smtp_from,
                "configured": bool(smtp_server and smtp_from),
                "label": ("Eigene SMTP" if company_mail.get("scope") == "custom" else "Global SMTP") if smtp_server and smtp_from else "Nicht konfiguriert",
                "mode": str(effective_settings.get("mail_mode", "smtp") or "smtp"),
                "scope": company_mail.get("scope", "global"),
                "password_set": bool(str(company_mail.get("smtp", {}).get("password", "") or "")),
                "settings": {
                    "server": str(company_mail.get("smtp", {}).get("server", "") or ""),
                    "port": int(company_mail.get("smtp", {}).get("port", 587) or 587),
                    "security": str(company_mail.get("smtp", {}).get("security", "tls") or "tls"),
                    "username": str(company_mail.get("smtp", {}).get("username", "") or ""),
                    "from_email": str(company_mail.get("smtp", {}).get("from_email", "") or ""),
                    "from_name": str(company_mail.get("smtp", {}).get("from_name", "") or ""),
                    "timeout_sec": int(company_mail.get("smtp", {}).get("timeout_sec", 30) or 30),
                },
            },
            "license": {
                "status": license_status,
                "label": "Aktiv" if license_status in {"active", "business", "registered", "valid"} else "Nicht registriert",
            },
            "period": {
                "mode": str(period_settings.get("mode", "") or "automatic_current_month"),
                "month": int(period_settings.get("month", 0) or 0),
                "year": int(period_settings.get("year", 0) or 0),
            },
        }

    def _license_payload(self, settings: dict, refresh: bool = False, state: dict | None = None) -> dict:
        manager = LicenseManager(settings)
        state = state or (manager.refresh(force=False, start_trial=True) if refresh else manager.load_state())
        raw_key = str(state.get("license_key", "") or settings.get("license", {}).get("key", "") or "").strip()
        status = str(state.get("status", "") or "unregistered").strip().lower()
        license_type = str(state.get("type", "") or "none").strip().lower()
        active = status in {"trialing", "active", "expiring_soon"}
        status_label = self._license_label(status, license_type, state)
        status_level = self._license_status_level(status, active, manager.server_url)
        return {
            "status": status,
            "label": status_label,
            "status_level": status_level,
            "active": active,
            "key_masked": self._mask_license_key(raw_key),
            "key_present": bool(raw_key),
            "type": self._license_type_label(license_type),
            "plan": str(state.get("plan", "") or ("Trial" if license_type == "trial" else "Professional")),
            "seats": str(state.get("seats", "") or "1"),
            "server": str(state.get("server", "") or ("Verbunden" if manager.server_url else "Nicht konfiguriert")),
            "server_note": "Online-Prüfung aktiv" if manager.server_url else "Keine Serverlogik aktiv",
            "mode": "Server" if manager.server_url else "Lokal",
            "company": get_company_name(settings),
            "machine_id": str(state.get("machine_id", "") or ""),
            "days_remaining": state.get("days_remaining"),
            "trial_ends_at": str(state.get("trial_ends_at", "") or ""),
            "current_period_end": str(state.get("current_period_end", "") or ""),
            "message": self._license_message(status, state),
            "state_list": self._license_state_list(status),
            "features": [
                {"name": "PDF Import", "enabled": True},
                {"name": "Excel Import", "enabled": True},
                {"name": "Prüfung", "enabled": True},
                {"name": "Versand", "enabled": active or not manager.server_url},
                {"name": "Lizenzserver", "enabled": bool(manager.server_url)},
            ],
            "history": [
                {
                    "date": str(state.get("last_successful_check_at", "") or "Noch nicht geprüft"),
                    "action": "Lizenzprüfung",
                    "computer": str(state.get("machine_id", "") or "-"),
                    "user": "-",
                    "status": status_label,
                }
            ],
        }

    @staticmethod
    def _mask_license_key(value: str) -> str:
        if not value:
            return "Nicht hinterlegt"
        return f"{value[:8]}-••••-{value[-4:]}"

    @staticmethod
    def _license_type_label(value: str) -> str:
        labels = {
            "trial": "Trial",
            "subscription": "Subscription",
            "lifetime": "Lifetime",
            "demo": "Demo",
            "internal": "Internal",
            "none": "Nicht registriert",
        }
        return labels.get(value, value or "Nicht registriert")

    @staticmethod
    def _license_label(status: str, license_type: str, state: dict) -> str:
        days = state.get("days_remaining")
        if status == "trialing":
            suffix = f" · {days} Tage verbleibend" if days is not None else ""
            return f"Trial{suffix}"
        if license_type == "lifetime" and status == "active":
            return "Lifetime"
        if status == "active":
            return "Active · Professional"
        if status == "expiring_soon":
            return "Läuft bald ab"
        if status == "past_due":
            return "Zahlung fehlgeschlagen"
        if status == "unpaid":
            return "Zahlung offen"
        if status == "canceled":
            return "Gekündigt"
        if status == "refunded":
            return "Erstattet"
        if status == "disputed":
            return "Zahlung angefochten"
        if status == "revoked":
            return "Widerrufen"
        if status == "invalid":
            return "Ungültig"
        if status == "expired":
            return "Abgelaufen"
        if status == "no_connection":
            return "Keine Verbindung"
        return "Nicht registriert"

    @staticmethod
    def _license_status_level(status: str, active: bool, server_url: str) -> str:
        if status in {"expired", "unpaid", "canceled", "refunded", "disputed", "revoked", "invalid"}:
            return "error"
        if status in {"past_due", "expiring_soon", "no_connection"}:
            return "warning"
        if active:
            return "ready"
        return "warning" if server_url else "neutral"

    @staticmethod
    def _license_message(status: str, state: dict) -> str:
        messages = {
            "trialing": "Testphase aktiv. LohnMail kann während der Testphase genutzt werden.",
            "active": "Lizenz aktiv. Alle freigeschalteten Aktionen sind verfügbar.",
            "expiring_soon": "Lizenz läuft bald ab. Bitte prüfen Sie die Verlängerung.",
            "past_due": "Zahlung überfällig. Bitte Zahlungsdaten im Kundenportal aktualisieren.",
            "unpaid": "Lizenz wegen offener Zahlung gesperrt.",
            "canceled": "Lizenz gekündigt. Nutzung ist nach Ablauf der Periode gesperrt.",
            "expired": "Lizenz oder Testphase abgelaufen.",
            "refunded": "Zahlung erstattet. Lizenz gesperrt.",
            "disputed": "Zahlung angefochten. Lizenz gesperrt.",
            "revoked": "Lizenz wurde widerrufen.",
            "invalid": "Lizenz ist ungültig oder an einen anderen Computer gebunden.",
            "no_connection": "Lizenzserver nicht erreichbar. Offline-Gnadenfrist wird geprüft.",
            "unregistered": "Keine Lizenz hinterlegt.",
        }
        return messages.get(status) or str(state.get("last_message", "") or "Lizenzstatus geladen.")

    @classmethod
    def _license_state_list(cls, current_status: str) -> list[dict]:
        groups = [
            ("trialing", "Trial", "info"),
            ("active", "Aktiv", "success"),
            ("expiring_soon", "Läuft bald ab", "warning"),
            ("past_due", "Zahlung überfällig", "warning"),
            ("unpaid", "Unbezahlt", "error"),
            ("canceled", "Gekündigt", "error"),
            ("expired", "Abgelaufen", "error"),
            ("refunded", "Erstattet", "error"),
            ("disputed", "Angefochten", "error"),
            ("revoked", "Widerrufen", "error"),
            ("invalid", "Ungültig", "error"),
            ("no_connection", "Keine Verbindung", "warning"),
        ]
        return [
            {
                "status": status,
                "label": label,
                "level": level,
                "active": status == current_status,
            }
            for status, label, level in groups
        ]

    def _settings_payload(self, settings: dict) -> dict:
        smtp = settings.get("smtp", {})
        mail_text = settings.get("mail_text", {})
        pdf_password = settings.get("pdf_password", {})
        period = settings.get("period", {})
        ui_settings = settings.get("ui", {})
        notification_settings = settings.get("notifications", {})
        return {
            "mail_mode": str(settings.get("mail_mode", "smtp") or "smtp"),
            "smtp": {
                "server": str(smtp.get("server", "") or ""),
                "port": int(smtp.get("port", 587) or 587),
                "security": str(smtp.get("security", "tls") or "tls"),
                "username": str(smtp.get("username", "") or ""),
                "password_set": bool(str(smtp.get("password", "") or "")),
                "timeout_sec": int(smtp.get("timeout_sec", 30) or 30),
                "from_email": str(smtp.get("from_email", "") or ""),
                "from_name": str(smtp.get("from_name", "Personalabteilung") or "Personalabteilung"),
            },
            "mail_text": {
                "subject": str(mail_text.get("subject", "") or ""),
                "body": str(mail_text.get("body", "") or ""),
                "body_html": str(mail_text.get("body_html", "") or ""),
            },
            "pdf_password": {
                "enabled": bool(pdf_password.get("enabled", True)),
                "prefix": str(pdf_password.get("prefix", "") or ""),
                "suffix": str(pdf_password.get("suffix", "") or ""),
            },
            "period": {
                "mode": str(period.get("mode", "automatic_current_month") or "automatic_current_month"),
                "month": int(period.get("month", datetime.now().month) or datetime.now().month),
                "year": int(period.get("year", datetime.now().year) or datetime.now().year),
            },
            "ui": {
                "dry_run_default": bool(ui_settings.get("dry_run_default", True)),
                "remember_last_paths": bool(ui_settings.get("remember_last_paths", True)),
            },
            "notifications": {
                "show_badge": bool(notification_settings.get("show_badge", True)),
                "workflow_warnings": bool(notification_settings.get("workflow_warnings", True)),
                "validation_warnings": bool(notification_settings.get("validation_warnings", True)),
                "processing_errors": bool(notification_settings.get("processing_errors", True)),
                "delivery_events": bool(notification_settings.get("delivery_events", True)),
                "auto_open_on_start": bool(notification_settings.get("auto_open_on_start", False)),
            },
            "company": self._company_payload(settings),
            "license": self._license_payload(settings),
            "outlook_supported": True,
        }

    def _mass_message_payload(self, settings: dict) -> dict:
        company_id = str(settings.get("selected_company_id", "") or "").strip()
        excel_file = str(
            get_company_email_excel_file(settings)
            or settings.get("ui", {}).get("last_excel_file", "")
            or ""
        ).strip()
        preview_payload = {
            key: value
            for key, value in self._mass_message_preview.items()
            if key != "recipients"
        }
        return {
            "status": {**self._mass_message_status},
            "preview": preview_payload,
            "company": {
                "id": company_id,
                "name": get_company_name(settings, company_id),
            },
            "excel": self._path_state(excel_file, expected="excel"),
            "mail_mode": str(settings.get("mail_mode", "smtp") or "smtp"),
        }

    def _emit_mass_message_payload(self, settings: dict) -> str:
        serialized = json.dumps(self._mass_message_payload(settings), ensure_ascii=False)
        self.massMessageStateChanged.emit(serialized)
        return serialized

    def _build_mass_message_preview(self, settings: dict, subject: str, body: str) -> dict:
        from core.jobs import load_mass_message_rows
        from core.message_templates import build_mail_context, format_message_template

        company_id = str(settings.get("selected_company_id", "") or "").strip()
        excel_path = Path(
            str(
                get_company_email_excel_file(settings, company_id)
                or settings.get("ui", {}).get("last_excel_file", "")
                or ""
            )
        ).expanduser()
        subject_template = str(subject or "").strip()
        body_template = str(body or "")

        if not company_id:
            raise ValueError("Bitte ein Unternehmen auswählen.")
        if not excel_path.is_file():
            raise ValueError("Für dieses Unternehmen ist keine gültige Excel-Datei hinterlegt.")
        if not subject_template:
            raise ValueError("Bitte einen Betreff eingeben.")
        if not body_template.strip():
            raise ValueError("Bitte eine Nachricht eingeben.")

        recipients = load_mass_message_rows(excel_path)
        if not recipients:
            raise ValueError("In der Excel-Datei wurden keine E-Mail-Adressen gefunden.")

        sample_persnr = str(recipients[0].get("PersNr", "") or "")
        context = build_mail_context(settings, sample_persnr, company_id=company_id)
        subject_preview = format_message_template(subject_template, context)
        body_preview = format_message_template(body_template, context)

        return {
            "ready": True,
            "company_id": company_id,
            "company_name": str(context.get("company_name", "") or get_company_name(settings, company_id)),
            "excel_path": str(excel_path),
            "subject_preview": subject_preview,
            "body_preview": body_preview,
            "total_count": len(recipients),
            "recipients": recipients,
            "rows": recipients[:50],
        }

    def _emit_shipping_payload(self, settings: dict) -> str:
        serialized = json.dumps(self._shipping_payload(settings), ensure_ascii=False)
        self.shippingStateChanged.emit(serialized)
        return serialized

    @Slot(str)
    def _on_processing_progress(self, message: str) -> None:
        self._processing_status["message"] = message
        self._processing_status["progress"] = min(92, int(self._processing_status.get("progress", 8)) + 14)
        self._processing_status["current_step"] = "Prüfung läuft"
        serialized = self._emit_processing_payload(load_settings())
        self.processingProgress.emit(serialized)

    @Slot(str)
    def _on_shipping_progress(self, message: str) -> None:
        self._shipping_status["message"] = message
        self._shipping_status["progress"] = min(92, int(self._shipping_status.get("progress", 8)) + 12)
        self._shipping_status["current_step"] = "Versand wird vorbereitet"
        serialized = self._emit_shipping_payload(self._settings_with_company_mail(load_settings()))
        self.shippingProgress.emit(serialized)

    @Slot(str)
    def _on_mass_message_progress(self, message: str) -> None:
        self._mass_message_status["message"] = message
        self._mass_message_status["progress"] = min(92, int(self._mass_message_status.get("progress", 8)) + 8)
        self._mass_message_status["current_step"] = "Nachricht wird gesendet"
        serialized = self._emit_mass_message_payload(self._settings_with_company_mail(load_settings()))
        self.massMessageProgress.emit(serialized)

    @Slot(dict)
    def _on_processing_finished(self, result: dict) -> None:
        summary = result.get("summary", {}) if isinstance(result, dict) else {}
        table_rows = result.get("table_rows", []) if isinstance(result, dict) else []
        employees_total = int(summary.get("unique_persnr_count", len(table_rows)) or 0)
        missing_email = int(summary.get("missing_email_count", 0) or 0)
        missing_files = int(summary.get("missing_files_count", 0) or 0)
        invalid_pdf = int(summary.get("invalid_pdf_files", 0) or 0)
        unreadable_pdf = int(summary.get("unreadable_pdf_files", 0) or 0)

        self._processing_running = False
        self._processing_status = {
            **self._idle_processing_status(),
            "finished": True,
            "can_check": True,
            "current_step": "Prüfung abgeschlossen",
            "progress": 100,
            "employees_total": employees_total,
            "processed": len(table_rows),
            "sent": 0,
            "warnings": missing_email + missing_files,
            "missing_email": missing_email,
            "missing_files": missing_files,
            "errors": invalid_pdf + unreadable_pdf,
            "elapsed": "--:--:--",
            "remaining": "00:00:00",
            "message": "Prüfung abgeschlossen. Ergebnisse wurden erstellt.",
            "reports": {
                "audit_path": str(result.get("audit_path") or ""),
                "missing_pdf_path": str(result.get("missing_pdf_path") or ""),
                "run_dir": str(result.get("run_dir") or ""),
            },
        }
        self._validation_state = self._build_validation_state(result)
        serialized = self._emit_processing_payload(load_settings())
        self.processingFinished.emit(serialized)

    @Slot(dict)
    def _on_shipping_finished(self, result: dict) -> None:
        summary = result.get("summary", {}) if isinstance(result, dict) else {}
        table_rows = result.get("table_rows", []) if isinstance(result, dict) else []
        dry_run = bool(summary.get("dry_run", True))
        completed_count = int(summary.get("prepared_or_sent_count", 0) or 0)
        self._shipping_running = False
        self._shipping_source_rows = [row for row in table_rows if isinstance(row, dict)]
        self._shipping_rows = [self._shipping_row(row) for row in table_rows if isinstance(row, dict)]
        self._shipping_status = {
            **self._idle_shipping_status(),
            "finished": True,
            "can_send": True,
            "current_step": "Dry-Run abgeschlossen" if dry_run else "Versand abgeschlossen",
            "progress": 100,
            "dry_run": dry_run,
            "prepared": completed_count if dry_run else 0,
            "sent": 0 if dry_run else completed_count,
            "skipped": int(summary.get("skipped_count", 0) or 0),
            "errors": int(summary.get("failed_count", 0) or 0),
            "message": "Versand-Dry-Run abgeschlossen. Anhänge und Bericht wurden erstellt." if dry_run else f"Versand abgeschlossen. {completed_count} E-Mails wurden gesendet.",
            "reports": {
                "send_report_path": str(result.get("send_report_path") or ""),
                "run_dir": str(result.get("run_dir") or ""),
            },
        }
        serialized = self._emit_shipping_payload(self._settings_with_company_mail(load_settings()))
        self.shippingFinished.emit(serialized)

    @Slot(dict)
    def _on_mass_message_finished(self, result: dict) -> None:
        sent_count = int(result.get("sent_count", 0) or 0)
        error_count = int(result.get("error_count", 0) or 0)
        total_count = int(result.get("total_count", 0) or 0)
        self._mass_message_running = False
        self._mass_message_status = {
            **self._idle_mass_message_status(),
            "finished": True,
            "preview_ready": True,
            "current_step": "Nachricht abgeschlossen",
            "progress": 100,
            "sent_count": sent_count,
            "error_count": error_count,
            "total_count": total_count,
            "errors": result.get("errors", []) if isinstance(result.get("errors", []), list) else [],
            "message": f"Nachricht-Versand abgeschlossen: {sent_count}/{total_count} gesendet, {error_count} Fehler.",
        }
        serialized = self._emit_mass_message_payload(self._settings_with_company_mail(load_settings()))
        self.massMessageFinished.emit(serialized)

    @Slot(str)
    def _on_processing_error(self, message: str) -> None:
        self._processing_running = False
        self._processing_status = {
            **self._idle_processing_status(),
            "failed": True,
            "can_check": True,
            "current_step": "Fehler",
            "progress": 0,
            "errors": 1,
            "message": f"Prüfung fehlgeschlagen: {message}",
        }
        serialized = self._emit_processing_payload(load_settings())
        self.processingError.emit(serialized)

    @Slot(str)
    def _on_shipping_error(self, message: str) -> None:
        self._shipping_running = False
        self._shipping_status = {
            **self._idle_shipping_status(),
            "failed": True,
            "can_send": True,
            "current_step": "Fehler",
            "progress": 0,
            "errors": 1,
            "message": f"Versand fehlgeschlagen: {message}",
        }
        serialized = self._emit_shipping_payload(self._settings_with_company_mail(load_settings()))
        self.shippingError.emit(serialized)

    @Slot(str)
    def _on_mass_message_error(self, message: str) -> None:
        self._mass_message_running = False
        self._mass_message_status = {
            **self._idle_mass_message_status(),
            "failed": True,
            "preview_ready": bool(self._mass_message_preview.get("ready")),
            "current_step": "Fehler",
            "progress": 0,
            "error_count": 1,
            "message": f"Nachricht-Versand fehlgeschlagen: {message}",
        }
        serialized = self._emit_mass_message_payload(self._settings_with_company_mail(load_settings()))
        self.massMessageError.emit(serialized)

    @Slot()
    def _cleanup_worker(self) -> None:
        if self.worker is not None:
            self.worker.deleteLater()
        if self.worker_thread is not None:
            self.worker_thread.deleteLater()
        self.worker = None
        self.worker_thread = None

    @staticmethod
    def _idle_processing_status() -> dict:
        return {
            "running": False,
            "finished": False,
            "failed": False,
            "can_check": False,
            "current_step": "Eingaben prüfen",
            "progress": 0,
            "employees_total": 0,
            "processed": 0,
            "sent": 0,
            "warnings": 0,
            "missing_email": 0,
            "missing_files": 0,
            "errors": 0,
            "elapsed": "00:00:00",
            "remaining": "--:--:--",
            "message": "Eingaben werden geladen.",
        }

    @staticmethod
    def _idle_shipping_status() -> dict:
        return {
            "running": False,
            "finished": False,
            "failed": False,
            "can_send": False,
            "current_step": "Eingaben prüfen",
            "progress": 0,
            "prepared": 0,
            "sent": 0,
            "skipped": 0,
            "errors": 0,
            "message": "Versanddaten werden geladen.",
        }

    @staticmethod
    def _idle_mass_message_status() -> dict:
        return {
            "running": False,
            "finished": False,
            "failed": False,
            "preview_ready": False,
            "current_step": "Bereit",
            "progress": 0,
            "sent_count": 0,
            "error_count": 0,
            "total_count": 0,
            "errors": [],
            "message": "Nachricht kann vorbereitet werden.",
        }

    @staticmethod
    def _empty_mass_message_preview() -> dict:
        return {
            "ready": False,
            "company_id": "",
            "company_name": "",
            "excel_path": "",
            "subject_preview": "",
            "body_preview": "",
            "total_count": 0,
            "recipients": [],
            "rows": [],
        }

    def _empty_validation_state(self) -> dict:
        return {
            "ready": False,
            "summary": {
                "critical": 0,
                "warnings": 0,
                "info": 0,
                "checked": 0,
                "total": 0,
                "status": "Nicht gestartet",
                "updated": "--",
            },
            "filters": {
                "all": 0,
                "critical": 0,
                "warnings": 0,
                "info": 0,
            },
            "rows": [],
            "detail": None,
            "reports": self._reports_state(),
        }

    def _build_validation_state(self, result: dict) -> dict:
        summary = result.get("summary", {}) if isinstance(result, dict) else {}
        table_rows = result.get("table_rows", []) if isinstance(result, dict) else []
        validation_rows = [self._validation_row(row) for row in table_rows if isinstance(row, dict)]
        critical = sum(1 for row in validation_rows if row["severity"] == "critical")
        warnings = sum(1 for row in validation_rows if row["severity"] == "warning")
        info = sum(1 for row in validation_rows if row["severity"] == "info")
        checked = int(summary.get("unique_persnr_count", len(table_rows)) or 0)
        total = max(checked, len(table_rows))
        updated = datetime.now().strftime("%d.%m.%Y %H:%M")

        return {
            "ready": True,
            "summary": {
                "critical": critical,
                "warnings": warnings,
                "info": info,
                "checked": checked,
                "total": total,
                "status": "Abgeschlossen",
                "updated": updated,
            },
            "filters": {
                "all": len(validation_rows),
                "critical": critical,
                "warnings": warnings,
                "info": info,
            },
            "rows": validation_rows,
            "detail": validation_rows[0] if validation_rows else None,
            "reports": {
                "audit": self._report_from_result(result, "audit_path", "audit_check.xlsx"),
                "missing": self._report_from_result(result, "missing_pdf_path", "ohne_email_gesamt.pdf"),
            },
        }

    @staticmethod
    def _validation_row(row: dict) -> dict:
        status = str(row.get("Status", "") or "OK")
        error = str(row.get("Error", "") or "").strip()
        persnr = str(row.get("PersNr", "") or "")
        name = " ".join(
            part for part in [
                str(row.get("Vorname", "") or "").strip(),
                str(row.get("Name", "") or "").strip(),
            ]
            if part
        ).strip() or "-"
        files = str(row.get("Files", "") or "").strip()

        if status == "Fehler" or error:
            severity = "critical"
            category = "PDF"
            description = error or "PDF-Datei konnte nicht validiert werden."
        elif status == "Keine Dateien":
            severity = "critical"
            category = "Dateien"
            description = "Für diesen Mitarbeiter wurde keine passende PDF-Datei gefunden."
        elif status == "Keine E-Mail":
            severity = "warning"
            category = "E-Mail"
            description = "Für diesen Mitarbeiter fehlt eine E-Mail-Adresse."
        else:
            severity = "success"
            category = "OK"
            description = "Keine Auffälligkeiten."

        return {
            "severity": severity,
            "status": status,
            "employee": name,
            "persnr": persnr,
            "category": category,
            "description": description,
            "document": files or "-",
            "position": "-",
            "email": str(row.get("Email", "") or ""),
            "count": int(row.get("Count", 0) or 0),
            "pages": int(row.get("Pages", 0) or 0),
        }

    @staticmethod
    def _shipping_row(row: dict) -> dict:
        persnr = str(row.get("PersNr", "") or "")
        first_name = str(row.get("Vorname", "") or "").strip()
        last_name = str(row.get("Name", "") or "").strip()
        name = " ".join(part for part in [first_name, last_name] if part).strip() or "-"
        status = str(row.get("Status", "") or "Bereit").strip() or "Bereit"
        attachment = str(row.get("Attachment", "") or "").strip()
        files = str(row.get("Files", "") or "").strip()
        document = attachment or files or "-"
        initials = "".join(part[:1].upper() for part in [first_name, last_name] if part)[:2] or "MA"
        return {
            "employee": name,
            "persnr": persnr,
            "initials": initials,
            "email": str(row.get("Email", "") or ""),
            "document": document,
            "size": "-",
            "status": status,
            "planned": "Dry-Run",
            "error": str(row.get("Error", "") or ""),
        }

    def _shipping_rows_from_validation(self) -> list[dict]:
        rows = []
        for row in self._validation_state.get("rows", []):
            if not isinstance(row, dict):
                continue
            status = str(row.get("status", "") or "")
            if status == "OK":
                status = "Bereit"
            rows.append(
                {
                    "employee": row.get("employee", "-"),
                    "persnr": row.get("persnr", ""),
                    "initials": self._initials(str(row.get("employee", "") or "")),
                    "email": row.get("email", ""),
                    "document": row.get("document", "-"),
                    "size": "-",
                    "status": status,
                    "planned": "Dry-Run",
                    "error": "",
                }
            )
        return rows

    def _inputs_ready(self, settings: dict) -> bool:
        ui_settings = settings.get("ui", {})
        pdf_input = str(ui_settings.get("last_pdf_dir", "") or "").strip()
        excel_file = str(
            get_company_email_excel_file(settings)
            or ui_settings.get("last_excel_file", "")
            or ""
        ).strip()
        pdf_expected = "pdf" if self._pdf_input_mode(settings) == "single_pdf" else "folder"
        return bool(
            self._path_state(pdf_input, expected=pdf_expected)["valid"]
            and self._path_state(excel_file, expected="excel")["valid"]
            and self._path_state(str(GESOB_DIR), expected="folder")["valid"]
        )

    @staticmethod
    def _initials(name: str) -> str:
        parts = [part for part in name.replace("-", " ").split() if part]
        return "".join(part[:1].upper() for part in parts[:2]) or "MA"

    @staticmethod
    def _normalize_company_id(value: str) -> str:
        normalized = []
        previous_dash = False
        for char in str(value or "").strip().lower():
            if char.isascii() and char.isalnum():
                normalized.append(char)
                previous_dash = False
            elif char in {"_", "-"} or char.isspace():
                if normalized and not previous_dash:
                    normalized.append("-")
                    previous_dash = True
        return "".join(normalized).strip("-")

    @staticmethod
    def _pdf_input_mode(settings: dict) -> str:
        mode = str(settings.get("ui", {}).get("last_pdf_input_mode", "folder") or "folder").strip()
        return mode if mode in {"folder", "single_pdf"} else "folder"

    @staticmethod
    def _set_company_excel_file(settings: dict, excel_file: str) -> None:
        selected_company_id = str(settings.get("selected_company_id", "") or "").strip()
        companies = settings.setdefault("companies", [])
        if isinstance(companies, list):
            for company in companies:
                if not isinstance(company, dict):
                    continue
                if str(company.get("id", "") or "").strip() == selected_company_id:
                    company["email_excel_file"] = excel_file
                    return

    def _activate_dialog_parent(self) -> None:
        if self._dialog_parent is None:
            return
        self._dialog_parent.raise_()
        self._dialog_parent.activateWindow()

    @staticmethod
    def _dialog_start_path(raw_path: str) -> str:
        if not raw_path:
            return str(Path.home())
        path = Path(raw_path).expanduser()
        if path.is_file():
            return str(path.parent)
        if path.is_dir():
            return str(path)
        for parent in path.parents:
            if parent.exists() and parent.is_dir():
                return str(parent)
        return str(Path.home())

    def _report_state(self, filename: str) -> dict[str, str | bool]:
        path = self._latest_report_path(filename)
        if path is None:
            return {"name": filename, "exists": False, "label": "Nicht erstellt", "path": ""}
        return {
            "name": filename,
            "exists": True,
            "label": self._format_mtime(path),
            "path": str(path),
        }

    def _reports_state(self) -> dict[str, dict[str, str | bool]]:
        return {
            "audit": self._report_state("audit_check.xlsx"),
            "missing": self._report_state("ohne_email_gesamt.pdf"),
            "send": self._report_state("send_report.xlsx"),
        }

    def _report_from_result(self, result: dict, key: str, filename: str) -> dict[str, str | bool]:
        raw_path = result.get(key) if isinstance(result, dict) else None
        path = Path(str(raw_path or ""))
        if path.is_file():
            return {
                "name": filename,
                "exists": True,
                "label": self._format_mtime(path),
                "path": str(path),
            }
        return self._report_state(filename)

    def _latest_report_path(self, filename: str) -> Path | None:
        candidates = [path for path in GESOB_DIR.rglob(filename) if path.is_file()]
        if not candidates:
            return None
        return max(candidates, key=lambda path: path.stat().st_mtime)

    def _path_state(self, raw_path: str, expected: str) -> dict[str, str | bool]:
        raw_path = str(raw_path or "").strip()
        if not raw_path:
            return {
                "path": "",
                "label": "Nicht ausgewählt",
                "exists": False,
                "valid": False,
                "expected": expected,
                "updated": "",
            }

        path = Path(raw_path).expanduser()
        exists = path.exists()
        if expected == "folder":
            valid = exists and path.is_dir()
        elif expected == "pdf":
            valid = exists and path.is_file() and path.suffix.lower() == ".pdf"
        elif expected == "excel":
            valid = exists and path.is_file() and path.suffix.lower() in {".xlsx", ".xls", ".xlsm"}
        else:
            valid = exists

        if valid:
            label = "Bereit"
        elif exists:
            label = "Falscher Typ"
        else:
            label = "Nicht gefunden"

        updated = ""
        if exists:
            try:
                updated = self._format_mtime(path)
            except OSError:
                updated = ""

        return {
            "path": str(path),
            "label": label,
            "exists": exists,
            "valid": valid,
            "expected": expected,
            "updated": updated,
        }

    @staticmethod
    def _format_mtime(path: Path) -> str:
        timestamp = datetime.fromtimestamp(path.stat().st_mtime)
        return timestamp.strftime("%d.%m.%Y %H:%M")

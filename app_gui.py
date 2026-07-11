import sys
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QThread, Signal, QUrl
from PySide6.QtGui import QAction, QColor, QDesktopServices, QFont, QTextCharFormat, QTextCursor, QTextListFormat
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenuBar,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.config import (
    APP_NAME,
    APP_TAGLINE,
    GESOB_DIR,
    consume_settings_warning,
    get_company_email_excel_file,
    get_company_name,
    load_settings,
    save_settings,
)
from core.help_content import build_help_html
from core.jobs import load_mass_message_rows, run_main_job, run_mass_message_job
from core.message_templates import (
    build_mail_context,
    build_send_preview_data,
    format_message_template,
    format_name_vorname_row,
)
from core.text_utils import repair_mojibake


class SettingsDialog(QDialog):
    SECTION_TITLES = {
        "mail": "E-Mail-Einstellungen",
        "companies": "Unternehmen",
        "letter": "E-Mail-Text",
        "password": "Passwort",
        "period": "Zeitraum",
    }

    def __init__(self, parent=None, initial_section: str = "mail"):
        super().__init__(parent)
        self.settings = load_settings()
        self.setWindowTitle("Einstellungen")
        self.resize(760, 760)

        root = QVBoxLayout(self)
        self.tabs = QTabWidget()
        root.addWidget(self.tabs)

        smtp_group = QGroupBox("SMTP / Absender")
        smtp_form = QFormLayout(smtp_group)

        smtp = self.settings["smtp"]
        self.mail_mode = QComboBox()
        mail_modes = ["smtp"]
        if sys.platform in {"darwin", "win32"}:
            mail_modes.append("outlook")
        self.mail_mode.addItems(mail_modes)
        self.mail_mode.setCurrentText(self.settings.get("mail_mode", "smtp"))

        self.smtp_server = QLineEdit(smtp.get("server", ""))
        self.smtp_port = QSpinBox()
        self.smtp_port.setRange(1, 65535)
        self.smtp_port.setValue(int(smtp.get("port", 587) or 587))
        self.smtp_security = QComboBox()
        self.smtp_security.addItems(["tls", "ssl", "none"])
        self.smtp_security.setCurrentText(smtp.get("security", "tls"))
        self.smtp_user = QLineEdit(smtp.get("username", ""))
        self.smtp_pass = QLineEdit(smtp.get("password", ""))
        self.smtp_pass.setEchoMode(QLineEdit.Password)
        self.smtp_timeout = QSpinBox()
        self.smtp_timeout.setRange(5, 300)
        self.smtp_timeout.setValue(int(smtp.get("timeout_sec", 30) or 30))
        self.from_email = QLineEdit(smtp.get("from_email", ""))
        self.from_name = QLineEdit(smtp.get("from_name", "Personalabteilung"))
        self.smtp_widgets = [
            self.smtp_server,
            self.smtp_port,
            self.smtp_security,
            self.smtp_user,
            self.smtp_pass,
            self.smtp_timeout,
        ]
        self.outlook_account_combo = QComboBox()
        self.outlook_account_combo.addItem("Automatisch (erstes Konto)", "")
        self.btn_refresh_outlook_accounts = QPushButton("Konten laden")
        outlook_account_row = QWidget()
        outlook_account_layout = QHBoxLayout(outlook_account_row)
        outlook_account_layout.setContentsMargins(0, 0, 0, 0)
        outlook_account_layout.addWidget(self.outlook_account_combo, 1)
        outlook_account_layout.addWidget(self.btn_refresh_outlook_accounts)

        smtp_form.addRow("Versandmethode", self.mail_mode)
        smtp_form.addRow("SMTP Server", self.smtp_server)
        smtp_form.addRow("SMTP Port", self.smtp_port)
        smtp_form.addRow("Sicherheit", self.smtp_security)
        smtp_form.addRow("SMTP Benutzer", self.smtp_user)
        smtp_form.addRow("SMTP Passwort", self.smtp_pass)
        smtp_form.addRow("Timeout (Sek.)", self.smtp_timeout)
        smtp_form.addRow("Absender E-Mail", self.from_email)
        smtp_form.addRow("Outlook Konto", outlook_account_row)
        smtp_form.addRow("Absender Name", self.from_name)
        self._add_settings_tab("mail", smtp_group)

        company_group = QGroupBox("Unternehmen")
        company_layout = QGridLayout(company_group)
        self.company_combo = QComboBox()
        self.company_id = QLineEdit()
        self.company_name = QLineEdit()
        self.company_excel_file = QLineEdit()
        self.btn_company_excel_file = QPushButton("Datei wählen")
        self.btn_new_company = QPushButton("Neu")
        self._loading_company_fields = False
        self._editing_company_id = None
        self.btn_delete_company = QPushButton("Löschen")

        for company in self.settings.get("companies", []):
            self.company_combo.addItem(company.get("name", ""), company.get("id", ""))

        idx = self.company_combo.findData(self.settings.get("selected_company_id", ""))
        if idx >= 0:
            self.company_combo.setCurrentIndex(idx)
        self._load_selected_company_into_fields()

        company_layout.addWidget(QLabel("Aktives Unternehmen"), 0, 0)
        company_layout.addWidget(self.company_combo, 0, 1, 1, 2)
        company_layout.addWidget(self.btn_new_company, 0, 3)
        company_layout.addWidget(self.btn_delete_company, 0, 4)
        company_layout.addWidget(QLabel("Unternehmens-ID"), 1, 0)
        company_layout.addWidget(self.company_id, 1, 1, 1, 4)
        company_layout.addWidget(QLabel("Unternehmensname"), 2, 0)
        company_layout.addWidget(self.company_name, 2, 1, 1, 4)
        company_excel_row = QHBoxLayout()
        company_excel_row.addWidget(self.company_excel_file)
        company_excel_row.addWidget(self.btn_company_excel_file)
        company_layout.addWidget(QLabel("Excel-Datei E-Mail-Adressen"), 3, 0)
        company_layout.addLayout(company_excel_row, 3, 1, 1, 4)
        self._add_settings_tab("companies", company_group)

        mail_group = QGroupBox("Mailtext")
        mail_layout = QVBoxLayout(mail_group)
        mail_form = QFormLayout()
        mail_text = self.settings["mail_text"]
        self.mail_subject = QLineEdit(mail_text.get("subject", ""))
        self.mail_body = QTextEdit()
        body_html = str(mail_text.get("body_html", "") or "").strip()
        if body_html:
            self.mail_body.setHtml(body_html)
        else:
            self.mail_body.setPlainText(mail_text.get("body", ""))
        mail_toolbar = QHBoxLayout()
        self.btn_mail_bold = QPushButton("Fett")
        self.btn_mail_italic = QPushButton("Kursiv")
        self.btn_mail_underline = QPushButton("Unterstr.")
        self.btn_mail_list = QPushButton("Liste")
        mail_toolbar.addWidget(self.btn_mail_bold)
        mail_toolbar.addWidget(self.btn_mail_italic)
        mail_toolbar.addWidget(self.btn_mail_underline)
        mail_toolbar.addWidget(self.btn_mail_list)
        mail_toolbar.addStretch(1)
        mail_toolbar_2 = QHBoxLayout()
        self.btn_mail_align_left = QPushButton("Links")
        self.btn_mail_align_center = QPushButton("Mitte")
        self.btn_mail_align_right = QPushButton("Rechts")
        self.mail_font_size = QSpinBox()
        self.mail_font_size.setRange(8, 48)
        self.mail_font_size.setValue(10)
        self.btn_mail_color = QPushButton("Farbe")
        mail_toolbar_2.addWidget(self.btn_mail_align_left)
        mail_toolbar_2.addWidget(self.btn_mail_align_center)
        mail_toolbar_2.addWidget(self.btn_mail_align_right)
        mail_toolbar_2.addWidget(QLabel("Größe"))
        mail_toolbar_2.addWidget(self.mail_font_size)
        mail_toolbar_2.addWidget(self.btn_mail_color)
        mail_toolbar_2.addStretch(1)
        mail_form.addRow("Betreff", self.mail_subject)
        mail_form.addRow("Text", self.mail_body)
        mail_layout.addLayout(mail_toolbar)
        mail_layout.addLayout(mail_toolbar_2)
        mail_layout.addLayout(mail_form)
        letter_container = QWidget()
        letter_root = QVBoxLayout(letter_container)
        letter_root.addWidget(mail_group)
        hint = QLabel(
            "Platzhalter im Mailtext: {persnr}, {monat}, {jahr}, {company_name}, {from_name}"
        )
        letter_root.addWidget(hint)
        letter_root.addStretch(1)
        self._add_settings_tab("letter", letter_container)

        pdf_group = QGroupBox("PDF / Passwort")
        pdf_form = QFormLayout(pdf_group)
        pdf_password = self.settings["pdf_password"]
        self.pdf_enabled = QCheckBox("PDF verschlüsseln")
        self.pdf_enabled.setChecked(bool(pdf_password.get("enabled", True)))
        self.pdf_prefix = QLineEdit(pdf_password.get("prefix", ""))
        self.pdf_suffix = QLineEdit(pdf_password.get("suffix", ""))
        pdf_form.addRow("", self.pdf_enabled)
        pdf_form.addRow("Passwort Prefix", self.pdf_prefix)
        pdf_form.addRow("Passwort Suffix", self.pdf_suffix)
        self._add_settings_tab("password", pdf_group)

        other_group = QGroupBox("Perioden / UI")
        other_form = QFormLayout(other_group)
        period = self.settings["period"]
        ui = self.settings["ui"]

        self.period_mode = QComboBox()
        self.period_mode.addItems([
            "automatic_current_month",
            "automatic_previous_month",
            "manual",
        ])
        saved_mode = str(period.get("mode", "automatic_current_month"))
        index = self.period_mode.findText(saved_mode)
        if index >= 0:
            self.period_mode.setCurrentIndex(index)
        else:
            self.period_mode.setCurrentIndex(0)

        self.period_month = QSpinBox()
        self.period_month.setRange(1, 12)
        self.period_month.setValue(int(period.get("month", 1) or 1))
        self.period_year = QSpinBox()
        self.period_year.setRange(2020, 2100)
        self.period_year.setValue(int(period.get("year", 2026) or 2026))
        self.dry_run_default = QCheckBox("Dry-Run standardmäßig aktiv")
        self.dry_run_default.setChecked(bool(ui.get("dry_run_default", True)))
        self.remember_paths = QCheckBox("Letzte Pfade merken")
        self.remember_paths.setChecked(bool(ui.get("remember_last_paths", True)))
        other_form.addRow("Periodenmodus", self.period_mode)
        other_form.addRow("Monat", self.period_month)
        other_form.addRow("Jahr", self.period_year)
        other_form.addRow("", self.dry_run_default)
        other_form.addRow("", self.remember_paths)
        self._add_settings_tab("period", other_group)

        buttons = QHBoxLayout()
        self.btn_preview = QPushButton("Vorschau")
        self.btn_test_mail = QPushButton("Test-E-Mail senden")
        self.btn_save = QPushButton("Speichern")
        self.btn_cancel = QPushButton("Abbrechen")
        buttons.addStretch(1)
        buttons.addWidget(self.btn_preview)
        buttons.addWidget(self.btn_test_mail)
        buttons.addWidget(self.btn_save)
        buttons.addWidget(self.btn_cancel)
        root.addLayout(buttons)

        self.company_combo.currentIndexChanged.connect(self._company_selection_changed)
        self.btn_company_excel_file.clicked.connect(self._choose_company_excel_file)
        self.btn_new_company.clicked.connect(self._add_company)
        self.btn_delete_company.clicked.connect(self._delete_company)
        self.btn_mail_bold.clicked.connect(self._toggle_mail_bold)
        self.btn_mail_italic.clicked.connect(self._toggle_mail_italic)
        self.btn_mail_underline.clicked.connect(self._toggle_mail_underline)
        self.btn_mail_list.clicked.connect(self._toggle_mail_list)
        self.btn_mail_align_left.clicked.connect(lambda: self._set_mail_alignment(Qt.AlignLeft))
        self.btn_mail_align_center.clicked.connect(lambda: self._set_mail_alignment(Qt.AlignHCenter))
        self.btn_mail_align_right.clicked.connect(lambda: self._set_mail_alignment(Qt.AlignRight))
        self.mail_font_size.valueChanged.connect(self._set_mail_font_size)
        self.btn_mail_color.clicked.connect(self._choose_mail_color)
        self.btn_preview.clicked.connect(self.open_mail_preview)
        self.btn_test_mail.clicked.connect(self.send_test_mail)
        self.btn_save.clicked.connect(self._save)
        self.btn_cancel.clicked.connect(self.reject)
        self.mail_mode.currentTextChanged.connect(self._update_mail_mode_state)
        self.outlook_account_combo.currentIndexChanged.connect(self._apply_selected_outlook_account)
        self.btn_refresh_outlook_accounts.clicked.connect(
            lambda: self._refresh_outlook_accounts(show_message=True)
        )
        self._update_mail_mode_state()
        self.set_initial_section(initial_section)

    def _add_settings_tab(self, section_key: str, content_widget: QWidget):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(content_widget)
        layout.addStretch(1)
        self.tabs.addTab(page, self.SECTION_TITLES[section_key])

    def set_initial_section(self, section_key: str):
        title = self.SECTION_TITLES.get(section_key, self.SECTION_TITLES["mail"])
        for index in range(self.tabs.count()):
            if self.tabs.tabText(index) == title:
                self.tabs.setCurrentIndex(index)
                break

    def _is_outlook_mode(self) -> bool:
        return str(self.mail_mode.currentText() or "").strip().lower() == "outlook"

    def _populate_outlook_account_combo(self, accounts: list[dict[str, str]]) -> None:
        current_value = self.from_email.text().strip()
        self.outlook_account_combo.blockSignals(True)
        try:
            self.outlook_account_combo.clear()
            self.outlook_account_combo.addItem("Automatisch (erstes Konto)", "")
            matched_index = 0
            seen: set[str] = set()

            for account in accounts:
                identifier = str(account.get("identifier", "") or "").strip()
                label = str(account.get("label", identifier) or identifier).strip()
                smtp_address = str(account.get("smtp_address", "") or "").strip().lower()
                display_name = str(account.get("display_name", "") or "").strip().lower()
                if not identifier:
                    continue
                normalized_identifier = identifier.lower()
                if normalized_identifier in seen:
                    continue
                seen.add(normalized_identifier)
                self.outlook_account_combo.addItem(label, identifier)
                if current_value and current_value.lower() in {
                    normalized_identifier,
                    smtp_address,
                    display_name,
                }:
                    matched_index = self.outlook_account_combo.count() - 1

            if current_value and matched_index == 0:
                self.outlook_account_combo.addItem(f"Manuell: {current_value}", current_value)
                matched_index = self.outlook_account_combo.count() - 1

            self.outlook_account_combo.setCurrentIndex(matched_index)
        finally:
            self.outlook_account_combo.blockSignals(False)

    def _refresh_outlook_accounts(self, *, show_message: bool = False) -> None:
        if sys.platform != "win32":
            self._populate_outlook_account_combo([])
            return

        try:
            from core.mailer import list_outlook_accounts

            accounts = list_outlook_accounts()
        except Exception as exc:
            self._populate_outlook_account_combo([])
            if show_message:
                QMessageBox.warning(self, "Outlook-Konten", str(exc))
            return

        self._populate_outlook_account_combo(accounts)
        if not show_message:
            return

        if accounts:
            QMessageBox.information(
                self,
                "Outlook-Konten",
                f"{len(accounts)} Outlook-Konto/Konten wurden geladen.",
            )
        else:
            QMessageBox.information(
                self,
                "Outlook-Konten",
                "Es wurden keine Outlook-Konten gefunden. "
                "Die Absenderadresse kann weiterhin manuell eingetragen werden.",
            )

    def _apply_selected_outlook_account(self, *_args) -> None:
        selected_value = str(self.outlook_account_combo.currentData() or "").strip()
        if selected_value:
            self.from_email.setText(selected_value)
            return

        if self._is_outlook_mode():
            self.from_email.clear()

    def _update_mail_mode_state(self, *_args) -> None:
        is_outlook = self._is_outlook_mode()
        for widget in self.smtp_widgets:
            widget.setEnabled(not is_outlook)

        can_load_accounts = is_outlook and sys.platform == "win32"
        self.outlook_account_combo.setEnabled(can_load_accounts)
        self.btn_refresh_outlook_accounts.setEnabled(can_load_accounts)
        self.from_email.setPlaceholderText(
            "Outlook-Absenderadresse oder Kontoname" if is_outlook else ""
        )

        if can_load_accounts and self.outlook_account_combo.count() <= 1:
            self._refresh_outlook_accounts(show_message=False)

    def _companies(self) -> list[dict]:
        companies = self.settings.get("companies", [])
        if not companies:
            companies = [{"id": "gesob", "name": "GeSoB GmbH", "email_excel_file": ""}]
            self.settings["companies"] = companies
        return companies

    def _load_selected_company_into_fields(self):
        current_id = self.company_combo.currentData()
        company = None
        for item in self._companies():
            if item.get("id") == current_id:
                company = item
                break
        if company is None and self._companies():
            company = self._companies()[0]
        self._loading_company_fields = True
        try:
            self.company_id.setText(company.get("id", "") if company else "")
            self.company_name.setText(company.get("name", "") if company else "")
            self.company_excel_file.setText(company.get("email_excel_file", "") if company else "")
            self._editing_company_id = company.get("id", "") if company else None
        finally:
            self._loading_company_fields = False

    def _company_selection_changed(self):
        if self._loading_company_fields:
            return
        self._store_company_fields(self._editing_company_id)
        self._load_selected_company_into_fields()

    def _store_company_fields(self, current_id: str | None):
        new_id = self.company_id.text().strip() or current_id or "company"
        new_name = self.company_name.text().strip() or new_id
        new_email_excel_file = self.company_excel_file.text().strip()

        companies = self._companies()
        for item in companies:
            if item.get("id") == current_id:
                item["id"] = new_id
                item["name"] = new_name
                item["email_excel_file"] = new_email_excel_file
                break
        else:
            companies.append({
                "id": new_id,
                "name": new_name,
                "email_excel_file": new_email_excel_file,
            })

        return new_id

    def _store_current_company_fields(self):
        new_id = self._store_company_fields(self.company_combo.currentData())

        self._reload_company_combo(selected_id=new_id)

    def _reload_company_combo(self, selected_id: str | None = None):
        self.company_combo.blockSignals(True)
        self.company_combo.clear()
        for company in self._companies():
            self.company_combo.addItem(company.get("name", ""), company.get("id", ""))
        if selected_id:
            idx = self.company_combo.findData(selected_id)
            if idx >= 0:
                self.company_combo.setCurrentIndex(idx)
        self.company_combo.blockSignals(False)
        self._load_selected_company_into_fields()

    def _add_company(self):
        self._store_current_company_fields()
        new_id = "company_new"
        suffix = 1
        existing_ids = {c.get("id") for c in self._companies()}
        while new_id in existing_ids:
            suffix += 1
            new_id = f"company_new_{suffix}"
        self._companies().append({
            "id": new_id,
            "name": "Neues Unternehmen",
            "email_excel_file": "",
        })
        self._reload_company_combo(selected_id=new_id)

    def _initial_company_excel_dir(self) -> str:
        candidates = [
            self.company_excel_file.text().strip(),
            self.settings.get("ui", {}).get("last_excel_file", ""),
        ]
        for candidate in candidates:
            if not candidate:
                continue
            path = Path(candidate)
            if path.is_file():
                return str(path.parent)
            if path.parent.is_dir():
                return str(path.parent)
        return ""

    def _choose_company_excel_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Excel-Datei wählen",
            self._initial_company_excel_dir(),
            "Excel Dateien (*.xlsx *.xlsm)",
        )
        if file_path:
            self.company_excel_file.setText(file_path)

    def _delete_company(self):
        if len(self._companies()) <= 1:
            QMessageBox.warning(self, "Nicht möglich", "Mindestens ein Unternehmen muss erhalten bleiben.")
            return
        current_id = self.company_combo.currentData()
        self.settings["companies"] = [c for c in self._companies() if c.get("id") != current_id]
        self._reload_company_combo(selected_id=self.settings["companies"][0].get("id"))

    def _persist_settings(self, *, show_message: bool, close_dialog: bool):
        self._store_current_company_fields()

        self.settings["mail_mode"] = self.mail_mode.currentText()
        self.settings["selected_company_id"] = self.company_combo.currentData() or ""

        self.settings["smtp"]["server"] = self.smtp_server.text().strip()
        self.settings["smtp"]["port"] = int(self.smtp_port.value())
        self.settings["smtp"]["security"] = self.smtp_security.currentText()
        self.settings["smtp"]["username"] = self.smtp_user.text().strip()
        self.settings["smtp"]["password"] = self.smtp_pass.text()
        self.settings["smtp"]["timeout_sec"] = int(self.smtp_timeout.value())
        self.settings["smtp"]["from_email"] = self.from_email.text().strip()
        self.settings["smtp"]["from_name"] = self.from_name.text().strip() or "Personalabteilung"

        self.settings["mail_text"]["subject"] = self.mail_subject.text()
        self.settings["mail_text"]["body"] = self.mail_body.toPlainText()
        self.settings["mail_text"]["body_html"] = self.mail_body.toHtml()

        self.settings["pdf_password"]["enabled"] = self.pdf_enabled.isChecked()
        self.settings["pdf_password"]["prefix"] = self.pdf_prefix.text()
        self.settings["pdf_password"]["suffix"] = self.pdf_suffix.text()

        self.settings["period"]["mode"] = self.period_mode.currentText()
        self.settings["period"]["month"] = int(self.period_month.value())
        self.settings["period"]["year"] = int(self.period_year.value())
        self.settings["ui"]["dry_run_default"] = self.dry_run_default.isChecked()
        self.settings["ui"]["remember_last_paths"] = self.remember_paths.isChecked()

        save_settings(self.settings)
        if show_message:
            QMessageBox.information(self, "Gespeichert", "Einstellungen wurden gespeichert.")
        if close_dialog:
            self.accept()

    def _merge_mail_format(self, format_update: QTextCharFormat):
        cursor = self.mail_body.textCursor()
        if not cursor.hasSelection():
            cursor.select(QTextCursor.WordUnderCursor)
        cursor.mergeCharFormat(format_update)
        self.mail_body.mergeCurrentCharFormat(format_update)
        self.mail_body.setFocus()

    def _toggle_mail_bold(self):
        fmt = QTextCharFormat()
        current_weight = self.mail_body.fontWeight()
        fmt.setFontWeight(QFont.Normal if current_weight >= QFont.Bold else QFont.Bold)
        self._merge_mail_format(fmt)

    def _toggle_mail_italic(self):
        fmt = QTextCharFormat()
        fmt.setFontItalic(not self.mail_body.fontItalic())
        self._merge_mail_format(fmt)

    def _toggle_mail_underline(self):
        fmt = QTextCharFormat()
        fmt.setFontUnderline(not self.mail_body.fontUnderline())
        self._merge_mail_format(fmt)

    def _toggle_mail_list(self):
        cursor = self.mail_body.textCursor()
        cursor.beginEditBlock()
        current_list = cursor.currentList()
        if current_list is not None:
            block_fmt = cursor.blockFormat()
            block_fmt.setIndent(0)
            cursor.setBlockFormat(block_fmt)
        else:
            list_fmt = QTextListFormat()
            list_fmt.setStyle(QTextListFormat.ListDisc)
            cursor.createList(list_fmt)
        cursor.endEditBlock()
        self.mail_body.setTextCursor(cursor)
        self.mail_body.setFocus()

    def _set_mail_alignment(self, alignment):
        self.mail_body.setAlignment(alignment)
        self.mail_body.setFocus()

    def _set_mail_font_size(self, size: int):
        fmt = QTextCharFormat()
        fmt.setFontPointSize(float(size))
        self._merge_mail_format(fmt)

    def _choose_mail_color(self):
        color = QColorDialog.getColor(self.mail_body.textColor(), self, "Textfarbe wählen")
        if not color.isValid():
            return
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        self._merge_mail_format(fmt)

    def _preview_settings(self) -> dict:
        preview_settings = load_settings()
        preview_settings["mail_mode"] = self.mail_mode.currentText()
        preview_settings["selected_company_id"] = self.company_combo.currentData() or ""
        preview_settings["smtp"]["server"] = self.smtp_server.text().strip()
        preview_settings["smtp"]["port"] = int(self.smtp_port.value())
        preview_settings["smtp"]["security"] = self.smtp_security.currentText()
        preview_settings["smtp"]["username"] = self.smtp_user.text().strip()
        preview_settings["smtp"]["password"] = self.smtp_pass.text()
        preview_settings["smtp"]["timeout_sec"] = int(self.smtp_timeout.value())
        preview_settings["smtp"]["from_email"] = self.from_email.text().strip()
        preview_settings["smtp"]["from_name"] = self.from_name.text().strip() or "Personalabteilung"
        preview_settings["mail_text"]["subject"] = self.mail_subject.text()
        preview_settings["mail_text"]["body"] = self.mail_body.toPlainText()
        preview_settings["mail_text"]["body_html"] = self.mail_body.toHtml()
        preview_settings["pdf_password"]["enabled"] = self.pdf_enabled.isChecked()
        preview_settings["pdf_password"]["prefix"] = self.pdf_prefix.text()
        preview_settings["pdf_password"]["suffix"] = self.pdf_suffix.text()
        preview_settings["period"]["mode"] = self.period_mode.currentText()
        preview_settings["period"]["month"] = int(self.period_month.value())
        preview_settings["period"]["year"] = int(self.period_year.value())
        return preview_settings

    def _mail_preview_context(self) -> dict[str, str | int]:
        preview_settings = self._preview_settings()
        return build_mail_context(
            preview_settings,
            "10001",
            company_id=str(preview_settings.get("selected_company_id", "") or "").strip() or None,
            company_name=self.company_name.text().strip() or None,
        )

    def open_mail_preview(self):
        context = self._mail_preview_context()
        try:
            subject = format_message_template(self.mail_subject.text(), context)
            body_text = format_message_template(self.mail_body.toPlainText(), context)
            body_html = format_message_template(self.mail_body.toHtml(), context)
        except ValueError as exc:
            QMessageBox.warning(self, "Vorschau nicht möglich", str(exc))
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Mail-Vorschau")
        dialog.resize(760, 640)

        layout = QVBoxLayout(dialog)
        form = QFormLayout()
        form.addRow("An", QLabel("max.mustermann@example.com"))
        form.addRow("Betreff", QLabel(subject))
        layout.addLayout(form)

        preview = QTextEdit()
        preview.setReadOnly(True)
        preview.setHtml(body_html)
        layout.addWidget(preview)

        plain_text = QTextEdit()
        plain_text.setReadOnly(True)
        plain_text.setPlainText(body_text)
        form.addRow("Text-Version", plain_text)

        close_row = QHBoxLayout()
        close_row.addStretch(1)
        btn_close = QPushButton("Schließen")
        btn_close.clicked.connect(dialog.accept)
        close_row.addWidget(btn_close)
        layout.addLayout(close_row)
        dialog.exec()

    def _create_test_pdf(self) -> Path:
        from PyPDF2 import PdfWriter

        test_dir = GESOB_DIR / "_test_mail"
        test_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = test_dir / "test_attachment.pdf"

        writer = PdfWriter()
        writer.add_blank_page(width=595, height=842)
        with pdf_path.open("wb") as f:
            writer.write(f)

        return pdf_path

    def send_test_mail(self):
        to_email, ok = QInputDialog.getText(
            self,
            "Test-E-Mail senden",
            "Empfängeradresse:",
            text=self.from_email.text().strip(),
        )
        to_email = to_email.strip()
        if not ok:
            return
        if not to_email:
            QMessageBox.warning(self, "Fehler", "Bitte eine E-Mail-Adresse eingeben.")
            return

        settings = self._preview_settings()
        context = self._mail_preview_context()
        mail_mode = str(settings.get("mail_mode", "smtp") or "smtp").strip().lower()
        subject_template = str(settings.get("mail_text", {}).get("subject", "") or "")
        body_template = str(settings.get("mail_text", {}).get("body", "") or "")
        body_html_template = str(settings.get("mail_text", {}).get("body_html", "") or "")

        try:
            subject = format_message_template(subject_template, context)
            body = format_message_template(body_template, context)
            body_html = format_message_template(body_html_template, context) if body_html_template else ""
            attachment_path = self._create_test_pdf()

            if mail_mode == "smtp":
                from core.mailer import send_email_with_attachment, test_smtp_connection

                test_smtp_connection(settings["smtp"])
                send_email_with_attachment(
                    smtp_settings=settings["smtp"],
                    to_email=to_email,
                    subject=subject,
                    body=body,
                    attachment_path=attachment_path,
                    html_body=body_html,
                )
            elif mail_mode == "outlook":
                from core.mailer import send_outlook_email_with_attachment, test_outlook_connection

                from_email = str(settings.get("smtp", {}).get("from_email", "") or "").strip()
                test_outlook_connection(from_email)
                send_outlook_email_with_attachment(
                    to_email=to_email,
                    subject=subject,
                    body=body,
                    attachment_path=attachment_path,
                    from_email=from_email,
                    html_body=body_html,
                )
            else:
                raise ValueError(f"Unbekannte Versandmethode: {mail_mode}")

            QMessageBox.information(
                self,
                "Test-E-Mail",
                f"Test-E-Mail wurde an {to_email} gesendet.",
            )
        except Exception as exc:
            QMessageBox.critical(self, "Test-E-Mail fehlgeschlagen", str(exc))

    def _save(self):
        self._persist_settings(show_message=True, close_dialog=True)

    def reject(self):
        super().reject()


class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Hilfe - Help")
        self.resize(920, 760)

        layout = QVBoxLayout(self)
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setHtml(build_help_html())
        layout.addWidget(browser)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_close = QPushButton("Schlie\u00dfen")
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)



class SupportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Technischer Support")
        self.resize(520, 280)

        layout = QVBoxLayout(self)
        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(
            "Technischer Support\n\n"
            "Bei Fragen zur Einrichtung, zu Versandfehlern oder zur Nutzung des Programms "
            "wenden Sie sich bitte an den verantwortlichen Administrator oder an den technischen Support Ihres Unternehmens.\n\n"
            "Die Kontaktdaten koennen hier spaeter noch ergaenzt werden."
        )
        layout.addWidget(text)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_close = QPushButton("Schließen")
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)


class SendPreviewDialog(QDialog):
    def __init__(self, summary_lines: list[str], rows: list[dict], subject_preview: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Versand-Vorschau")
        self.resize(980, 680)

        layout = QVBoxLayout(self)

        info = QTextEdit()
        info.setReadOnly(True)
        info.setPlainText("\n".join(summary_lines + ["", f"Betreff: {subject_preview}"]))
        layout.addWidget(info)

        table = QTableWidget(len(rows), 5)
        table.setHorizontalHeaderLabels(["PersNr", "Name, Vorname", "E-Mail", "Anhang", "Quell-PDFs"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        for row_index, row in enumerate(rows):
            values = [
                str(row.get("PersNr", "")),
                format_name_vorname_row(row),
                str(row.get("Email", "")),
                str(row.get("AttachmentPreview", "")),
                str(row.get("Files", "")),
            ]
            for col_index, value in enumerate(values):
                table.setItem(row_index, col_index, QTableWidgetItem(value))
        layout.addWidget(table)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_cancel = QPushButton("Abbrechen")
        btn_continue = QPushButton("Versand starten")
        btn_cancel.clicked.connect(self.reject)
        btn_continue.clicked.connect(self.accept)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_continue)
        layout.addLayout(btn_row)

class MassMessagePreviewDialog(QDialog):
    def __init__(
        self,
        company_name: str,
        excel_path: Path,
        subject_preview: str,
        body_preview: str,
        rows: list[dict],
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Nachricht-Vorschau")
        self.resize(900, 650)

        layout = QVBoxLayout(self)

        info = QTextEdit()
        info.setReadOnly(True)
        info.setPlainText(
            "\n".join([
                f"Unternehmen: {company_name or '-'}",
                f"Excel-Datei: {excel_path}",
                f"EmpfÃ¤nger: {len(rows)}",
                "",
                f"Betreff: {subject_preview}",
                "",
                "Nachricht:",
                body_preview,
            ])
        )
        layout.addWidget(info)

        table = QTableWidget(len(rows), 3)
        table.setHorizontalHeaderLabels(["PersNr", "Name, Vorname", "E-Mail"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        for row_index, row in enumerate(rows):
            table.setItem(row_index, 0, QTableWidgetItem(str(row.get("PersNr", ""))))
            table.setItem(row_index, 1, QTableWidgetItem(format_name_vorname_row(row)))
            table.setItem(row_index, 2, QTableWidgetItem(str(row.get("Email", ""))))
        layout.addWidget(table)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_cancel = QPushButton("Abbrechen")
        btn_continue = QPushButton("Nachricht senden")
        btn_cancel.clicked.connect(self.reject)
        btn_continue.clicked.connect(self.accept)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_continue)
        layout.addLayout(btn_row)


class MassMessageDialog(QDialog):
    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.request: dict | None = None
        self.setWindowTitle("Nachricht senden")
        self.resize(780, 560)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.company_combo = QComboBox()
        for company in self.settings.get("companies", []):
            self.company_combo.addItem(company.get("name", ""), company.get("id", ""))
        selected_id = self.settings.get("selected_company_id", "")
        selected_index = self.company_combo.findData(selected_id)
        if selected_index >= 0:
            self.company_combo.setCurrentIndex(selected_index)

        self.excel_file = QLineEdit()
        self.excel_file.setReadOnly(True)
        self.btn_choose_excel_file = QPushButton("Datei wählen")
        self.subject = QLineEdit()
        self.body = QTextEdit()

        form.addRow("Unternehmen", self.company_combo)
        excel_row = QHBoxLayout()
        excel_row.addWidget(self.excel_file)
        excel_row.addWidget(self.btn_choose_excel_file)
        form.addRow("Excel-Datei", excel_row)
        form.addRow("Betreff", self.subject)
        form.addRow("Nachricht", self.body)
        layout.addLayout(form)

        hint = QLabel(
            "Platzhalter: {persnr}, {monat}, {jahr}, {company_name}, {from_name}"
        )
        layout.addWidget(hint)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_cancel = QPushButton("Abbrechen")
        btn_preview = QPushButton("Vorschau")
        btn_cancel.clicked.connect(self.reject)
        btn_preview.clicked.connect(self._preview)
        self.btn_choose_excel_file.clicked.connect(self._choose_excel_file)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_preview)
        layout.addLayout(btn_row)

        self.company_combo.currentIndexChanged.connect(self._update_excel_file)
        self._update_excel_file()

    def _selected_company_id(self) -> str:
        return str(self.company_combo.currentData() or "").strip()

    def _selected_excel_file(self) -> str:
        return get_company_email_excel_file(self.settings, self._selected_company_id())

    def _update_excel_file(self):
        self.excel_file.setText(self._selected_excel_file())

    def _initial_excel_dir(self) -> str:
        candidates = [
            self.excel_file.text().strip(),
            self._selected_excel_file(),
            self.settings.get("ui", {}).get("last_excel_file", ""),
        ]
        for candidate in candidates:
            if not candidate:
                continue
            path = Path(candidate)
            if path.is_file():
                return str(path.parent)
            if path.parent.is_dir():
                return str(path.parent)
        return ""

    def _choose_excel_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Excel-Datei wählen",
            self._initial_excel_dir(),
            "Excel Dateien (*.xlsx *.xlsm)",
        )
        if file_path:
            self.excel_file.setText(file_path)

    def _preview_context(self, persnr: str) -> dict[str, str | int]:
        return build_mail_context(self.settings, persnr, company_id=self._selected_company_id())

    def _preview(self):
        company_id = self._selected_company_id()
        subject = self.subject.text().strip()
        body = self.body.toPlainText()
        excel_path = Path(self.excel_file.text().strip())

        if not company_id:
            QMessageBox.warning(self, "Fehler", "Bitte ein Unternehmen auswÃ¤hlen.")
            return
        if not excel_path.is_file():
            QMessageBox.warning(
                self,
                "Fehler",
                "FÃ¼r dieses Unternehmen ist keine gÃ¼ltige Excel-Datei hinterlegt.",
            )
            return
        if not subject:
            QMessageBox.warning(self, "Fehler", "Bitte einen Betreff eingeben.")
            return
        if not body.strip():
            QMessageBox.warning(self, "Fehler", "Bitte eine Nachricht eingeben.")
            return

        try:
            rows = load_mass_message_rows(excel_path)
        except Exception as exc:
            QMessageBox.critical(self, "Excel-Datei", str(exc))
            return

        if not rows:
            QMessageBox.warning(self, "Fehler", "In der Excel-Datei wurden keine E-Mail-Adressen gefunden.")
            return

        sample_persnr = str(rows[0].get("PersNr", ""))
        context = self._preview_context(sample_persnr)
        try:
            subject_preview = format_message_template(subject, context)
            body_preview = format_message_template(body, context)
        except ValueError as exc:
            QMessageBox.warning(self, "Vorschau nicht möglich", str(exc))
            return

        preview = MassMessagePreviewDialog(
            company_name=str(context.get("company_name", "")),
            excel_path=excel_path,
            subject_preview=subject_preview,
            body_preview=body_preview,
            rows=rows,
            parent=self,
        )
        if preview.exec() != QDialog.Accepted:
            return

        request_settings = self.settings.copy()
        request_settings["selected_company_id"] = company_id
        self.request = {
            "settings": request_settings,
            "company_id": company_id,
            "company_name": str(context.get("company_name", "")),
            "excel_path": str(excel_path),
            "subject": subject,
            "body": body,
            "recipients": rows,
        }
        self.accept()


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
    ):
        super().__init__()
        self.settings = settings
        self.company_id = company_id
        self.subject_template = subject_template
        self.body_template = body_template
        self.recipients = recipients

    def run(self):
        try:
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
            self.error.emit(str(exc))


class Worker(QObject):
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
    ):
        super().__init__()
        self.mode = mode
        self.pdf_input = pdf_input
        self.excel_path = excel_path
        self.settings = settings
        self.dry_run = dry_run
        self.selected_persnr = selected_persnr

    def run(self):
        try:
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
            self.error.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = load_settings()
        self._company_combo_updating = False
        self._pending_send_request: dict | None = None
        self.worker_thread: QThread | None = None
        self.worker: Worker | None = None
        self.all_table_rows: list[dict] = []
        self.last_audit_path: str = ""
        self.last_missing_pdf_path: str = ""
        self.last_send_report_path: str = ""

        self.setWindowTitle(APP_NAME)
        self.resize(
            int(self.settings.get("ui", {}).get("window_width", 1100)),
            int(self.settings.get("ui", {}).get("window_height", 720)),
        )

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.addWidget(QLabel(APP_TAGLINE))
        self._create_menu_bar()

        form = QFormLayout()
        self.input_mode_combo = QComboBox()
        self.input_mode_combo.addItem("PDF-Ordner mit fertigen Dateien", "folder")
        self.input_mode_combo.addItem("Eine Gesamt-PDF zum Aufteilen", "single_pdf")
        saved_input_mode = str(self.settings.get("ui", {}).get("last_pdf_input_mode", "folder") or "folder")
        input_mode_index = self.input_mode_combo.findData(saved_input_mode)
        if input_mode_index >= 0:
            self.input_mode_combo.setCurrentIndex(input_mode_index)

        self.pdf_input_edit = QLineEdit(self.settings.get("ui", {}).get("last_pdf_dir", ""))
        initial_excel_file = get_company_email_excel_file(self.settings, self.settings.get("selected_company_id"))
        self.excel_file_edit = QLineEdit(initial_excel_file)

        btn_pdf = QPushButton("Ordner wählen")
        btn_excel = QPushButton("Datei wählen")
        self.btn_pdf_select = btn_pdf
        btn_pdf.clicked.connect(self.choose_pdf_input)
        btn_excel.clicked.connect(self.choose_excel_file)

        pdf_row = QHBoxLayout()
        form.addRow("Eingabemodus", self.input_mode_combo)

        pdf_row.addWidget(self.pdf_input_edit)
        pdf_row.addWidget(btn_pdf)
        form.addRow("PDF-Quelle", pdf_row)

        excel_row = QHBoxLayout()
        excel_row.addWidget(self.excel_file_edit)
        excel_row.addWidget(btn_excel)
        form.addRow("Excel-Datei", excel_row)

        self.company_combo = QComboBox()
        self.active_company_label = QLabel()
        self.reload_company_combo()
        form.addRow("Unternehmen", self.company_combo)
        form.addRow("Aktiv", self.active_company_label)

        self.dry_run_checkbox = QCheckBox("Dry-Run (PDF erstellen, aber keine E-Mails senden)")
        self.dry_run_checkbox.setChecked(bool(self.settings.get("ui", {}).get("dry_run_default", True)))
        form.addRow("", self.dry_run_checkbox)
        root.addLayout(form)

        btn_row = QHBoxLayout()
        self.btn_check = QPushButton("Adressen prüfen")
        self.btn_send = QPushButton("E-Mails senden")
        self.btn_send_selected = QPushButton("Nur ausgewählte senden")

        btn_row.addWidget(self.btn_check)
        btn_row.addWidget(self.btn_send)
        btn_row.addWidget(self.btn_send_selected)
        btn_row.addStretch(1)
        root.addLayout(btn_row)

        filter_row = QHBoxLayout()
        self.search_persnr_edit = QLineEdit()
        self.search_email_edit = QLineEdit()
        self.status_filter_combo = QComboBox()
        self.status_filter_combo.addItems([
            "Alle",
            "OK",
            "Keine E-Mail",
            "Keine Dateien",
            "Fehler",
            "Dry-Run",
            "Gesendet",
        ])
        self.btn_select_all = QPushButton("Alle markieren")
        self.btn_select_none = QPushButton("Alle abwählen")
        self.btn_clear_filters = QPushButton("Filter zurücksetzen")

        self.search_persnr_edit.setPlaceholderText("Suche PersNr")
        self.search_email_edit.setPlaceholderText("Suche E-Mail")

        filter_row.addWidget(QLabel("PersNr"))
        filter_row.addWidget(self.search_persnr_edit)
        filter_row.addWidget(QLabel("E-Mail"))
        filter_row.addWidget(self.search_email_edit)
        filter_row.addWidget(QLabel("Status"))
        filter_row.addWidget(self.status_filter_combo)
        filter_row.addWidget(self.btn_select_all)
        filter_row.addWidget(self.btn_select_none)
        filter_row.addWidget(self.btn_clear_filters)
        root.addLayout(filter_row)

        self.table = QTableWidget(0, 10)
        self.table.setHorizontalHeaderLabels([
            "Auswahl",
            "PersNr",
            "Name, Vorname",
            "E-Mail",
            "Dateien",
            "Anzahl",
            "Status",
            "Anhang",
            "Passwort",
            "Fehler",
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        root.addWidget(self.table)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        root.addWidget(self.log)

        self.btn_check.clicked.connect(lambda: self.start_job("check"))
        self.btn_send.clicked.connect(lambda: self.start_job("send"))
        self.btn_send_selected.clicked.connect(self.start_selected_send)
        self.company_combo.currentIndexChanged.connect(self._company_changed)
        self.input_mode_combo.currentIndexChanged.connect(self._update_pdf_input_ui)
        self.search_persnr_edit.textChanged.connect(self.apply_table_filters)
        self.search_email_edit.textChanged.connect(self.apply_table_filters)
        self.status_filter_combo.currentIndexChanged.connect(self.apply_table_filters)
        self.btn_select_all.clicked.connect(lambda: self.set_all_checkboxes(True))
        self.btn_select_none.clicked.connect(lambda: self.set_all_checkboxes(False))
        self.btn_clear_filters.clicked.connect(self.clear_table_filters)
        self.table.itemChanged.connect(self._on_table_item_changed)
        self._update_pdf_input_ui()

        settings_warning = consume_settings_warning()
        if settings_warning:
            self.append_log(f"WARNUNG: {settings_warning}")
            QMessageBox.warning(self, "Einstellungen", settings_warning)

    def _create_menu_bar(self):
        menu_bar = QMenuBar(self)
        self.setMenuBar(menu_bar)

        settings_menu = menu_bar.addMenu("Einstellungen")
        self._add_menu_action(settings_menu, "E-Mail-Einstellungen", lambda: self.open_settings("mail"))
        self._add_menu_action(settings_menu, "Unternehmen", lambda: self.open_settings("companies"))
        self._add_menu_action(settings_menu, "E-Mail-Text", lambda: self.open_settings("letter"))
        self._add_menu_action(settings_menu, "Passwort", lambda: self.open_settings("password"))
        self._add_menu_action(settings_menu, "Zeitraum", lambda: self.open_settings("period"))

        message_menu = menu_bar.addMenu("Nachricht")
        self.action_mass_message = self._add_menu_action(
            message_menu,
            "Nachricht senden",
            self.open_mass_message_dialog,
        )

        reports_menu = menu_bar.addMenu("Berichte")
        self.action_open_audit = self._add_menu_action(
            reports_menu,
            "audit_check.xlsx öffnen",
            self.open_audit_file,
        )
        self.action_open_missing_pdf = self._add_menu_action(
            reports_menu,
            "ohne_email_gesamt.pdf öffnen",
            self.open_missing_pdf_file,
        )
        self.action_open_send_report = self._add_menu_action(
            reports_menu,
            "send_report.xlsx öffnen",
            self.open_send_report_file,
        )
        self.action_open_audit.setEnabled(False)
        self.action_open_missing_pdf.setEnabled(False)
        self.action_open_send_report.setEnabled(False)

        help_menu = menu_bar.addMenu("Hilfe")
        self._add_menu_action(help_menu, "Help", self.open_help)
        self._add_menu_action(help_menu, "Technischer Support", self.open_support)

    def _add_menu_action(self, menu, title: str, handler):
        action = QAction(title, self)
        action.triggered.connect(handler)
        menu.addAction(action)
        return action

    def reload_company_combo(self):
        self._company_combo_updating = True
        self.company_combo.blockSignals(True)
        try:
            self.company_combo.clear()
            selected_id = self.settings.get("selected_company_id", "")
            for company in self.settings.get("companies", []):
                self.company_combo.addItem(company.get("name", ""), company.get("id", ""))

            idx = self.company_combo.findData(selected_id)
            if idx < 0 and self.company_combo.count() > 0:
                idx = 0
                self.settings["selected_company_id"] = self.company_combo.itemData(0) or ""

            if idx >= 0:
                self.company_combo.setCurrentIndex(idx)
        finally:
            self.company_combo.blockSignals(False)
            self._company_combo_updating = False

        self._update_active_company_label()
        self._apply_company_excel_file()

    def _current_company_email_excel_file(self, company_id: str | None = None) -> str:
        target_id = company_id or self.company_combo.currentData() or self.settings.get("selected_company_id", "")
        return get_company_email_excel_file(self.settings, target_id)

    def _set_company_email_excel_file(self, excel_file: str, company_id: str | None = None):
        target_id = str(company_id or self.company_combo.currentData() or self.settings.get("selected_company_id", "") or "").strip()
        if not target_id:
            return
        for company in self.settings.get("companies", []):
            if not isinstance(company, dict):
                continue
            if str(company.get("id", "") or "").strip() == target_id:
                company["email_excel_file"] = excel_file.strip()
                return

    def _apply_company_excel_file(self):
        if not hasattr(self, "excel_file_edit"):
            return
        self.excel_file_edit.setText(self._current_company_email_excel_file())

    def _update_active_company_label(self):
        if not hasattr(self, "active_company_label"):
            return
        company_id = self.company_combo.currentData() or self.settings.get("selected_company_id", "")
        company_name = get_company_name(self.settings, company_id) or "-"
        company_id = company_id or "-"
        self.active_company_label.setText(f"{company_name} ({company_id})")

    def _company_changed(self):
        if self._company_combo_updating:
            return
        previous_company_id = self.settings.get("selected_company_id", "")
        self._set_company_email_excel_file(self.excel_file_edit.text().strip(), previous_company_id)
        self.settings["selected_company_id"] = self.company_combo.currentData() or ""
        self._apply_company_excel_file()
        save_settings(self.settings)
        self._update_active_company_label()

    def append_log(self, text: str):
        self.log.append(repair_mojibake(text))

    def _remember_ui_path(self, *, pdf_dir: str | None = None, excel_file: str | None = None):
        if excel_file is not None:
            self._set_company_email_excel_file(excel_file)
        if not self.settings.get("ui", {}).get("remember_last_paths", True):
            if excel_file is not None:
                save_settings(self.settings)
            return
        if pdf_dir is not None:
            self.settings["ui"]["last_pdf_dir"] = pdf_dir
        if excel_file is not None:
            self.settings["ui"]["last_excel_file"] = excel_file
        save_settings(self.settings)

    def _best_existing_dir(self, *candidates: str) -> str:
        for candidate in candidates:
            if not candidate:
                continue
            path = Path(candidate)
            if path.is_dir():
                return str(path)
            if path.is_file() and path.parent.is_dir():
                return str(path.parent)
            if path.parent.is_dir():
                return str(path.parent)
        return str(Path(__file__).resolve().parent)

    def _initial_pdf_dir(self) -> str:
        path = self.settings.get("ui", {}).get("last_pdf_dir", "")
        saved_path = Path(path) if path else None
        if self._pdf_input_mode() == "single_pdf":
            if saved_path and saved_path.is_file():
                return str(saved_path.parent)
            if saved_path and saved_path.parent.is_dir():
                return str(saved_path.parent)
            return self._best_existing_dir(
                self.pdf_input_edit.text().strip(),
                self.excel_file_edit.text().strip(),
                path,
            )
        if saved_path and saved_path.is_dir():
            return path
        return self._best_existing_dir(
            self.pdf_input_edit.text().strip(),
            self.excel_file_edit.text().strip(),
            path,
        )

    def _pdf_input_mode(self) -> str:
        return str(self.input_mode_combo.currentData() or "folder")

    def _update_pdf_input_ui(self):
        if self._pdf_input_mode() == "single_pdf":
            self.btn_pdf_select.setText("PDF wählen")
        else:
            self.btn_pdf_select.setText("Ordner wählen")

    def _initial_excel_dir(self) -> str:
        candidates = [
            self.excel_file_edit.text().strip(),
            self._current_company_email_excel_file(),
            self.settings.get("ui", {}).get("last_excel_file", ""),
        ]
        for candidate in candidates:
            if not candidate:
                continue
            excel_path = Path(candidate)
            if excel_path.is_file():
                return str(excel_path.parent)
            if excel_path.parent.is_dir():
                return str(excel_path.parent)
        return ""

    def choose_pdf_input(self):
        if self._pdf_input_mode() == "single_pdf":
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Gesamt-PDF wählen",
                self._initial_pdf_dir(),
                "PDF Dateien (*.pdf)",
            )
            if file_path:
                self.pdf_input_edit.setText(file_path)
                self._remember_ui_path(pdf_dir=file_path)
            return

        folder = QFileDialog.getExistingDirectory(
            self,
            "PDF-Ordner wählen",
            self._initial_pdf_dir(),
        )
        if folder:
            self.pdf_input_edit.setText(folder)
            self._remember_ui_path(pdf_dir=folder)

    def choose_excel_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Excel-Datei wählen",
            self._initial_excel_dir(),
            "Excel Dateien (*.xlsx *.xlsm)",
        )
        if file_path:
            self.excel_file_edit.setText(file_path)
            self._remember_ui_path(excel_file=file_path)

    def open_settings(self, section: str = "mail"):
        dialog = SettingsDialog(self, initial_section=section)
        dialog.exec()
        self.settings = load_settings()
        self.reload_company_combo()
        self.dry_run_checkbox.setChecked(bool(self.settings.get("ui", {}).get("dry_run_default", True)))
        self.append_log("Einstellungen wurden aktualisiert.")

    def open_mass_message_dialog(self):
        if self.worker_thread is not None and self.worker_thread.isRunning():
            QMessageBox.information(self, "Vorgang lÃ¤uft", "Bitte warten Sie, bis der aktuelle Vorgang beendet ist.")
            return

        self._save_ui_state()
        dialog = MassMessageDialog(load_settings(), self)
        if dialog.exec() != QDialog.Accepted or not dialog.request:
            return

        self._launch_mass_message_worker(dialog.request)

    def _launch_mass_message_worker(self, request: dict):
        self.append_log(f"Starte Nachricht-Versand fÃ¼r Unternehmen: {request.get('company_name') or '-'}")
        self._set_busy(True)

        self.worker_thread = QThread(self)
        self.worker = MassMessageWorker(
            settings=request["settings"],
            company_id=request["company_id"],
            subject_template=request["subject"],
            body_template=request["body"],
            recipients=request["recipients"],
        )
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.append_log)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.error.connect(self.worker_thread.quit)
        self.worker_thread.finished.connect(lambda: self._set_busy(False))
        self.worker_thread.start()

    def open_help(self):
        HelpDialog(self).exec()

    def open_support(self):
        SupportDialog(self).exec()

    def _validate_inputs(self) -> tuple[Path, Path] | None:
        pdf_input = Path(self.pdf_input_edit.text().strip())
        excel_path = Path(self.excel_file_edit.text().strip())

        if self._pdf_input_mode() == "single_pdf":
            if not pdf_input.is_file() or pdf_input.suffix.lower() != ".pdf":
                QMessageBox.warning(
                    self,
                    "Fehler",
                    "Bitte eine gültige PDF-Datei auswählen",
                )
                return None
        elif not pdf_input.is_dir():
            QMessageBox.warning(self, "Fehler", "Bitte einen gültigen PDF-Ordner auswählen.")
            return None
        if not excel_path.is_file():
            QMessageBox.warning(self, "Fehler", "Bitte eine gültige Excel-Datei auswählen.")
            return None
        return pdf_input, excel_path

    def _save_ui_state(self):
        self.settings["selected_company_id"] = self.company_combo.currentData() or ""
        self._set_company_email_excel_file(self.excel_file_edit.text().strip())
        if self.settings.get("ui", {}).get("remember_last_paths", True):
            self.settings["ui"]["last_pdf_dir"] = self.pdf_input_edit.text().strip()
            self.settings["ui"]["last_pdf_input_mode"] = self._pdf_input_mode()
            self.settings["ui"]["last_excel_file"] = self.excel_file_edit.text().strip()
        save_settings(self.settings)

    def _set_busy(self, busy: bool):
        self.btn_check.setEnabled(not busy)
        self.btn_send.setEnabled(not busy)
        self.btn_send_selected.setEnabled(not busy)
        if hasattr(self, "action_mass_message"):
            self.action_mass_message.setEnabled(not busy)
        self.action_open_audit.setEnabled(not busy and bool(self.last_audit_path))
        self.action_open_missing_pdf.setEnabled(not busy and bool(self.last_missing_pdf_path))
        self.action_open_send_report.setEnabled(not busy and bool(self.last_send_report_path))

    def _launch_worker(
        self,
        mode: str,
        pdf_input: Path,
        excel_path: Path,
        settings: dict,
        dry_run: bool,
        selected_persnr: set[str] | None = None,
    ):
        company_name = get_company_name(settings, settings.get("selected_company_id"))
        self.append_log(f"Starte {mode} fÃ¼r Unternehmen: {company_name or '-'}")
        self.action_open_audit.setEnabled(False)
        self.action_open_missing_pdf.setEnabled(False)
        self.action_open_send_report.setEnabled(False)
        self._set_busy(True)

        self.worker_thread = QThread(self)
        self.worker = Worker(mode, pdf_input, excel_path, settings, dry_run, selected_persnr=selected_persnr)
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.append_log)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.error.connect(self.worker_thread.quit)
        self.worker_thread.finished.connect(lambda: self._set_busy(False))
        self.worker_thread.start()

    def start_job(self, mode: str):
        validated = self._validate_inputs()
        if not validated:
            return

        pdf_input, excel_path = validated
        self.settings = load_settings()
        self.settings["selected_company_id"] = self.company_combo.currentData() or ""
        self._save_ui_state()

        dry_run = self.dry_run_checkbox.isChecked()
        if mode == "send":
            self._pending_send_request = {
                "pdf_input": pdf_input,
                "excel_path": excel_path,
                "settings": self.settings.copy(),
                "dry_run": dry_run,
                "selected_persnr": None,
            }
            self._launch_worker("send_preview", pdf_input, excel_path, self.settings, dry_run)
            return
        company_name = get_company_name(self.settings, self.settings.get("selected_company_id"))
        self.append_log(f"Starte {mode} für Unternehmen: {company_name or '-'}")
        self.action_open_audit.setEnabled(False)
        self.action_open_missing_pdf.setEnabled(False)
        self.action_open_send_report.setEnabled(False)
        self._set_busy(True)

        self._launch_worker(mode, pdf_input, excel_path, self.settings, dry_run)

    def _selected_persnr_set(self) -> set[str]:
        return {
            str(row.get("PersNr", "") or "")
            for row in self.all_table_rows
            if row.get("Selected", True) and str(row.get("PersNr", "") or "").strip()
        }

    def start_selected_send(self):
        validated = self._validate_inputs()
        if not validated:
            return

        selected_persnr = self._selected_persnr_set()
        if not selected_persnr:
            QMessageBox.information(
                self,
                "Keine Auswahl",
                "Bitte markieren Sie zuerst die Mitarbeiter, die gesendet werden sollen.",
            )
            return

        pdf_input, excel_path = validated
        self.settings = load_settings()
        self.settings["selected_company_id"] = self.company_combo.currentData() or ""
        self._save_ui_state()

        dry_run = self.dry_run_checkbox.isChecked()
        self._pending_send_request = {
            "pdf_input": pdf_input,
            "excel_path": excel_path,
            "settings": self.settings.copy(),
            "dry_run": dry_run,
            "selected_persnr": selected_persnr,
        }
        self._launch_worker(
            "send_preview",
            pdf_input,
            excel_path,
            self.settings,
            dry_run,
            selected_persnr=selected_persnr,
        )

    def _open_path(self, path_str: str, label: str):
        if not path_str:
            QMessageBox.information(self, "Datei nicht verfügbar", f"Für {label} ist noch kein Pfad vorhanden.")
            return
        path = Path(path_str)
        if not path.exists():
            QMessageBox.warning(self, "Datei nicht gefunden", f"Die Datei für {label} wurde nicht gefunden:\n{path}")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.resolve())))

    def open_audit_file(self):
        self._open_path(self.last_audit_path, "audit_check.xlsx")

    def open_missing_pdf_file(self):
        self._open_path(self.last_missing_pdf_path, "ohne_email_gesamt.pdf")

    def open_send_report_file(self):
        self._open_path(self.last_send_report_path, "send_report.xlsx")

    def _show_send_preview(self, result: dict) -> bool:
        settings = (self._pending_send_request or {}).get("settings", self.settings)
        dry_run = bool((self._pending_send_request or {}).get("dry_run", self.dry_run_checkbox.isChecked()))
        selected_persnr = (self._pending_send_request or {}).get("selected_persnr")
        try:
            preview_data = build_send_preview_data(
                settings=settings,
                table_rows=result.get("table_rows", []),
                dry_run=dry_run,
                summary=result.get("summary", {}),
                selected_persnr=selected_persnr,
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Versand-Vorschau", str(exc))
            return False

        dialog = SendPreviewDialog(
            summary_lines=preview_data["summary_lines"],
            rows=preview_data["preview_rows"],
            subject_preview=preview_data["subject_preview"],
            parent=self,
        )
        return dialog.exec() == QDialog.Accepted

    def on_finished(self, result: dict):
        if result.get("mode") == "mass_message":
            sent_count = int(result.get("sent_count", 0) or 0)
            error_count = int(result.get("error_count", 0) or 0)
            total_count = int(result.get("total_count", 0) or 0)
            self.append_log("--- Nachricht-Versand abgeschlossen ---")
            self.append_log(f"Gesendet: {sent_count}/{total_count}")
            if error_count:
                self.append_log(f"Fehler: {error_count}")
                for error in result.get("errors", [])[:20]:
                    self.append_log(
                        f"{error.get('PersNr', '')} -> {error.get('Email', '')}: {error.get('Error', '')}"
                    )
            QMessageBox.information(
                self,
                "Nachricht-Versand",
                f"Gesendet: {sent_count}/{total_count}\nFehler: {error_count}",
            )
            return

        if result.get("mode") == "send_preview":
            if not self._show_send_preview(result):
                self._pending_send_request = None
                self.append_log("Versand wurde vor dem Start abgebrochen.")
                return

            request = self._pending_send_request or {}
            self._pending_send_request = None
            if self.worker_thread is not None and self.worker_thread.isRunning():
                self.worker_thread.finished.connect(
                    lambda req=request: self._launch_worker(
                        "send",
                        req["pdf_input"],
                        req["excel_path"],
                        req["settings"],
                        req["dry_run"],
                        selected_persnr=req.get("selected_persnr"),
                    )
                )
            else:
                self._launch_worker(
                    "send",
                    request["pdf_input"],
                    request["excel_path"],
                    request["settings"],
                    request["dry_run"],
                    selected_persnr=request.get("selected_persnr"),
                )
            return

        self.fill_table(result.get("table_rows", []))

        summary = result.get("summary", {})
        if summary:
            self.append_log("--- Zusammenfassung ---")
            for key, value in summary.items():
                self.append_log(f"{key}: {value}")

        run_dir = result.get("run_dir")
        audit_path = result.get("audit_path")
        missing_pdf_path = result.get("missing_pdf_path")
        send_report_path = result.get("send_report_path")

        self.last_audit_path = str(audit_path or "")
        self.last_missing_pdf_path = str(missing_pdf_path or "")
        self.last_send_report_path = str(send_report_path or "")

        self.action_open_audit.setEnabled(bool(audit_path and Path(audit_path).exists()))
        self.action_open_missing_pdf.setEnabled(bool(missing_pdf_path and Path(missing_pdf_path).exists()))
        self.action_open_send_report.setEnabled(bool(send_report_path and Path(send_report_path).exists()))

        if run_dir:
            self.append_log(f"Run-Ordner: {run_dir}")
        if audit_path:
            self.append_log(f"audit_check.xlsx: {audit_path}")
        if missing_pdf_path:
            self.append_log(f"ohne_email_gesamt.pdf: {missing_pdf_path}")
        else:
            self.append_log("ohne_email_gesamt.pdf: nicht erstellt (keine Mitarbeiter ohne E-Mail).")
        if send_report_path:
            self.append_log(f"send_report.xlsx: {send_report_path}")

        msg_lines = ["Vorgang abgeschlossen."]
        if run_dir:
            msg_lines.append(f"\nRun-Ordner:\n{run_dir}")
        if audit_path:
            msg_lines.append(f"\nAudit-Datei:\n{audit_path}")
        if missing_pdf_path:
            msg_lines.append(f"\nSammel-PDF ohne E-Mail:\n{missing_pdf_path}")
        if send_report_path:
            msg_lines.append(f"\nVersandbericht:\n{send_report_path}")

        QMessageBox.information(self, "Fertig", "".join(msg_lines))

    def on_error(self, message: str):
        self.append_log(f"FEHLER: {message}")
        QMessageBox.critical(self, "Fehler", message)

    def _status_color(self, status: str) -> QColor | None:
        status_norm = str(status or "").strip().lower()
        if not status_norm:
            return None

        if "fehler" in status_norm or "keine e-mail" in status_norm:
            return QColor(244, 199, 195)
        if "gesendet" in status_norm or status_norm == "ok":
            return QColor(206, 234, 214)
        if "dry-run" in status_norm or "keine dateien" in status_norm:
            return QColor(255, 242, 204)
        return None

    def clear_table_filters(self):
        self.search_persnr_edit.clear()
        self.search_email_edit.clear()
        self.status_filter_combo.setCurrentIndex(0)

    def set_all_checkboxes(self, checked: bool):
        for row in self.all_table_rows:
            if self._is_selectable_row(row):
                row["Selected"] = checked
        self.apply_table_filters()

    def _row_key(self, row: dict) -> str:
        return "|".join([
            str(row.get("PersNr", "") or ""),
            str(row.get("Name", "") or ""),
            str(row.get("Vorname", "") or ""),
            str(row.get("Email", "") or ""),
            str(row.get("Files", "") or ""),
            str(row.get("Status", "") or ""),
        ])

    def _is_selectable_row(self, row: dict) -> bool:
        persnr = str(row.get("PersNr", "") or "").strip()
        return bool(persnr)

    def _on_table_item_changed(self, item: QTableWidgetItem):
        if item.column() != 0:
            return
        row_key = item.data(Qt.UserRole)
        if not row_key:
            return
        for row in self.all_table_rows:
            if self._row_key(row) == row_key:
                row["Selected"] = item.checkState() == Qt.Checked
                break

    def _row_matches_filters(self, row: dict) -> bool:
        persnr_query = self.search_persnr_edit.text().strip().lower()
        email_query = self.search_email_edit.text().strip().lower()
        status_filter = self.status_filter_combo.currentText().strip().lower()

        persnr = str(row.get("PersNr", "") or "").lower()
        email = str(row.get("Email", "") or "").lower()
        status = str(row.get("Status", "") or "").lower()

        if persnr_query and persnr_query not in persnr:
            return False
        if email_query and email_query not in email:
            return False
        if status_filter and status_filter != "alle" and status_filter != status:
            return False
        return True

    def _render_table(self, rows: list[dict]):
        self.table.setRowCount(len(rows))
        self.table.blockSignals(True)
        for row_index, row in enumerate(rows):
            select_item = QTableWidgetItem()
            select_item.setData(Qt.UserRole, self._row_key(row))
            if self._is_selectable_row(row):
                select_item.setFlags(select_item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                select_item.setCheckState(Qt.Checked if row.get("Selected", True) else Qt.Unchecked)
            else:
                select_item.setFlags(Qt.ItemIsEnabled)
            self.table.setItem(row_index, 0, select_item)

            values = [
                str(row.get("PersNr", "")),
                format_name_vorname_row(row),
                str(row.get("Email", "")),
                str(row.get("Files", "")),
                str(row.get("Count", "")),
                str(row.get("Status", "")),
                str(row.get("Attachment", "")),
                str(row.get("Password", "")),
                str(row.get("Error", "")),
            ]
            row_color = self._status_color(row.get("Status", ""))
            if row_color is not None:
                select_item.setBackground(row_color)
            for col_index, value in enumerate(values, start=1):
                item = QTableWidgetItem(value)
                if row_color is not None:
                    item.setBackground(row_color)
                self.table.setItem(row_index, col_index, item)
        self.table.blockSignals(False)

    def apply_table_filters(self):
        filtered_rows = [row for row in self.all_table_rows if self._row_matches_filters(row)]
        self._render_table(filtered_rows)

    def fill_table(self, rows: list[dict]):
        previous_selected_by_persnr = {
            str(row.get("PersNr", "") or "").strip(): bool(row.get("Selected", True))
            for row in self.all_table_rows
            if str(row.get("PersNr", "") or "").strip()
        }
        self.all_table_rows = []
        for row in rows:
            row_copy = dict(row)
            persnr = str(row_copy.get("PersNr", "") or "").strip()
            if persnr and persnr in previous_selected_by_persnr:
                row_copy["Selected"] = previous_selected_by_persnr[persnr]
            else:
                row_copy.setdefault("Selected", self._is_selectable_row(row_copy))
            self.all_table_rows.append(row_copy)
        self.apply_table_filters()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

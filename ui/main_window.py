from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout, QMainWindow, QMessageBox, QStackedWidget, QVBoxLayout, QWidget
)

from app_gui import MainWindow as LegacyMainWindow
from core.config import APP_NAME, consume_settings_warning, get_company_name, load_settings, save_settings
from ui.layout.footer import Footer
from ui.layout.sidebar import Sidebar
from ui.layout.topbar import TopBar
from ui.pages.dashboard_page import DashboardPage
from ui.pages.processing_page import ProcessingPage
from ui.pages.validation_page import ValidationPage
from ui.pages.mailing_page import MailingPage
from ui.pages.reports_page import ReportsPage
from ui.pages.company_page import CompanyPage
from ui.pages.license_page import LicensePage
from ui.pages.settings_page import SettingsPage
from ui.pages.help_page import HelpPage
from ui.pages.about_page import AboutPage
from ui.theme.stylesheet import build_stylesheet


class MainWindow(LegacyMainWindow):
    """LohnMail v2 shell.

    It intentionally inherits the legacy MainWindow methods so existing PDF/Excel/Mail
    business logic, dialogs and worker flow remain intact while the visual structure
    is replaced by the new product shell.
    """

    PAGE_TITLES = {
        'dashboard': 'Dashboard',
        'processing': 'Verarbeitung',
        'validation': 'Prüfung',
        'mailing': 'Versand',
        'reports': 'Berichte',
        'company': 'Unternehmen',
        'license': 'Lizenzen',
        'settings': 'Einstellungen',
        'help': 'Hilfe',
        'about': 'Über LohnMail',
    }

    def __init__(self):
        QMainWindow.__init__(self)
        self.settings = load_settings()
        self._company_combo_updating = False
        self._pending_send_request: dict | None = None
        self.worker_thread = None
        self.worker = None
        self.all_table_rows: list[dict] = []
        self.last_audit_path = ''
        self.last_missing_pdf_path = ''
        self.last_send_report_path = ''

        self.setWindowTitle(f'{APP_NAME} v2')
        self.resize(
            int(self.settings.get('ui', {}).get('window_width', 1280)),
            int(self.settings.get('ui', {}).get('window_height', 820)),
        )
        self.setStyleSheet(build_stylesheet())
        self._create_menu_bar()
        self._build_shell()
        self._wire_legacy_logic()
        self.navigate('dashboard')

        settings_warning = consume_settings_warning()
        if settings_warning:
            self.append_log(f'WARNUNG: {settings_warning}')
            QMessageBox.warning(self, 'Einstellungen', settings_warning)

    def _build_shell(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.sidebar = Sidebar()
        root.addWidget(self.sidebar)

        main = QWidget()
        main_layout = QVBoxLayout(main)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        root.addWidget(main, 1)

        self.topbar = TopBar()
        main_layout.addWidget(self.topbar)

        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack, 1)

        self.footer = Footer()
        main_layout.addWidget(self.footer)

        self.pages = {}
        self.dashboard_page = DashboardPage(self)
        self.pages['dashboard'] = self.dashboard_page
        self.pages['processing'] = ProcessingPage(self)
        self.pages['validation'] = ValidationPage(self)
        self.pages['mailing'] = MailingPage(self)
        self.pages['reports'] = ReportsPage(self)
        self.pages['company'] = CompanyPage(self)
        self.pages['license'] = LicensePage(self)
        self.pages['settings'] = SettingsPage(self)
        self.pages['help'] = HelpPage(self)
        self.pages['about'] = AboutPage(self)

        for key in self.PAGE_TITLES:
            self.stack.addWidget(self.pages[key])

    def _wire_legacy_logic(self) -> None:
        self.reload_company_combo()
        self._update_pdf_input_ui()
        self.sidebar.page_selected.connect(self.navigate)
        self.input_mode_combo.currentIndexChanged.connect(self._update_pdf_input_ui)
        self.company_combo.currentIndexChanged.connect(self._company_changed)
        self.btn_check.clicked.connect(lambda: self.start_job('check'))
        self.btn_send.clicked.connect(lambda: self.start_job('send'))
        self.btn_send_selected.clicked.connect(self.start_selected_send)
        self.search_persnr_edit.textChanged.connect(self.apply_table_filters)
        self.search_email_edit.textChanged.connect(self.apply_table_filters)
        self.status_filter_combo.currentIndexChanged.connect(self.apply_table_filters)
        self.btn_select_all.clicked.connect(lambda: self.set_all_checkboxes(True))
        self.btn_select_none.clicked.connect(lambda: self.set_all_checkboxes(False))
        self.btn_clear_filters.clicked.connect(self.clear_table_filters)
        self.table.itemChanged.connect(self._on_table_item_changed)

    def navigate(self, key: str) -> None:
        if key not in self.pages:
            key = 'dashboard'
        self.stack.setCurrentWidget(self.pages[key])
        self.sidebar.set_current(key)
        self.topbar.set_title(self.PAGE_TITLES.get(key, key))

    def _set_busy(self, busy: bool):
        super()._set_busy(busy)
        for attr in ('btn_send_mailing', 'btn_send_selected_mailing', 'btn_check_mailing'):
            button = getattr(self, attr, None)
            if button is not None:
                button.setEnabled(not busy)
        self.topbar.set_title('Verarbeitung läuft…' if busy else self.PAGE_TITLES.get(self._current_page_key(), 'Dashboard'))

    def _current_page_key(self) -> str:
        widget = self.stack.currentWidget()
        for key, page in self.pages.items():
            if page is widget:
                return key
        return 'dashboard'

    def on_finished(self, result: dict):
        super().on_finished(result)
        if hasattr(self, 'dashboard_page'):
            self.dashboard_page.update_from_result(result)
        if result.get('mode') not in {'send_preview', 'mass_message'}:
            self.navigate('validation')

    def _save_ui_state(self):
        self.settings['selected_company_id'] = self.company_combo.currentData() or ''
        self._set_company_email_excel_file(self.excel_file_edit.text().strip())
        ui = self.settings.setdefault('ui', {})
        ui['window_width'] = self.width()
        ui['window_height'] = self.height()
        if ui.get('remember_last_paths', True):
            ui['last_pdf_dir'] = self.pdf_input_edit.text().strip()
            ui['last_pdf_input_mode'] = self._pdf_input_mode()
            ui['last_excel_file'] = self.excel_file_edit.text().strip()
        save_settings(self.settings)

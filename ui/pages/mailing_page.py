from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGridLayout,
    QTableWidget, QHeaderView, QTextEdit
)
from ui.widgets.card import LMCard
from ui.widgets.badge import LMBadge


class MailingPage(QWidget):
    def __init__(self, window):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(18)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel('Versand')
        title.setObjectName('pageTitle')
        subtitle = QLabel('Empfänger prüfen, Testversand ausführen und E-Mails kontrolliert versenden.')
        subtitle.setObjectName('muted')
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box)
        header.addStretch(1)
        mass_btn = QPushButton('Nachricht senden')
        mass_btn.clicked.connect(window.open_mass_message_dialog)
        header.addWidget(mass_btn)
        root.addLayout(header)

        grid = QGridLayout()
        grid.setSpacing(18)

        summary = LMCard('Versandkontrolle')
        summary.layout.addWidget(LMBadge('Dry-Run empfohlen', 'warning'))
        summary.layout.addWidget(QLabel('1. Prüfung starten\n2. Empfänger kontrollieren\n3. Versandvorschau bestätigen\n4. Senden'))
        grid.addWidget(summary, 0, 0)

        actions = LMCard('Aktionen')
        window.btn_send_mailing = QPushButton('E-Mails senden')
        window.btn_send_mailing.setObjectName('primary')
        window.btn_send_selected_mailing = QPushButton('Nur ausgewählte senden')
        window.btn_check_mailing = QPushButton('Vor Versand prüfen')
        window.btn_check_mailing.clicked.connect(lambda: window.start_job('check'))
        window.btn_send_mailing.clicked.connect(lambda: window.start_job('send'))
        window.btn_send_selected_mailing.clicked.connect(window.start_selected_send)
        actions.layout.addWidget(window.btn_check_mailing)
        actions.layout.addWidget(window.btn_send_mailing)
        actions.layout.addWidget(window.btn_send_selected_mailing)
        grid.addWidget(actions, 0, 1)

        status = LMCard('Mail-System')
        status.layout.addWidget(LMBadge('SMTP / Outlook verbunden', 'success'))
        status.layout.addWidget(QLabel('Die tatsächliche Versandart wird aus den vorhandenen Einstellungen übernommen.'))
        grid.addWidget(status, 0, 2)
        root.addLayout(grid)

        table_card = LMCard('Empfängerübersicht')
        info = QLabel('Die zentrale Prüftabelle bleibt auf der Seite Prüfung. Für den Versand werden die dort markierten Mitarbeiter verwendet.')
        info.setObjectName('muted')
        table_card.layout.addWidget(info)
        root.addWidget(table_card)

        log_card = LMCard('Versandjournal')
        self.mail_log_hint = QLabel('Versandmeldungen erscheinen zusätzlich im Live Operation Log auf Verarbeitung.')
        self.mail_log_hint.setObjectName('muted')
        log_card.layout.addWidget(self.mail_log_hint)
        root.addWidget(log_card)
        root.addStretch(1)

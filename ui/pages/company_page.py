from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGridLayout, QFormLayout, QLineEdit
from ui.widgets.card import LMCard
from ui.widgets.badge import LMBadge


class CompanyPage(QWidget):
    def __init__(self, window):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(18)
        title = QLabel('Unternehmen')
        title.setObjectName('pageTitle')
        root.addWidget(title)
        root.addWidget(QLabel('Firmenprofil, Absenderdaten, SMTP/Outlook und Standardvorlagen.'))

        grid = QGridLayout()
        grid.setSpacing(18)
        profile = LMCard('Firmenprofil')
        form = QFormLayout()
        company = window.settings.get('companies', [{}])[0] if window.settings.get('companies') else {}
        for label, value in [
            ('Firmenname', company.get('name', '')),
            ('Ansprechpartner', company.get('contact', '')),
            ('E-Mail', company.get('sender_email', company.get('email', ''))),
            ('Absendername', company.get('sender_name', '')),
        ]:
            edit = QLineEdit(str(value or ''))
            edit.setReadOnly(True)
            form.addRow(label, edit)
        profile.layout.addLayout(form)
        btn_companies = QPushButton('Unternehmen bearbeiten')
        btn_companies.clicked.connect(lambda: window.open_settings('companies'))
        profile.layout.addWidget(btn_companies)
        grid.addWidget(profile, 0, 0)

        smtp = LMCard('Mail-Konfiguration')
        smtp.layout.addWidget(LMBadge('SMTP / Outlook', 'primary'))
        smtp.layout.addWidget(QLabel('Alle bestehenden SMTP-, Outlook- und Absendereinstellungen bleiben im vorhandenen Einstellungsdialog verbunden.'))
        btn_mail = QPushButton('E-Mail-Einstellungen')
        btn_mail.clicked.connect(lambda: window.open_settings('mail'))
        smtp.layout.addWidget(btn_mail)
        grid.addWidget(smtp, 0, 1)

        templates = LMCard('Vorlagen & Signatur')
        templates.layout.addWidget(QLabel('Standard-Betreff, E-Mail-Text, Variablen und Signatur.'))
        btn_letter = QPushButton('E-Mail-Text bearbeiten')
        btn_letter.clicked.connect(lambda: window.open_settings('letter'))
        templates.layout.addWidget(btn_letter)
        grid.addWidget(templates, 0, 2)
        root.addLayout(grid)
        root.addStretch(1)

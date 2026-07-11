from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGridLayout
from ui.widgets.card import LMCard


class SettingsPage(QWidget):
    def __init__(self, window):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(18)
        title = QLabel('Einstellungen')
        title.setObjectName('pageTitle')
        root.addWidget(title)
        root.addWidget(QLabel('Schneller Einstieg in die bestehenden Konfigurationsbereiche.'))

        grid = QGridLayout()
        grid.setSpacing(18)
        items = [
            ('Allgemein', 'Pfadverhalten, Dry-Run und UI-Defaults.', None),
            ('Unternehmen', 'Firmen und Excel-Zuordnung.', lambda: window.open_settings('companies')),
            ('Mail', 'SMTP, Outlook-Modus und Absender.', lambda: window.open_settings('mail')),
            ('E-Mail-Text', 'Betreff, Text, Variablen und Signatur.', lambda: window.open_settings('letter')),
            ('Passwort', 'Passwortlogik für verschlüsselte PDFs.', lambda: window.open_settings('password')),
            ('Zeitraum', 'Abrechnungsperiode und Periodenlogik.', lambda: window.open_settings('period')),
        ]
        for i, (title_text, desc, callback) in enumerate(items):
            card = LMCard(title_text)
            d = QLabel(desc)
            d.setWordWrap(True)
            d.setObjectName('muted')
            card.layout.addWidget(d)
            if callback:
                btn = QPushButton('Öffnen')
                btn.clicked.connect(callback)
                card.layout.addWidget(btn)
            grid.addWidget(card, i // 3, i % 3)
        root.addLayout(grid)
        root.addStretch(1)

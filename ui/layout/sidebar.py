from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QVBoxLayout, QPushButton, QLabel

class Sidebar(QFrame):
    page_selected = Signal(str)

    ITEMS = [
        ('dashboard', 'Dashboard'),
        ('processing', 'Verarbeitung'),
        ('validation', 'Prüfung'),
        ('mailing', 'Versand'),
        ('reports', 'Berichte'),
        ('sep1', ''),
        ('company', 'Unternehmen'),
        ('license', 'Lizenzen'),
        ('settings', 'Einstellungen'),
        ('sep2', ''),
        ('help', 'Hilfe'),
        ('about', 'Über LohnMail'),
    ]

    def __init__(self):
        super().__init__()
        self.setObjectName('sidebar')
        self.setFixedWidth(280)
        self.buttons: dict[str, QPushButton] = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 20, 18, 16)
        layout.setSpacing(6)

        brand = QLabel('LohnMail')
        brand.setStyleSheet('font-size: 22px; font-weight: 800;')
        subtitle = QLabel('Payroll Mail Automation')
        subtitle.setObjectName('muted')
        layout.addWidget(brand)
        layout.addWidget(subtitle)
        layout.addSpacing(18)

        for key, title in self.ITEMS:
            if key.startswith('sep'):
                layout.addSpacing(12)
                continue
            btn = QPushButton(title)
            btn.setObjectName('nav')
            btn.setProperty('selected', 'false')
            btn.clicked.connect(lambda checked=False, k=key: self.page_selected.emit(k))
            self.buttons[key] = btn
            layout.addWidget(btn)
        layout.addStretch(1)

    def set_current(self, key: str) -> None:
        for item_key, button in self.buttons.items():
            button.setProperty('selected', 'true' if item_key == key else 'false')
            button.style().unpolish(button)
            button.style().polish(button)

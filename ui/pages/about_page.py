from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from ui.widgets.card import LMCard
from core.config import APP_NAME


class AboutPage(QWidget):
    def __init__(self, window):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(18)
        title = QLabel('Über LohnMail')
        title.setObjectName('pageTitle')
        root.addWidget(title)
        card = LMCard(APP_NAME)
        card.layout.addWidget(QLabel('Version: 2.0.0-alpha\nBuild Preview: 2\nEntwickler: Andrii Bakanov\nFramework: PySide6\nArchitektur: lokales Desktop-App mit bestehendem Core.'))
        root.addWidget(card)
        root.addStretch(1)

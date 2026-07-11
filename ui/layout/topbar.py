from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton
from ui.widgets.badge import LMBadge

class TopBar(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName('topbar')
        self.setFixedHeight(64)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 0, 24, 0)
        self.title = QLabel('Dashboard')
        self.title.setStyleSheet('font-size: 16px; font-weight: 750;')
        layout.addWidget(self.title)
        layout.addStretch(1)
        layout.addWidget(LMBadge('License Active', 'success'))
        layout.addWidget(LMBadge('System Ready', 'primary'))
        self.theme_btn = QPushButton('Light')
        self.theme_btn.setObjectName('ghost')
        layout.addWidget(self.theme_btn)
        layout.addWidget(QLabel('Andrii'))

    def set_title(self, title: str) -> None:
        self.title.setText(title)

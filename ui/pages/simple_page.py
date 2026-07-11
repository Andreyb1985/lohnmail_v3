from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from ui.widgets.card import LMCard

class SimplePage(QWidget):
    def __init__(self, title: str, description: str = '', actions: list[tuple[str, callable]] | None = None):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(18)
        heading = QLabel(title); heading.setObjectName('pageTitle')
        root.addWidget(heading)
        card = LMCard(title)
        text = QLabel(description or 'Dieser Bereich wird im nächsten Sprint mit der bestehenden Logik verbunden.')
        text.setWordWrap(True); text.setObjectName('muted')
        card.layout.addWidget(text)
        for label, callback in actions or []:
            btn = QPushButton(label)
            btn.clicked.connect(callback)
            card.layout.addWidget(btn)
        root.addWidget(card)
        root.addStretch(1)

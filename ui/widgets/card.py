from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QWidget

class LMCard(QFrame):
    def __init__(self, title: str | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName('card')
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(18, 16, 18, 16)
        self.layout.setSpacing(12)
        if title:
            label = QLabel(title)
            label.setObjectName('sectionTitle')
            self.layout.addWidget(label)

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel

class Footer(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName('footer')
        self.setFixedHeight(30)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 0, 18, 0)
        for text in ['v2.0.0-alpha', 'License: Active', 'Mail: Local/SMTP', 'Core: Connected', 'Ready']:
            label = QLabel(text)
            label.setObjectName('muted')
            layout.addWidget(label)
        layout.addStretch(1)

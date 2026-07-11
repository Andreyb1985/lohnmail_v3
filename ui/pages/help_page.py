from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGridLayout
from ui.widgets.card import LMCard


class HelpPage(QWidget):
    def __init__(self, window):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(18)
        title = QLabel('Hilfe')
        title.setObjectName('pageTitle')
        root.addWidget(title)
        grid = QGridLayout(); grid.setSpacing(18)
        docs = LMCard('Dokumentation')
        docs.layout.addWidget(QLabel('Handbuch, Ablauf und häufige Fragen.'))
        btn_help = QPushButton('Help öffnen')
        btn_help.clicked.connect(window.open_help)
        docs.layout.addWidget(btn_help)
        grid.addWidget(docs, 0, 0)
        support = LMCard('Support')
        support.layout.addWidget(QLabel('Technische Unterstützung und Log-Analyse.'))
        btn_support = QPushButton('Technischer Support')
        btn_support.clicked.connect(window.open_support)
        support.layout.addWidget(btn_support)
        grid.addWidget(support, 0, 1)
        logs = LMCard('Logs senden')
        logs.layout.addWidget(QLabel('Log-Export wird in einem späteren Sprint direkt mit dem lokalen Journal verbunden.'))
        grid.addWidget(logs, 0, 2)
        root.addLayout(grid)
        root.addStretch(1)

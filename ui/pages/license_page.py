from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGridLayout, QTableWidget, QHeaderView
from ui.widgets.card import LMCard
from ui.widgets.badge import LMBadge


class LicensePage(QWidget):
    def __init__(self, window):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(18)
        title = QLabel('Lizenzen')
        title.setObjectName('pageTitle')
        root.addWidget(title)

        grid = QGridLayout()
        grid.setSpacing(18)
        overview = LMCard('License Manager')
        overview.layout.addWidget(LMBadge('Active', 'success'))
        overview.layout.addWidget(QLabel('Typ: Business\nLizenznummer: lokal verwaltet\nArbeitsplätze: 1 / 3\nServer: Connected'))
        grid.addWidget(overview, 0, 0)

        actions = LMCard('Aktionen')
        for text in ['Lizenz aktivieren', 'Lizenz deaktivieren', 'Lizenz verlängern', 'Lizenz übertragen']:
            btn = QPushButton(text)
            btn.setEnabled(False)
            actions.layout.addWidget(btn)
        actions.layout.addWidget(QLabel('Die Oberfläche ist vorbereitet; echte Lizenzserver-Logik folgt separat.'))
        grid.addWidget(actions, 0, 1)

        states = LMCard('Statuszustände')
        for label, tone in [('Trial', 'info'), ('Active', 'success'), ('Expiring Soon', 'warning'), ('Expired', 'error'), ('Invalid License', 'error'), ('No Connection', 'warning'), ('Activation Error', 'error')]:
            states.layout.addWidget(LMBadge(label, tone))
        grid.addWidget(states, 0, 2)
        root.addLayout(grid)

        history = LMCard('Aktivierungshistorie')
        table = QTableWidget(0, 5)
        table.setHorizontalHeaderLabels(['Datum', 'Aktion', 'Computer', 'Benutzer', 'Status'])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        history.layout.addWidget(table)
        root.addWidget(history, 1)

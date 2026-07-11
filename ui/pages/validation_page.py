from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QPushButton, QTableWidget, QHeaderView
from ui.widgets.card import LMCard

class ValidationPage(QWidget):
    def __init__(self, window):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(18)
        title = QLabel('Prüfung')
        title.setObjectName('pageTitle')
        root.addWidget(title)

        filters = LMCard('Filter & Ergebnisse')
        row = QHBoxLayout()
        window.search_persnr_edit = QLineEdit(); window.search_persnr_edit.setPlaceholderText('Suche PersNr')
        window.search_email_edit = QLineEdit(); window.search_email_edit.setPlaceholderText('Suche E-Mail')
        window.status_filter_combo = QComboBox(); window.status_filter_combo.addItems(['Alle','OK','Keine E-Mail','Keine Dateien','Fehler','Dry-Run','Gesendet'])
        window.btn_select_all = QPushButton('Alle markieren')
        window.btn_select_none = QPushButton('Alle abwählen')
        window.btn_clear_filters = QPushButton('Filter zurücksetzen')
        for w in [QLabel('PersNr'), window.search_persnr_edit, QLabel('E-Mail'), window.search_email_edit, QLabel('Status'), window.status_filter_combo, window.btn_select_all, window.btn_select_none, window.btn_clear_filters]:
            row.addWidget(w)
        filters.layout.addLayout(row)
        root.addWidget(filters)

        window.table = QTableWidget(0, 10)
        window.table.setHorizontalHeaderLabels(['Auswahl','PersNr','Name, Vorname','E-Mail','Dateien','Anzahl','Status','Anhang','Passwort','Fehler'])
        window.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        root.addWidget(window.table, 1)

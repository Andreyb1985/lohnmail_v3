from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGridLayout
from ui.widgets.card import LMCard
from ui.widgets.badge import LMBadge


class ReportsPage(QWidget):
    def __init__(self, window):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(18)

        title = QLabel('Berichte')
        title.setObjectName('pageTitle')
        root.addWidget(title)
        subtitle = QLabel('Zentrale Ablage für Prüf-, Versand- und Auditberichte des letzten Laufs.')
        subtitle.setObjectName('muted')
        root.addWidget(subtitle)

        grid = QGridLayout()
        grid.setSpacing(18)

        for i, (title_text, desc, action_text, callback, tone) in enumerate([
            ('Prüfbericht', 'audit_check.xlsx mit PersNr, E-Mail, Status und Fehlerdetails.', 'audit_check.xlsx öffnen', window.open_audit_file, 'info'),
            ('Ohne E-Mail', 'Gesamt-PDF für Mitarbeiter ohne E-Mail-Adresse.', 'ohne_email_gesamt.pdf öffnen', window.open_missing_pdf_file, 'warning'),
            ('Versandbericht', 'send_report.xlsx mit Zustellstatus und Versandfehlern.', 'send_report.xlsx öffnen', window.open_send_report_file, 'success'),
        ]):
            card = LMCard(title_text)
            card.layout.addWidget(LMBadge(title_text, tone))
            label = QLabel(desc)
            label.setWordWrap(True)
            label.setObjectName('muted')
            card.layout.addWidget(label)
            btn = QPushButton(action_text)
            btn.clicked.connect(callback)
            card.layout.addWidget(btn)
            grid.addWidget(card, 0, i)
        root.addLayout(grid)

        audit = LMCard('Audit & Statistik')
        audit.layout.addWidget(QLabel('Nach jedem Lauf werden die zuletzt erzeugten Pfade automatisch im Footer/Menu aktiviert. Weitere PDF-/Excel-Exporte werden in einem späteren Sprint direkt hier ergänzt.'))
        root.addWidget(audit)
        root.addStretch(1)

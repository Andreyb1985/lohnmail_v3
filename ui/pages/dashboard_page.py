from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGridLayout, QProgressBar
from ui.widgets.card import LMCard
from ui.widgets.badge import LMBadge

class DashboardPage(QWidget):
    def __init__(self, parent_window=None):
        super().__init__()
        self.parent_window = parent_window
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(24)
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel('Dashboard')
        title.setObjectName('pageTitle')
        subtitle = QLabel('Überblick über Verarbeitung, Versand und Systemstatus.')
        subtitle.setObjectName('muted')
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box)
        header.addStretch(1)
        new_btn = QPushButton('New Processing')
        new_btn.setObjectName('primary')
        if parent_window:
            new_btn.clicked.connect(lambda: parent_window.navigate('processing'))
        header.addWidget(new_btn)
        root.addLayout(header)

        kpi = QGridLayout()
        kpi.setSpacing(16)
        self.cards = {}
        for i, (key, value, label, tone) in enumerate([
            ('employees', '0', 'Employees processed', 'primary'),
            ('sent', '0', 'Emails sent', 'success'),
            ('missing', '0', 'Missing emails', 'warning'),
            ('errors', '0', 'Errors', 'error'),
        ]):
            card = LMCard()
            number = QLabel(value)
            number.setStyleSheet('font-size: 32px; font-weight: 800;')
            text = QLabel(label)
            text.setObjectName('muted')
            badge = LMBadge('Ready', tone)
            card.layout.addWidget(number)
            card.layout.addWidget(text)
            card.layout.addWidget(badge)
            self.cards[key] = number
            kpi.addWidget(card, 0, i)
        root.addLayout(kpi)

        mid = QGridLayout()
        mid.setSpacing(18)
        health = LMCard('System Health')
        for text, tone in [('SMTP Ready', 'success'), ('License Active', 'success'), ('PDF Engine OK', 'success'), ('Excel Engine OK', 'success')]:
            health.layout.addWidget(LMBadge(text, tone))
        mid.addWidget(health, 0, 0)

        activity = LMCard('Activity Timeline')
        self.activity_label = QLabel('Noch keine Verarbeitung gestartet.\nWähle PDF und Excel in Verarbeitung.')
        self.activity_label.setObjectName('muted')
        activity.layout.addWidget(self.activity_label)
        mid.addWidget(activity, 0, 1)

        pipeline = LMCard('Processing Overview')
        for step in ['PDF', 'Excel', 'Prüfung', 'Verarbeitung', 'Versand', 'Berichte']:
            pipeline.layout.addWidget(QLabel(f'○ {step}'))
        bar = QProgressBar()
        bar.setValue(0)
        pipeline.layout.addWidget(bar)
        mid.addWidget(pipeline, 0, 2)
        root.addLayout(mid)
        root.addStretch(1)

    def update_from_result(self, result: dict) -> None:
        rows = result.get('table_rows', []) or []
        summary = result.get('summary', {}) or {}
        total = len(rows)
        missing = sum(1 for r in rows if 'keine e-mail' in str(r.get('Status','')).lower())
        errors = sum(1 for r in rows if str(r.get('Error','') or '').strip() or 'fehler' in str(r.get('Status','')).lower())
        sent = sum(1 for r in rows if 'gesendet' in str(r.get('Status','')).lower())
        self.cards['employees'].setText(str(total or summary.get('total', 0) or 0))
        self.cards['sent'].setText(str(sent or summary.get('sent', 0) or 0))
        self.cards['missing'].setText(str(missing))
        self.cards['errors'].setText(str(errors))
        self.activity_label.setText('Letzter Lauf abgeschlossen.\nReports und Prüftabelle wurden aktualisiert.')

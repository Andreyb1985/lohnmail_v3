from PySide6.QtWidgets import QLabel
from ui.theme import tokens as t

class LMBadge(QLabel):
    COLORS = {
        'success': (t.SUCCESS, '#DCFCE7'),
        'warning': (t.WARNING, '#FEF3C7'),
        'error': (t.ERROR, '#FEE2E2'),
        'info': (t.INFO, '#E0F2FE'),
        'neutral': (t.MUTED, '#F3F4F6'),
        'primary': (t.PRIMARY, t.PRIMARY_SOFT),
    }
    def __init__(self, text: str, tone: str = 'neutral'):
        super().__init__(text)
        fg, bg = self.COLORS.get(tone, self.COLORS['neutral'])
        self.setStyleSheet(f'padding: 5px 10px; border-radius: 10px; background: {bg}; color: {fg}; font-weight: 700;')

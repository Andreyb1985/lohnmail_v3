from . import tokens as t


def build_stylesheet() -> str:
    return f'''
    QMainWindow {{ background: {t.BG}; }}
    QWidget {{ font-family: Inter, "SF Pro Display", "Segoe UI", Arial; font-size: 14px; color: {t.TEXT}; }}
    QLabel#muted {{ color: {t.MUTED}; }}
    QLabel#pageTitle {{ font-size: 26px; font-weight: 700; color: {t.TEXT}; }}
    QLabel#sectionTitle {{ font-size: 16px; font-weight: 650; color: {t.TEXT}; }}
    QFrame#sidebar {{ background: {t.SIDEBAR}; border-right: 1px solid {t.BORDER}; }}
    QFrame#topbar {{ background: {t.SURFACE}; border-bottom: 1px solid {t.BORDER}; }}
    QFrame#footer {{ background: {t.SURFACE}; border-top: 1px solid {t.BORDER}; }}
    QFrame#card {{ background: {t.SURFACE}; border: 1px solid {t.BORDER}; border-radius: 14px; }}
    QPushButton {{
        border: 1px solid {t.BORDER}; background: {t.SURFACE}; border-radius: 10px; padding: 8px 14px; font-weight: 600; min-height: 22px;
    }}
    QPushButton:hover {{ background: {t.SURFACE_2}; }}
    QPushButton#primary {{ background: {t.PRIMARY}; color: white; border: 1px solid {t.PRIMARY}; }}
    QPushButton#primary:hover {{ background: {t.PRIMARY_HOVER}; }}
    QPushButton#ghost {{ border: none; background: transparent; color: {t.MUTED}; text-align: left; padding: 10px 14px; }}
    QPushButton#ghost:hover {{ background: {t.SURFACE_2}; color: {t.TEXT}; }}
    QPushButton#nav {{ border: none; background: transparent; text-align: left; padding: 10px 14px; border-radius: 10px; color: {t.MUTED}; font-weight: 600; }}
    QPushButton#nav:hover {{ background: {t.SURFACE_2}; color: {t.TEXT}; }}
    QPushButton#nav[selected="true"] {{ background: {t.PRIMARY_SOFT}; color: {t.PRIMARY}; }}
    QLineEdit, QComboBox, QSpinBox {{ background: {t.SURFACE}; border: 1px solid {t.BORDER}; border-radius: 10px; padding: 8px 10px; min-height: 22px; }}
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{ border: 1px solid {t.PRIMARY}; }}
    QCheckBox {{ spacing: 8px; }}
    QTableWidget {{ background: {t.SURFACE}; border: 1px solid {t.BORDER}; border-radius: 12px; gridline-color: {t.BORDER}; selection-background-color: {t.PRIMARY_SOFT}; }}
    QHeaderView::section {{ background: {t.SURFACE_2}; padding: 10px; border: none; border-bottom: 1px solid {t.BORDER}; font-weight: 650; color: {t.MUTED}; }}
    QTextEdit {{ background: {t.SURFACE}; border: 1px solid {t.BORDER}; border-radius: 12px; padding: 10px; }}
    QProgressBar {{ border: none; background: #EEF2F7; border-radius: 4px; height: 8px; text-align: center; }}
    QProgressBar::chunk {{ background: {t.PRIMARY}; border-radius: 4px; }}
    '''

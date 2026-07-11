from __future__ import annotations

import sys
import time
from pathlib import Path

from PySide6.QtCore import QUrl, Qt
from PySide6.QtWidgets import QApplication, QMainWindow

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtWebEngineCore import QWebEngineProfile
    from PySide6.QtWebChannel import QWebChannel
    WEBENGINE_AVAILABLE = True
except Exception:  # pragma: no cover - depends on local PySide6 installation
    WEBENGINE_AVAILABLE = False
    QWebEngineView = None  # type: ignore
    QWebEngineProfile = None  # type: ignore
    QWebChannel = None  # type: ignore

from core.config import ensure_settings_file
from ui_web.bridge import WebBridge


class WebMainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("LohnMail v2 — Enterprise Edition")
        self.setMinimumSize(1180, 760)
        self._fit_to_screen()

        if not WEBENGINE_AVAILABLE:
            raise RuntimeError(
                "PySide6 WebEngine is not available. Install PySide6-Addons or use LOHNMAIL_UI=widgets."
            )

        self.view = QWebEngineView(self)
        self._disable_web_cache()
        self.bridge = WebBridge(self)
        self.channel = QWebChannel(self.view.page())
        self.channel.registerObject("lohnmailBridge", self.bridge)
        self.view.page().setWebChannel(self.channel)

        html_path = Path(__file__).resolve().parents[1] / "web" / "index.html"
        url = QUrl.fromLocalFile(str(html_path))
        url.setQuery(f"v={int(time.time())}")
        self.view.setUrl(url)
        self.setCentralWidget(self.view)

    def _disable_web_cache(self) -> None:
        profile = self.view.page().profile()
        if hasattr(profile, "clearHttpCache"):
            profile.clearHttpCache()
        if QWebEngineProfile is None:
            return
        no_cache = getattr(QWebEngineProfile, "NoCache", None)
        if no_cache is None and hasattr(QWebEngineProfile, "HttpCacheType"):
            no_cache = getattr(QWebEngineProfile.HttpCacheType, "NoCache", None)
        if no_cache is not None and hasattr(profile, "setHttpCacheType"):
            profile.setHttpCacheType(no_cache)

    def _fit_to_screen(self) -> None:
        screen = QApplication.primaryScreen()
        if screen is None:
            self.resize(1440, 900)
            return
        available = screen.availableGeometry()
        width = min(1440, max(1180, int(available.width() * 0.92)))
        height = min(920, max(760, int(available.height() * 0.90)))
        self.resize(width, height)
        frame = self.frameGeometry()
        frame.moveCenter(available.center())
        self.move(frame.topLeft())


def run() -> int:
    ensure_settings_file()
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("LohnMail")
    app.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings, True)
    window = WebMainWindow()
    window.show()
    return app.exec()

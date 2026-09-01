from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path
from typing import Any, Callable

import webview

from core.config import (
    ensure_settings_file,
    get_company_email_excel_file,
    load_settings,
    save_settings,
)
from core.license_manager import LicenseManager
from ui_web.bridge import WebBridge
from ui_web.version import APP_VERSION


ROOT = Path(__file__).resolve().parent
HTML_PATH = ROOT / "web" / "index.html"
WINDOWS_ICON_PATH = HTML_PATH.parent / "assets" / "brand" / "LohnMail.ico"
SIGNALS = (
    "pageChanged",
    "processingStateChanged",
    "processingProgress",
    "processingFinished",
    "processingError",
    "shippingStateChanged",
    "shippingProgress",
    "shippingFinished",
    "shippingError",
    "massMessageStateChanged",
    "massMessageProgress",
    "massMessageFinished",
    "massMessageError",
    "updateStateChanged",
    "updateProgress",
)


class ApiAdapter:
    """Expose the LohnMail bridge through pywebview's Promise based API."""

    def __init__(self, bridge: WebBridge) -> None:
        self._bridge = bridge
        self._window: webview.Window | None = None

    def attach_window(self, window: webview.Window) -> None:
        self._window = window

    def _processing_payload_after_selection(self) -> str:
        settings = load_settings()
        payload = self._bridge._processing_payload(settings)
        serialized = json.dumps(payload, ensure_ascii=False)
        self._bridge.processingStateChanged.emit(serialized)
        self._bridge.shippingStateChanged.emit(
            json.dumps(self._bridge._shipping_payload(settings), ensure_ascii=False)
        )
        return serialized

    def choosePdfInput(self) -> str:
        settings = load_settings()
        if self._bridge._workflow_running() or self._window is None:
            return self._processing_payload_after_selection()
        ui_settings = settings.get("ui", {})
        mode = self._bridge._pdf_input_mode(settings)
        start_path = self._bridge._dialog_start_path(
            str(ui_settings.get("last_pdf_dialog_dir", "") or "")
        )
        dialog_type = webview.FileDialog.OPEN if mode == "single_pdf" else webview.FileDialog.FOLDER
        file_types = ("PDF files (*.pdf)",) if mode == "single_pdf" else ()
        selected = self._window.create_file_dialog(
            dialog_type,
            directory=start_path,
            allow_multiple=False,
            file_types=file_types,
        )
        if selected:
            selected_path = Path(str(selected[0]))
            settings.setdefault("ui", {})["last_pdf_dir"] = str(selected_path)
            settings["ui"]["last_pdf_input_mode"] = mode
            settings["ui"]["last_pdf_dialog_dir"] = str(
                selected_path if mode == "folder" else selected_path.parent
            )
            self._bridge._set_company_pdf_input(settings, str(selected_path), mode)
            save_settings(settings)
            self._bridge._reset_workflow_state()
        return self._processing_payload_after_selection()

    def chooseExcelInput(self) -> str:
        settings = load_settings()
        if self._bridge._workflow_running() or self._window is None:
            return self._processing_payload_after_selection()
        ui_settings = settings.get("ui", {})
        start_path = self._bridge._dialog_start_path(
            str(ui_settings.get("last_excel_dialog_dir", "") or "")
        )
        selected = self._window.create_file_dialog(
            webview.FileDialog.OPEN,
            directory=start_path,
            allow_multiple=False,
            file_types=("Excel files (*.xlsx;*.xls;*.xlsm)",),
        )
        if selected:
            path = str(selected[0])
            self._bridge._set_company_excel_file(settings, path)
            settings.setdefault("ui", {})["last_excel_file"] = path
            settings["ui"]["last_excel_dialog_dir"] = str(Path(path).parent)
            save_settings(settings)
            self._bridge._reset_workflow_state()
        return self._processing_payload_after_selection()

    def chooseCompanyExcelInput(self) -> str:
        self.chooseExcelInput()
        return json.dumps(self._bridge._company_payload(load_settings()), ensure_ascii=False)

    def createCompany(self, payload: str) -> str:
        try:
            data = json.loads(payload or "{}")
        except Exception:
            data = {}
        choose_excel = bool(data.get("choose_excel")) if isinstance(data, dict) else False
        if isinstance(data, dict):
            data["choose_excel"] = False
        result = json.loads(self._bridge.createCompany(json.dumps(data, ensure_ascii=False)))
        if result.get("ok") and choose_excel:
            self.chooseExcelInput()
            result["state"] = self._bridge._company_payload(load_settings())
        return json.dumps(result, ensure_ascii=False)

    def promptActivateLicenseKey(self) -> str:
        if self._window is None:
            return self._bridge.promptActivateLicenseKey()
        value = self._window.evaluate_js("window.prompt('Lizenzschlüssel eingeben:')")
        if not value:
            return json.dumps(
                {
                    "ok": False,
                    "message": "Aktivierung abgebrochen.",
                    "state": self._bridge._license_payload(load_settings()),
                },
                ensure_ascii=False,
            )
        return self._bridge.activateLicenseKey(str(value))

    def checkForUpdates(self) -> str:
        return json.dumps(self._bridge._update_service.check(), ensure_ascii=False)

    def downloadUpdate(self) -> str:
        state = self._bridge._update_service.download(progress=self._bridge._on_update_progress)
        self._bridge._on_update_finished(state)
        return json.dumps(state, ensure_ascii=False)

    def installUpdateNow(self) -> str:
        self._bridge._update_service.set_preferences(install_on_exit=True)
        result = self._bridge._update_service.install_on_exit()
        if result.get("started") and self._window is not None:
            self._window.destroy()
        return json.dumps(result, ensure_ascii=False)


def _proxy_method(name: str) -> Callable[..., Any]:
    def call(self: ApiAdapter, *args: Any) -> Any:
        return getattr(self._bridge, name)(*args)

    call.__name__ = name
    call.__qualname__ = f"ApiAdapter.{name}"
    return call


for _name, _member in inspect.getmembers(WebBridge, predicate=callable):
    if (
        not _name.startswith("_")
        and _name not in {"deleteLater", "destroyed"}
        and not hasattr(ApiAdapter, _name)
    ):
        setattr(ApiAdapter, _name, _proxy_method(_name))


def _forward_signals(window: webview.Window, bridge: WebBridge) -> None:
    def connect(name: str) -> None:
        signal = getattr(bridge, name, None)
        if signal is None or not hasattr(signal, "connect"):
            return

        def emit(payload: Any, signal_name: str = name) -> None:
            script = "window.lohnmailReceiveSignal(%s, %s);" % (
                json.dumps(signal_name),
                json.dumps(payload),
            )
            try:
                window.run_js(script)
            except Exception:
                pass

        signal.connect(emit)

    for name in SIGNALS:
        connect(name)


def _set_runtime_app_identity() -> None:
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("LohnMail.Desktop.2")
        except Exception:
            pass
    elif sys.platform == "darwin":
        try:
            import AppKit

            icon_path = HTML_PATH.parent / "assets" / "brand" / "LohnMail.icns"
            icon = AppKit.NSImage.alloc().initWithContentsOfFile_(str(icon_path))
            if icon is not None:
                AppKit.NSApplication.sharedApplication().setApplicationIconImage_(icon)
        except Exception:
            pass


def _set_windows_window_icon(window: webview.Window) -> None:
    """Set small and large native icons, including source launches via python.exe."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        native = getattr(window, "native", None)
        handle_value = getattr(native, "Handle", 0)
        hwnd = int(handle_value.ToInt64()) if hasattr(handle_value, "ToInt64") else int(handle_value)
        if not hwnd or not WINDOWS_ICON_PATH.exists():
            return

        user32 = ctypes.windll.user32
        user32.LoadImageW.restype = ctypes.c_void_p
        user32.SendMessageW.restype = ctypes.c_ssize_t
        image_icon = 1
        load_from_file = 0x0010
        wm_seticon = 0x0080
        for icon_type, size in ((0, 16), (1, 32)):
            icon = user32.LoadImageW(
                None,
                str(WINDOWS_ICON_PATH),
                image_icon,
                size,
                size,
                load_from_file,
            )
            if icon:
                user32.SendMessageW(hwnd, wm_seticon, icon_type, icon)
    except Exception:
        pass


def run() -> None:
    _set_runtime_app_identity()
    ensure_settings_file()
    LicenseManager({}).machine_id()
    bridge = WebBridge()
    api = ApiAdapter(bridge)
    window = webview.create_window(
        f"LohnMail {APP_VERSION} — Enterprise Edition",
        str(HTML_PATH),
        js_api=api,
        width=1440,
        height=900,
        min_size=(1180, 760),
        background_color="#f5f8fb",
    )
    api.attach_window(window)
    _forward_signals(window, bridge)

    def on_closing() -> None:
        try:
            bridge._persist_workflow_session()
            bridge.installUpdateOnExit()
        except Exception:
            pass

    window.events.closing += on_closing
    window.events.loaded += lambda: _set_windows_window_icon(window)
    webview.start(debug=False)


if __name__ == "__main__":
    run()

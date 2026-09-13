"""CI-only native Windows capture of the unchanged desktop UI with synthetic data.

Never shipped with the app. No fake window decorations, image compositing or
upscaling. License/network boundaries are mocked; PDF/Excel validation is real.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import tempfile
import time
import traceback
from contextlib import ExitStack
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "lohnmail-pywebview-test"
OUTPUT = REPO / "artifacts" / "windows-screenshots"


def wait_for(predicate, timeout=60):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.25)
    raise TimeoutError("Native app did not reach the required state")


def main():
    if sys.platform != "win32":
        raise SystemExit("Capture must run on real Windows, not on macOS/Linux")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix="LohnMail-Demo-"))
    os.environ["LOHNMAIL_DATA_DIR"] = str(root)
    os.environ["LOHNMAIL_DISTRIBUTION"] = "store"
    sys.path.insert(0, str(SOURCE))
    # pywebview resolves its initial base URI from argv[0] during import.
    sys.argv[0] = str(Path(__file__).resolve())
    os.chdir(SOURCE)

    import ctypes
    import win32api
    import win32con
    import win32gui
    import webview
    from PIL import ImageGrab, ImageStat
    import fitz
    from openpyxl import Workbook
    from core import config, orchestrator
    from core.license_manager import LicenseManager
    from core.email_validation import validate_email_records

    ctypes.windll.user32.SetProcessDPIAware()
    mode = win32api.EnumDisplaySettings(None, win32con.ENUM_CURRENT_SETTINGS)
    mode.PelsWidth, mode.PelsHeight = 1920, 1080
    display_result = win32api.ChangeDisplaySettings(mode, 0)
    print("Display mode result:", display_result, flush=True)
    screen = (win32api.GetSystemMetrics(0), win32api.GetSystemMetrics(1))
    if screen[0] < 1800 or screen[1] < 1000:
        raise RuntimeError(f"Interactive Windows desktop too small: {screen}")

    pdf_dir = root / "Beispieldaten" / "September-2026"
    pdf_dir.mkdir(parents=True)
    employees = [
        ("01001", "anna.beispiel@example.com", "Beispiel", "Anna"),
        ("01002", "max.muster@example.com", "Muster", "Max"),
        ("01003", "lena.demo@example.com", "Demo", "Lena"),
        ("01004", "", "Beispiel", "Paul"),
        ("01005", "mia.muster@example.com", "Muster", "Mia"),
    ]
    book = Workbook()
    sheet = book.active
    sheet.title = "Mitarbeiter"
    sheet.append(["PersNr", "Email", "Name", "Vorname"])
    for number, email, last, first in employees:
        sheet.append([number, email, last, first])
        with fitz.open() as doc:
            page = doc.new_page()
            for y, text, size in [
                (70, "Musterfirma GmbH - Demonstrationsdaten", 20),
                (115, "Entgeltabrechnung September 2026", 17),
                (160, f"Pers.-Nr. {number}", 13),
                (185, f"{first} {last}", 13),
                (230, "Fiktives Dokument zur Darstellung der Programmfunktionen.", 11),
            ]:
                page.insert_text((55, y), text, fontsize=size)
            doc.save(pdf_dir / f"{number}.pdf")
    excel = root / "Beispieldaten" / "Mitarbeiter.xlsx"
    book.save(excel)
    settings = config.build_default_settings()
    settings["companies"] = [{"id": "musterfirma", "name": "Musterfirma GmbH",
                              "email_excel_file": str(excel), "pdf_input": str(pdf_dir),
                              "pdf_input_mode": "folder"}]
    settings["selected_company_id"] = "musterfirma"
    settings["ui"].update(last_pdf_dir=str(pdf_dir), last_excel_file=str(excel), dry_run_default=True)
    settings["updates"]["auto_check"] = False
    settings["smtp"].update(server="smtp.example.com", username="personal@example.com",
                            from_email="personal@example.com")
    config.save_settings(settings)
    state = dict(status="trialing", type="trial", plan="Professional", days_remaining=60,
                 machine_id="demo", license_key="", server="Demo",
                 last_message="Demonstrationsdaten", trial_ends_at="2026-11-12T12:00:00+00:00")

    def blocked(*args, **kwargs):
        raise RuntimeError("External services disabled in screenshot fixture")

    evidence = {"os": platform.platform(), "python": sys.version, "commit": os.getenv("GITHUB_SHA"),
                "capture": "Pillow ImageGrab of native Windows window including real caption",
                "execution": "canonical source, pywebview edgechromium, not installed MSIX",
                "fixtures": "synthetic employees; mocked license; mail/network disabled",
                "desktop": screen, "screenshots": []}
    failures = []
    original_create = webview.create_window
    original_start = webview.start
    captured = {}

    def create(*args, **kwargs):
        kwargs.update(width=1800, height=1000, x=20, y=20)
        window = original_create(*args, **kwargs)
        captured["window"] = window
        captured["bridge"] = kwargs["js_api"]._bridge
        return window

    def capture():
        window = captured["window"]
        try:
            wait_for(lambda: window.evaluate_js(
                "document.querySelector('[data-company-switch=\"name\"]')?.textContent === 'Musterfirma GmbH'"))
            bridge = captured["bridge"]
            bridge.startCheck()
            wait_for(lambda: not bridge._workflow_running())
            evidence["processing"] = json.loads(bridge.getProcessingState())
            hwnd = int(window.native.Handle.ToInt64())
            win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 20, 20, 1800, 1000, 0)
            pages = [("Dashboard", "01-dashboard"), ("Verarbeitung", "02-verarbeitung"),
                     ("Prüfung", "03-pruefung"), ("Versand", "04-versand"),
                     ("Berichte", "05-berichte"), ("Nachricht", "06-nachricht"),
                     ("Unternehmen", "07-unternehmen"), ("Lizenzen", "08-lizenzen"),
                     ("Einstellungen", "09a-general"), ("Einstellungen", "09b-email"),
                     ("Einstellungen", "09c-templates"), ("Einstellungen", "09d-notifications"),
                     ("Einstellungen", "09e-updates"), ("Einstellungen", "09f-security"),
                     ("Einstellungen", "09g-advanced"), ("Hilfe", "10-hilfe"),
                     ("Über LohnMail", "11-ueber-lohnmail")]
            for page, filename in pages:
                window.evaluate_js("[...document.querySelectorAll('.nav-item')].find(b => b.textContent.trim() === "
                                   + json.dumps(page) + ").click()")
                wait_for(lambda: window.evaluate_js("document.querySelector('.page.active')?.dataset.page") == page)
                if page == "Einstellungen":
                    tab = filename.split("-", 1)[1]
                    window.evaluate_js("document.querySelector('[data-settings-tab=\"" + tab + "\"]').click()")
                time.sleep(2)
                # GetWindowRect includes invisible resize margins (desktop pixels).
                # Ask DWM for the actual visible native frame; no image edits.
                from ctypes.wintypes import HWND, RECT
                rect = RECT()
                result = ctypes.windll.dwmapi.DwmGetWindowAttribute(
                    HWND(hwnd), 9, ctypes.byref(rect), ctypes.sizeof(rect))
                if result != 0:
                    raise RuntimeError(f"Cannot determine visible Windows frame: {result}")
                bounds = (rect.left, rect.top, rect.right, rect.bottom)
                if bounds[0] < 0 or bounds[1] < 0 or bounds[2] > screen[0] or bounds[3] > screen[1]:
                    raise RuntimeError(f"Window outside screen: {bounds}")
                img = ImageGrab.grab(bbox=bounds, all_screens=True)
                if img.width < 1366 or img.height < 768 or max(ImageStat.Stat(img).stddev) < 10:
                    raise RuntimeError("Blank or undersized native capture")
                path = OUTPUT / f"{filename}.png"
                img.save(path)
                evidence["screenshots"].append({"file": path.name, "size": img.size,
                    "title": win32gui.GetWindowText(hwnd), "bounds": bounds,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
                print("Captured", path.name, img.size, flush=True)
        except Exception:
            failures.append(traceback.format_exc())
            print(failures[-1], flush=True)
        finally:
            evidence["errors"] = failures
            (OUTPUT / "provenance.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
            window.destroy()

    with ExitStack() as stack:
        for name in ("load_state", "refresh"):
            stack.enter_context(patch.object(LicenseManager, name, lambda self, *a, **k: dict(state)))
        stack.enter_context(patch.object(LicenseManager, "_machine_id", lambda self: "demo"))
        stack.enter_context(patch.object(LicenseManager, "_migrate_legacy_files", lambda self: None))
        stack.enter_context(patch.object(LicenseManager, "_post", blocked))
        for name in ("urllib.request.urlopen", "smtplib.SMTP", "smtplib.SMTP_SSL", "webbrowser.open",
                     "win32com.client.Dispatch"):
            stack.enter_context(patch(name, blocked))
        stack.enter_context(patch.object(orchestrator, "validate_email_records",
            lambda records: validate_email_records(records, check_dns=False)))
        stack.enter_context(patch.object(webview, "create_window", create))
        stack.enter_context(patch.object(webview, "start", lambda **kwargs: original_start(capture, gui="edgechromium", **kwargs)))
        from pywebview_app import run
        run()
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

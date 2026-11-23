"""JSON-line bridge for the isolated UI regression. Never a production entry point."""
import json
import os
import socket
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
temporary = tempfile.TemporaryDirectory(prefix="lohnmail-pdf-ui-")
root = Path(temporary.name)
os.environ["LOHNMAIL_DATA_DIR"] = str(root)


def blocked(*args, **kwargs):
    raise AssertionError("External operation forbidden in UI test")


socket.socket.connect = blocked
socket.create_connection = blocked
socket.getaddrinfo = blocked
from core import config
from core import mailer
from copy import deepcopy
from openpyxl import Workbook
import fitz
from ui_web import bridge as module
config._protect_and_strip_smtp_passwords = deepcopy
config._hydrate_smtp_passwords = deepcopy
mailer.test_smtp_connection = mailer.send_email_with_attachment = blocked
mailer.send_outlook_email_with_attachment = blocked
module.LicenseManager = Mock()
module.UpdateService = Mock()
excel = root / "Mitarbeiter.xlsx"
book = Workbook()
book.active.append(["PersNr", "Email", "Name", "Vorname"])
book.active.append(["00022", "demo@example.invalid", "Mustermann", "Max"])
book.save(excel)
folder = root / "PDF"
folder.mkdir()
example = "Lohnabrechnung_2026_August_00022_Mustermann_Max.pdf"
for name in (example, example.replace("2026_August", "2027_September"),
             "00022_1.pdf", example.replace("00022", "00023"), "Unbekannt.pdf"):
    with fitz.open() as document:
        page = document.new_page()
        page.insert_text((40, 50), "Pers.-Nr. 00023" if "00023" in name else
                         ("Abrechnung ohne Nummer" if name == "Unbekannt.pdf" else "Pers.-Nr. 00022"))
        document.save(folder / name)
settings = config.build_default_settings()
settings.update(selected_company_id="a", companies=[
    {"id": "a", "name": "Musterfirma GmbH", "email_excel_file": str(excel)},
    {"id": "b", "name": "Beispielunternehmen GmbH", "email_excel_file": str(excel)},
])
config.save_settings(settings)
bridge = module.WebBridge()
for line in sys.stdin:
    request = json.loads(line)
    try:
        method, args = request["method"], request.get("args", [])
        if method == "choosePdfFilenameExample":
            result = {"ok": True, "company_id": config.load_settings()["selected_company_id"], "filename": example}
        elif method == "choosePdfFilenameFolder":
            result = json.loads(bridge.checkPdfFilenameFolder(args[0], str(folder)))
        elif method == "switchCompany":
            bridge.selectCompany(args[0])
            result = {"ok": True}
        elif method == "restart":
            bridge = module.WebBridge()
            result = {"ok": True}
        elif method in {"getPdfFilenameState", "previewPdfFilename", "savePdfFilenameRule"}:
            result = json.loads(getattr(bridge, method)(*args))
        else:
            raise ValueError("Unknown test operation")
        print(json.dumps({"id": request["id"], "result": result}), flush=True)
    except Exception as exc:
        print(json.dumps({"id": request["id"], "error": str(exc)}), flush=True)
temporary.cleanup()

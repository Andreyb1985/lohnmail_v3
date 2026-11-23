"""Synthetic preparation/transport failures: never deliver or access the network."""
import errno
import smtplib
import socket
import ssl
from unittest.mock import Mock

import fitz
import pytest
from openpyxl import Workbook, load_workbook
from PyPDF2 import PdfReader, PdfWriter

from core import orchestrator as engine
from core.shipping_errors import ERRORS, ShippingError, describe_shipping_error


@pytest.mark.parametrize("exc,stage,code", [
    (ShippingError("BIRTH_DATE_MISSING"), "prepare", "BIRTH_DATE_MISSING"),
    (PermissionError("private path"), "encrypt", "FILE_ACCESS"),
    (FileNotFoundError("private path"), "read", "FILE_MISSING"),
    (OSError(errno.ENOSPC, "private path"), "encrypt", "DISK_FULL"),
    (OSError(errno.EIO, "private path"), "merge", "FILE_IO"),
    (RuntimeError("secret"), "merge", "PDF_MERGE"),
    (RuntimeError("secret"), "encrypt", "PDF_ENCRYPTION"),
    (RuntimeError("secret"), "read", "PDF_UNREADABLE"),
    (RuntimeError("secret"), "prepare", "PREPARATION_FAILED"),
    (RuntimeError("secret"), "send", "MAIL_FAILED"),
    (smtplib.SMTPAuthenticationError(535, b"secret"), "send", "SMTP_AUTH"),
    (socket.gaierror("secret"), "send", "SMTP_DNS"),
    (TimeoutError("secret"), "send", "SMTP_TIMEOUT"),
    (ssl.SSLError("secret"), "send", "SMTP_TLS"),
    (smtplib.SMTPRecipientsRefused({"private@example.invalid": (550, "secret")}), "send", "SMTP_RECIPIENT"),
    (smtplib.SMTPSenderRefused(550, "secret", "private@example.invalid"), "send", "SMTP_SENDER"),
    (smtplib.SMTPDataError(552, "secret"), "send", "SMTP_DATA"),
    (smtplib.SMTPServerDisconnected("secret"), "send", "MAIL_CONNECTION"),
])
def test_actionable_error_mapping_does_not_expose_exception_data(exc, stage, code):
    wrapper = RuntimeError("private wrapped error")
    wrapper.__cause__ = exc
    result = describe_shipping_error(wrapper, stage)
    assert result["ErrorCode"] == code
    assert result["ErrorTitle"] and result["ErrorAction"]
    assert not any(value in result["Error"] for value in ("secret", "private", "535", "552"))


@pytest.fixture
def scenario(tmp_path, monkeypatch):
    monkeypatch.setattr(socket.socket, "connect", Mock(side_effect=AssertionError("Network forbidden")))
    monkeypatch.setattr("core.diagnostics.record_handled_error", Mock())
    monkeypatch.setattr("core.mailer.test_smtp_connection", Mock())
    monkeypatch.setattr("core.mailer.test_outlook_connection", Mock())
    sender = Mock()
    monkeypatch.setattr("core.mailer.send_email_with_attachment", sender)
    monkeypatch.setattr("core.mailer.send_outlook_email_with_attachment", sender)
    monkeypatch.setattr(engine, "validate_email_records", lambda records: {
        key: {"code": "valid", "email": record["Email"], "sendable": True} for key, record in records.items()
    })
    folder = tmp_path / "input"
    folder.mkdir()
    excel = tmp_path / "employees.xlsx"

    def pdf(name, dates=()):
        doc = fitz.open()
        for birth in dates or [""]:
            page = doc.new_page()
            page.insert_text((50, 60), "Geburtsdatum")
            if birth:
                page.insert_text((50, 74), birth)
        doc.save(folder / name)
        doc.close()

    def run(dates=("", ""), dry=True):
        wb = Workbook()
        wb.active.append(["PersNr", "Email", "Name", "Vorname", "Geburtsdatum"])
        for i, birth in enumerate(dates, 1):
            wb.active.append([str(i).zfill(5), f"test{i}@example.invalid", "Beispiel", f"Person{i}", birth])
        wb.save(excel)
        settings = {"mail_mode": "smtp", "smtp": {}, "pdf_password": {"enabled": True, "source": "birth_date"},
                    "companies": [{"id": "test", "name": "Beispiel"}], "selected_company_id": "test"}
        events = []
        result = engine.action_send(folder, excel, settings, "test", dry_run=dry,
                                    progress_cb=events.append, output_dir=tmp_path / "output")
        return result, events

    return pdf, run, sender, folder


@pytest.mark.parametrize("dry", [True, False])
@pytest.mark.parametrize("fallback", [False, True])
def test_missing_birth_date_blocks_attachment_and_delivery_but_keeps_valid_recipient(scenario, dry, fallback):
    pdf, run, sender, _ = scenario
    pdf("00001.pdf")
    pdf("00002.pdf")
    result, events = run(("03.02.1990" if fallback else "", ""), dry)
    rows = result["table_rows"]
    assert result["summary"]["failed_count"] == (1 if fallback else 2)
    assert sender.call_count == (1 if fallback and not dry else 0)
    bad = rows[-1]
    assert bad["ErrorCode"] == "BIRTH_DATE_MISSING"
    assert not bad["Attachment"] and not bad["Password"]
    assert "Im PDF wurde kein Geburtsdatum erkannt" in bad["ErrorAction"]
    assert "Auch in der Excel-Liste" in bad["ErrorAction"]
    assert "Spalte „Geburtsdatum“ bei der passenden Personalnummer" in bad["ErrorAction"]
    assert "Vorbereitung erneut starten" in bad["ErrorAction"]
    assert "nicht gesendet" in bad["ErrorAction"]
    assert not list(result["run_dir"].rglob("00002_protected.pdf"))
    last = [e for e in events if isinstance(e, dict) and e.get("persnr") == "00002"][-1]
    assert last["status"] == "error" and "Geburtsdatum" in last["operation"]
    assert "wurde vorbereitet" not in last["operation"]
    report = load_workbook(result["send_report_path"], data_only=True)
    assert any(bad["ErrorAction"] in str(cell) for row in report.active.values for cell in row)
    if fallback:
        output = next(result["run_dir"].rglob("00001_protected.pdf"))
        protected = PdfReader(output)
        assert protected.is_encrypted and protected.decrypt("03021990")


@pytest.mark.parametrize("dry", [True, False])
def test_pdf_excel_mismatch_blocks_all_employee_documents_and_keeps_others(scenario, dry):
    pdf, run, sender, _ = scenario
    pdf("00001.pdf", ["030290"])
    pdf("00001_1.pdf", ["030290"])
    pdf("00002.pdf", ["040391"])
    result, events = run(("04.03.1991", "04.03.1991"), dry)
    bad, good = result["table_rows"]
    assert bad["ErrorCode"] == "BIRTH_DATE_MISMATCH"
    assert "PDF und Excel" in bad["ErrorTitle"]
    assert "Personalnummer" in bad["ErrorAction"] and "nicht gesendet" in bad["ErrorAction"]
    assert not bad["Attachment"] and not bad["Password"]
    assert "03021990" not in bad["Error"] and "04031991" not in bad["Error"]
    assert not list(result["run_dir"].rglob("00001_protected.pdf"))
    assert result["summary"]["failed_count"] == 1
    assert good["Status"] == ("Dry-Run" if dry else "Gesendet")
    assert sender.call_count == (0 if dry else 1)
    protected = PdfReader(next(result["run_dir"].rglob("00002_protected.pdf")))
    assert protected.is_encrypted and protected.decrypt("04031991")
    assert any(e.get("persnr") == "00001" and e.get("status") == "error"
               and "PDF und Excel" in e.get("operation", "") for e in events if isinstance(e, dict))
    report = load_workbook(result["send_report_path"], data_only=True)
    assert any(bad["ErrorAction"] in str(cell) for row in report.active.values for cell in row)


@pytest.mark.parametrize("pdf_date,excel_date", [
    ("030290", "03.02.1990"), ("030290", ""), ("", "03.02.1990"),
    ("030290", "kein Datum"),
])
def test_matching_or_single_valid_birth_date_prepares_protected_pdf(scenario, pdf_date, excel_date):
    pdf, run, sender, _ = scenario
    pdf("00001.pdf", [pdf_date])
    result, _ = run((excel_date,), dry=True)
    assert result["summary"]["failed_count"] == 0
    protected = PdfReader(next(result["run_dir"].rglob("00001_protected.pdf")))
    assert protected.is_encrypted and protected.decrypt("03021990")
    sender.assert_not_called()


@pytest.mark.parametrize("settings,expected", [
    ({"enabled": False, "source": "birth_date"}, ""),
    ({"enabled": True, "source": "persnr"}, "00001"),
])
def test_birth_date_mismatch_does_not_affect_other_password_modes(settings, expected):
    assert engine._pdf_password_for_employee(settings, "00001", {
        "PdfGeburtsdatum": "03021990", "Geburtsdatum": "04031991",
    }) == expected


@pytest.mark.parametrize("across_files", [False, True])
def test_conflicting_pdf_birth_dates_block_without_leaking_dates(scenario, across_files):
    pdf, run, sender, _ = scenario
    pdf("00001.pdf", ["030290"] if across_files else ["030290", "040391"])
    if across_files:
        pdf("00001_1.pdf", ["040391"])
    result, _ = run(("03.02.1990",), dry=False)
    row = result["table_rows"][0]
    assert row["ErrorCode"] == "BIRTH_DATE_CONFLICT"
    assert "03021990" not in row["Error"] and "04031991" not in row["Error"]
    assert not row["Attachment"]
    sender.assert_not_called()


@pytest.mark.parametrize("failure,code", [(PermissionError(), "FILE_ACCESS"),
    (OSError(errno.ENOSPC, "full"), "DISK_FULL"), (RuntimeError(), "PDF_ENCRYPTION")])
def test_encryption_failure_never_sends_unprotected_document(scenario, monkeypatch, failure, code):
    pdf, run, sender, _ = scenario
    pdf("00001.pdf", ["030290"])
    monkeypatch.setattr(engine, "_encrypt_pdf", Mock(side_effect=failure))
    result, _ = run(("",), dry=False)
    assert result["table_rows"][0]["ErrorCode"] == code
    assert not result["table_rows"][0]["Attachment"]
    sender.assert_not_called()


@pytest.mark.parametrize("kind,code", [("locked", "PDF_LOCKED"), ("empty", "PDF_EMPTY"), ("corrupt", "PDF_UNREADABLE")])
def test_input_pdf_failures_are_distinguished(tmp_path, kind, code):
    path = tmp_path / "00001.pdf"
    writer = PdfWriter()
    if kind == "locked":
        writer.add_blank_page(width=100, height=100)
        writer.encrypt("synthetic")
    if kind == "corrupt":
        path.write_bytes(b"not a PDF")
    else:
        with path.open("wb") as stream:
            writer.write(stream)
    result = engine._validate_grouped_pdf_files({"00001": [path]})
    assert result["error_details"][0]["ErrorCode"] == code
    assert not result["valid_grouped"]


def test_failed_encryption_write_is_not_published(tmp_path, monkeypatch):
    source, target = tmp_path / "in.pdf", tmp_path / "protected.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    with source.open("wb") as stream:
        writer.write(stream)
    def interrupted(self, stream):
        stream.write(b"partial")
        raise OSError(errno.ENOSPC, "full")
    monkeypatch.setattr(PdfWriter, "write", interrupted)
    with pytest.raises(OSError):
        engine._encrypt_pdf(source, target, "synthetic")
    assert not target.exists() and not list(tmp_path.glob("*.encrypting"))
    with pytest.raises(ShippingError):
        engine._encrypt_pdf(source, target, "")


def test_every_catalog_entry_has_a_concrete_title_and_action():
    assert all(title and action and title != "Fehler" for title, action in ERRORS.values())

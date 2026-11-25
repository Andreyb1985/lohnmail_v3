"""Synthetic DATEV layout: headings and values in different PDF text objects."""
from pathlib import Path
from unittest.mock import Mock

import fitz
import pytest
from openpyxl import Workbook
from PyPDF2 import PdfReader

from core import orchestrator
from core.input_scan import scan_pdf_folder
from core.pdf_content import recognize_pdf_content


def social_pdf(path: Path, number="00022", address_number="00022", *, reverse=False):
    # Preserve the problematic text-object order, not any real employee data.
    headings = [
        ((40, 55), "Meldebescheinigung zur Sozialversicherung"),
        ((325, 96), "Pers.-Nr."),
        ((448, 55), "Datum:"),
        ((448, 65), "Seite:"),
        ((325, 123), "Versicherungsnummer"),
        ((465, 123), "Geburtsdatum"),
        ((405, 96), "Erstellungs-/Uebermittlungsdatum"),
    ]
    values = [((328, 107), number), ((490, 55), "23.11.2026"),
              ((490, 65), "1"), ((325, 134), "12123456A123"),
              ((405, 107), "23.11.2026 / 17:41")]
    if address_number is not None:
        values.append(((60, 174), f"*Pers.-Nr. {address_number}*"))
    with fitz.open() as doc:
        page = doc.new_page()
        for point, text in (values + headings if reverse else headings + values):
            if text is not None:
                page.insert_text(point, text, fontsize=8)
        doc.save(path)
    return path


@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("address_number", ["00022", None])
def test_social_form_recognizes_separate_field_value(tmp_path, reverse, address_number):
    path = social_pdf(tmp_path / "social.pdf", address_number=address_number, reverse=reverse)
    assert recognize_pdf_content(path)["persnr"] == "00022"
    folder = scan_pdf_folder(tmp_path, {"mode": "content"}, {"00022": {}})
    assert folder["valid_pdf_files"] == 1 and not folder["filename_errors"]
    total = orchestrator._prepare_pdf_input(path, tmp_path / "run")
    assert set(total["grouped"]) == {"00022"} and not total["filename_errors"]


@pytest.mark.parametrize("field,address,reason", [
    ("00023", "00022", "unterschiedliche"),
    ("000022", "00022", "nicht eindeutig"),
    ("22abc", "00022", "nicht eindeutig"),
    (None, None, "nicht eindeutig"),
])
def test_social_form_never_ignores_invalid_or_conflicting_field(tmp_path, field, address, reason):
    path = social_pdf(tmp_path / "social.pdf", field, address)
    result = recognize_pdf_content(path)
    assert not result["persnr"] and reason in result["reason"]
    total = orchestrator._prepare_pdf_input(path, tmp_path / "run")
    assert not total["grouped"] and reason in total["filename_errors"][0]["reason"]


def test_social_forms_multiple_documents_and_conflict_are_kept_separate(tmp_path):
    payroll = tmp_path / "payroll.pdf"
    with fitz.open() as doc:
        doc.new_page().insert_text((40, 50), "*Pers.-Nr. 00022*\nLohnabrechnung")
        doc.save(payroll)
    sources = [payroll, social_pdf(tmp_path / "social-a.pdf"),
               social_pdf(tmp_path / "social-b.pdf"),
               social_pdf(tmp_path / "other.pdf", "00023", "00023"),
               social_pdf(tmp_path / "conflict.pdf", "00023", "00022")]
    originals = {p: p.read_bytes() for p in sources}
    folder = scan_pdf_folder(tmp_path, {"mode": "content"}, {"00022": {}, "00023": {}})
    assert {k: len(v) for k, v in folder["grouped"].items()} == {"00022": 3, "00023": 1}
    assert len(folder["filename_errors"]) == 1
    total_path = tmp_path / "total.pdf"
    with fitz.open() as total:
        for source in sources:
            with fitz.open(source) as doc:
                total.insert_pdf(doc)
        total.save(total_path)
    split = orchestrator._prepare_pdf_input(total_path, tmp_path / "run")
    assert {k: len(v) for k, v in split["grouped"].items()} == {"00022": 3, "00023": 1}
    assert len(split["filename_errors"]) == 1
    assert all(p.read_bytes() == data for p, data in originals.items())


def test_compact_payroll_value_overlaps_heading_font_box(tmp_path):
    path = tmp_path / "payroll.pdf"
    with fitz.open() as doc:
        page = doc.new_page()
        # Different fonts have overlapping bounding boxes despite separate
        # printed baselines. Do not accidentally pick the next SV-Nummer label.
        page.insert_text((42, 64), "Personal-Nr.", fontsize=6)
        page.insert_text((81, 64), "Geburtsdatum", fontsize=6)
        page.insert_text((42, 81), "SV-Nummer", fontsize=6)
        page.insert_text((42, 72), "00022", fontname="cour", fontsize=9)
        page.insert_text((81, 72), "010180", fontname="cour", fontsize=9)
        page.insert_text((42, 89), "12010180A123", fontname="cour", fontsize=9)
        page.insert_text((60, 174), "*Pers.-Nr. 00022*", fontsize=8)
        doc.save(path)
    assert recognize_pdf_content(path)["persnr"] == "00022"


def test_multiple_values_below_heading_are_not_chosen_arbitrarily(tmp_path):
    path = social_pdf(tmp_path / "social.pdf", "00022 00023")
    result = recognize_pdf_content(path)
    assert not result["persnr"] and "nicht eindeutig" in result["reason"]


def test_adjacent_value_is_not_overwritten_by_unrelated_number_below(tmp_path):
    path = tmp_path / "inline.pdf"
    with fitz.open() as doc:
        page = doc.new_page()
        page.insert_text((40, 50), "Personalnummer:", fontsize=8)
        page.insert_text((130, 50), "00022", fontsize=8)
        page.insert_text((40, 64), "2026", fontsize=8)
        doc.save(path)
    assert recognize_pdf_content(path)["persnr"] == "00022"


@pytest.mark.parametrize("mode", ["folder", "single_pdf"])
def test_check_prepare_and_mock_send_include_social_forms(tmp_path, monkeypatch, mode):
    from core import mailer
    folder = tmp_path / "input"
    folder.mkdir()
    social_pdf(folder / "social-a.pdf")
    social_pdf(folder / "social-b.pdf")
    social_pdf(folder / "other.pdf", "00023", "00023")
    with fitz.open() as doc:
        doc.new_page().insert_text((40, 50), "*Pers.-Nr. 00022*\nLohnabrechnung")
        doc.save(folder / "payroll.pdf")
    source = folder
    if mode == "single_pdf":
        source = tmp_path / "all.pdf"
        with fitz.open() as doc:
            for path in sorted(folder.iterdir()):
                with fitz.open(path) as part:
                    doc.insert_pdf(part)
            doc.save(source)
    wb = Workbook()
    wb.active.append(["PersNr", "Email", "Name", "Vorname"])
    for nr in (22, 23):
        wb.active.append([nr, f"test{nr}@example.invalid", "Muster", "Test"])
    excel = tmp_path / "employees.xlsx"
    wb.save(excel)
    monkeypatch.setattr(orchestrator, "validate_email_records", lambda records: {
        k: {"sendable": True, "email": v["Email"], "label": "OK", "code": "valid"}
        for k, v in records.items()})
    connection, transport = Mock(), Mock()
    monkeypatch.setattr(mailer, "test_smtp_connection", connection)
    monkeypatch.setattr(mailer, "send_email_with_attachment", transport)
    monkeypatch.setattr(mailer, "test_outlook_connection", Mock(side_effect=AssertionError("No Outlook")))
    monkeypatch.setattr(mailer, "send_outlook_email_with_attachment", Mock(side_effect=AssertionError("No Outlook")))
    rule = {"mode": "content"}
    settings = {"selected_company_id": "test", "companies": [{"id": "test", "pdf_filename_rule": rule}],
                "mail_mode": "smtp", "smtp": {"from_email": "sender@example.invalid"},
                "pdf_password": {"enabled": True, "mode": "persnr"}}
    checked = orchestrator.action_check(source, excel, output_dir=tmp_path / "check", filename_rule=rule)
    assert checked["summary"]["valid_pdf_files"] == 4 and not checked["filename_errors"]
    prepared = orchestrator.action_send(source, excel, settings, dry_run=True,
                                        allowed_persnr={"00022"}, output_dir=tmp_path / "prepare")
    connection.assert_not_called()
    transport.assert_not_called()
    row = prepared["table_rows"][0]
    assert row["Count"] == 3 and row["Status"] == "Dry-Run"
    reader = PdfReader(str(prepared["run_dir"] / "prepared_pdfs" / row["Attachment"]))
    assert reader.decrypt("00022") and len(reader.pages) == 3
    texts = [p.extract_text() for p in reader.pages]
    assert sum("Meldebescheinigung" in t for t in texts) == 2
    assert sum("Lohnabrechnung" in t for t in texts) == 1
    assert all("00023" not in t for t in texts)
    sent = orchestrator.action_send(source, excel, settings, dry_run=False,
                                    allowed_persnr={"00022"}, output_dir=tmp_path / "mock-send")
    transport.assert_called_once()
    assert transport.call_args.kwargs["to_email"] == "test22@example.invalid"
    assert sent["table_rows"][0]["Status"] == "Gesendet"
    reader = PdfReader(str(transport.call_args.kwargs["attachment_path"]))
    assert reader.decrypt("00022") and len(reader.pages) == 3

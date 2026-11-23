"""Synthetic payroll only. No network, mail, credentials or production state."""
import hashlib
import json
import sqlite3
import subprocess
import sys
import types
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock

import pytest
import fitz
from openpyxl import Workbook
from PyPDF2 import PdfWriter, PdfReader

from core import config, jobs, orchestrator
from core.excel_io import load_email_records
from core.input_scan import scan_pdf_folder
from core.pdf_filename import company_rule, match_filename, recognize_filename, validate_rule
from core.pdf_content import recognize_pdf_content, recognize_personnel_text
from ui_web import bridge as bridge_module
from ui_web.bridge import WebBridge
from ui_web.workflow_sessions import WorkflowSessionStore


RULE = {"mode": "custom", "separator": "_", "index": 3, "parts": 6}
EXAMPLE = "Lohnabrechnung_2026_August_00022_Mustermann_Max.pdf"


def workbook(path, rows=None):
    wb = Workbook()
    ws = wb.active
    ws.append(["PersNr", "Email", "Name", "Vorname"])
    for row in rows or [[22, "demo@example.invalid", "Mustermann", "Max"]]:
        ws.append(row)
    wb.save(path)
    return path


def pdf(path):
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    with path.open("wb") as stream:
        writer.write(stream)
    return path


def text_pdf(path, pages):
    with fitz.open() as document:
        for text in pages:
            page = document.new_page()
            if text:
                page.insert_text((40, 50), text)
        document.save(path)
    return path


@pytest.mark.parametrize("label", ["Pers.-Nr.", "Personalnummer:", "Personal-Nr.", "Personalnr."])
def test_content_recognition_all_pages_and_leading_zeros(tmp_path, label):
    path = text_pdf(tmp_path / "arbitrary.pdf", [f"{label} 22", f"{label}\n00022"])
    assert recognize_pdf_content(path) == {"persnr": "00022", "reason": "", "source": "PDF-Inhalt"}


@pytest.mark.parametrize("text,number,reason", [
    ("*Pers.-Nr. 03028*", "03028", ""),
    ("Pers.-Nr.03028*", "03028", ""),
    ("Personal-Nr. Geburtsdatum\n03028 01011980\n*Pers.-Nr. 03028*", "03028", ""),
    ("Personal-Nr.\nGeburtsdatum\n*Pers.-Nr. 03028*", "03028", ""),
    ("*Pers.-Nr. 22*\nPersonalnummer: 00022", "00022", ""),
    ("Personal-Nr. Geburtsdatum\n03028 01011980", "", "keine gekennzeichnete"),
    ("Personalnummern: 03028", "", "keine gekennzeichnete"),
    ("*Pers.-Nr. 03028*\nPersonalnummer: 03029", "", "unterschiedliche"),
    ("*Pers.-Nr. 03028*03029", "", "nicht eindeutig"),
    ("*Pers.-Nr. 030280*", "", "nicht eindeutig"),
    ("*Pers.-Nr. 03028*\nPersonalnummer: 22abc", "", "nicht eindeutig"),
    ("Personal-Nr. Unbekannt\n*Pers.-Nr. 03028*", "", "nicht eindeutig"),
])
def test_folder_and_total_pdf_share_safe_personnel_parser(tmp_path, text, number, reason):
    path = text_pdf(tmp_path / "sample.pdf", [text])
    parsed = recognize_personnel_text(text)
    folder = recognize_pdf_content(path)
    assert parsed["persnr"] == folder["persnr"] == number
    assert reason in parsed["reason"] and reason in folder["reason"]
    total = orchestrator._prepare_pdf_input(path, tmp_path / "run")
    assert list(total["grouped"]) == ([number] if number else [])
    assert orchestrator._extract_persnr_from_pdf(path) == (number or None)
    if reason:
        assert reason in total["filename_errors"][0]["reason"]
        assert "Original-PDF, Seite 1" in total["filename_errors"][0]["reason"]


def test_total_pdf_splits_employees_but_folder_rejects_mixed_document(tmp_path):
    source = text_pdf(tmp_path / "total.pdf", [
        "*Pers.-Nr. 00022*\nDocument A",
        "Personal-Nr. Geburtsdatum\n*Pers.-Nr. 00023*\nDocument B",
        "Personalnummer: 22\nDocument C",
        "Pers.-Nr. 00022\nPersonalnummer: 00023\nAmbiguous",
    ])
    original = source.read_bytes()
    assert "unterschiedliche" in recognize_pdf_content(source)["reason"]
    result = orchestrator._prepare_pdf_input(source, tmp_path / "run")
    assert {key: len(paths) for key, paths in result["grouped"].items()} == {"00022": 2, "00023": 1}
    assert len(result["filename_errors"]) == 1
    assert "Original-PDF, Seite 4" in result["filename_errors"][0]["reason"]
    assert "unterschiedliche" in result["filename_errors"][0]["reason"]
    assert source.read_bytes() == original


@pytest.mark.parametrize("pages,reason", [
    (["Abrechnung 2026 / 00022"], "keine gekennzeichnete"),
    ([""], "kein lesbarer Text"),
    (["Pers.-Nr. 00022", ""], "Seite 2"),
    (["Pers.-Nr. 00022", "Fortsetzung ohne Nummer"], "Seite 2"),
    (["Pers.-Nr. 00022", "Pers.-Nr. 00023"], "unterschiedliche"),
    (["Pers.-Nr. 00022\nPersonalnummer: 00023"], "unterschiedliche"),
    (["Pers.-Nr. 000022"], "nicht eindeutig"),
    (["Personalnummer: 22.5"], "nicht eindeutig"),
    (["Personalnummer: 22abc"], "nicht eindeutig"),
])
def test_content_rejects_ambiguous_unlabelled_or_missing_numbers(tmp_path, pages, reason):
    result = recognize_pdf_content(text_pdf(tmp_path / "00022.pdf", pages))
    assert not result["persnr"] and reason in result["reason"]


def test_content_never_falls_back_to_filename_and_handles_unreadable(tmp_path):
    broken = tmp_path / "00022.pdf"
    broken.write_bytes(b"not a PDF")
    assert "beschädigt" in recognize_pdf_content(broken)["reason"]
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.encrypt("test-only")
    locked = tmp_path / "00022_1.pdf"
    with locked.open("wb") as stream:
        writer.write(stream)
    assert "passwortgeschützt" in recognize_pdf_content(locked)["reason"]
    assert recognize_filename("00022.pdf", {"mode": "content"})["persnr"] == ""
    assert not scan_pdf_folder(tmp_path, {"mode": "content"}, {"00022": {}})["grouped"]


def test_content_uses_text_not_filename_and_checks_excel(tmp_path):
    text_pdf(tmp_path / "00099.pdf", ["Pers.-Nr. 00022"])
    text_pdf(tmp_path / "anything.pdf", ["Pers.-Nr. 00023"])
    result = scan_pdf_folder(tmp_path, {"mode": "content"}, {"00022": {"Name": "Demo"}})
    assert list(result["grouped"]) == ["00022"]
    assert result["grouped"]["00022"][0].name == "00099.pdf"
    assert "nicht in der Excel" in result["filename_errors"][0]["reason"]


@pytest.mark.parametrize("name", [
    EXAMPLE, "Lohnabrechnung_2027_Januar_22_Anders_Erika.PDF",
    "Gehaltsabrechnung_2028_Dezember_00022_Von Muster_Anna-Maria.pdf",
    "00022.pdf", "22_1.pdf", "00022_2.PDF",
])
def test_structural_rule_and_standard_fallback(name):
    assert recognize_filename(name, RULE) == {"persnr": "00022", "reason": ""}


@pytest.mark.parametrize("name", [
    "Lohnabrechnung_2026_August_Mustermann_00022_Max.pdf",
    "Lohnabrechnung_2026_00022_Mustermann_Max.pdf",
    "Lohnabrechnung_2026_August_000022_Mustermann_Max.pdf",
    "Lohnabrechnung_2026_August_22.0_Mustermann_Max.pdf",
    "Lohnabrechnung_2026_August_00022__Max.pdf",
    "../00022.pdf", "Lohnabrechnung_2026_August_00022_Mustermann_Max.pdf.exe",
])
def test_no_guessing_when_structure_or_selected_number_is_invalid(name):
    result = recognize_filename(name, RULE)
    assert not result["persnr"] and result["reason"]


def test_old_settings_standard_and_bad_rules_fail_closed():
    assert company_rule({}) == {"mode": "standard"}
    assert recognize_filename("00022_3.pdf")["persnr"] == "00022"
    assert recognize_filename(EXAMPLE)["reason"]
    for value in ["custom", {}, {"mode": "other"}, {**RULE, "index": True}, {**RULE, "separator": "."}]:
        with pytest.raises(ValueError):
            validate_rule(value)


def test_ambiguous_standard_and_custom_interpretations_are_rejected():
    rule = {"mode": "custom", "separator": "_", "index": 1, "parts": 2}
    result = recognize_filename("00022_1.pdf", rule)
    assert not result["persnr"] and "Mehrdeutig" in result["reason"]
    assert recognize_filename("00022.pdf", rule)["persnr"] == "00022"
    assert recognize_filename("Abrechnung_00022.pdf", rule)["persnr"] == "00022"


def test_unknown_and_duplicate_numbers_not_assigned(tmp_path):
    records = load_email_records(workbook(tmp_path / "employees.xlsx"))
    assert match_filename(EXAMPLE, RULE, records)["employee"] == "Max Mustermann"
    result = match_filename(EXAMPLE.replace("00022", "00023"), RULE, records)
    assert not result["matched"] and "nicht in der Excel" in result["reason"]
    workbook(tmp_path / "duplicate.xlsx", [[22, "a@example.invalid", "One", "A"],
                                         ["00022", "", "Two", "B"]])
    with pytest.raises(ValueError, match="Doppelte PersNr"):
        load_email_records(tmp_path / "duplicate.xlsx")


def test_scan_grouping_case_suffix_and_originals_unchanged(tmp_path):
    names = ["00022_2.pdf", "00022.pdf", "00022_1.PDF", EXAMPLE,
             EXAMPLE.replace("August", "September"), "bad.pdf", EXAMPLE.replace("00022", "00023")]
    for name in names:
        (tmp_path / name).write_bytes(b"synthetic scan only")
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    scan = scan_pdf_folder(tmp_path, RULE, {"00022": {"Name": "Muster"}})
    assert scan["total_pdf_files"] == 7 and scan["valid_pdf_files"] == 5
    assert [p.name for p in scan["grouped"]["00022"]][:3] == ["00022.pdf", "00022_1.PDF", "00022_2.pdf"]
    assert len(scan["filename_errors"]) == 2
    assert before == {p.name: p.read_bytes() for p in tmp_path.iterdir()}


@pytest.fixture
def environment(tmp_path, monkeypatch):
    """Use actual settings serialization and workflow persistence in isolated data."""
    monkeypatch.setattr(config, "SETTINGS_PATH", tmp_path / "settings.json")
    monkeypatch.setattr(config, "ensure_default_config", lambda: None)
    monkeypatch.setattr(config, "_protect_and_strip_smtp_passwords", deepcopy)
    monkeypatch.setattr(config, "_hydrate_smtp_passwords", deepcopy)
    monkeypatch.setattr(bridge_module, "WorkflowSessionStore",
                        lambda *args: WorkflowSessionStore(tmp_path / "workflows.json"))
    monkeypatch.setattr(bridge_module, "SETTINGS_DIR", tmp_path / "Settings")
    monkeypatch.setattr(WebBridge, "REPORT_HISTORY_PATH", tmp_path / "history.sqlite3")
    monkeypatch.setattr(bridge_module, "LicenseManager", Mock())
    monkeypatch.setattr(bridge_module, "UpdateService", Mock())
    # No mail or DNS during actual check/prepare/send orchestration.
    monkeypatch.setattr(orchestrator, "validate_email_records", lambda records: {
        k: {"sendable": True, "email": v["Email"], "label": "OK", "code": "valid"}
        for k, v in records.items()})
    folder = tmp_path / "input"
    folder.mkdir()
    pdf(folder / EXAMPLE)
    pdf(folder / "00022_1.pdf")
    excel = workbook(tmp_path / "employees.xlsx")
    settings = config.build_default_settings()
    settings.update(selected_company_id="a", companies=[
        {"id": "a", "name": "Musterfirma GmbH", "email_excel_file": str(excel),
         "output_dir": str(tmp_path / "output-a"), "pdf_input": str(folder)},
        {"id": "b", "name": "Beispielfirma GmbH", "email_excel_file": str(excel),
         "output_dir": str(tmp_path / "output-b"), "pdf_input": str(folder)},
    ])
    settings["ui"].update(last_pdf_dir=str(folder), last_pdf_input_mode="folder")
    config.save_settings(settings)
    return tmp_path, folder, excel


def test_company_rule_persistence_reset_and_stale_request(environment):
    bridge = WebBridge()
    assert json.loads(bridge.getPdfFilenameState())["rule"] == {"mode": "standard"}
    request = json.dumps({"company_id": "a", "rule": {**RULE, "sample": EXAMPLE}})
    assert json.loads(bridge.savePdfFilenameRule(request))["ok"]
    assert company_rule(config.load_settings()) == RULE
    assert "sample" not in config.load_settings()["companies"][0]["pdf_filename_rule"]
    bridge = WebBridge()
    assert json.loads(bridge.getPdfFilenameState())["rule"] == RULE
    bridge.selectCompany("b")
    assert json.loads(bridge.getPdfFilenameState())["rule"] == {"mode": "standard"}
    assert not json.loads(bridge.savePdfFilenameRule(request))["ok"]
    bridge.selectCompany("a")
    assert json.loads(bridge.savePdfFilenameRule(json.dumps({"company_id": "a", "rule": {"mode": "standard"}})))["ok"]
    assert company_rule(config.load_settings()) == {"mode": "standard"}
    assert not json.loads(bridge.savePdfFilenameRule(json.dumps({"company_id": "a"})))["ok"]


def test_preview_folder_and_duplicate_excel(environment):
    tmp, folder, excel = environment
    bridge = WebBridge()
    request = json.dumps({"company_id": "a", "rule": RULE, "filename": EXAMPLE})
    assert json.loads(bridge.previewPdfFilename(request))["match"]["persnr"] == "00022"
    result = json.loads(bridge.checkPdfFilenameFolder(request, str(folder)))
    assert result["total"] == result["matched"] == 2 and result["problems"] == 0
    assert company_rule(config.load_settings()) == {"mode": "standard"}  # Preview never saves.
    workbook(excel, [[22, "a@example.invalid", "One", "A"], ["00022", "b@example.invalid", "Two", "B"]])
    result = json.loads(bridge.previewPdfFilename(request))
    assert not result["ok"] and "Doppelte PersNr" in result["message"]
    bridge._processing_running = True
    assert not json.loads(bridge.savePdfFilenameRule(request))["ok"]


def test_native_dialog_contracts_use_company_rule_without_changing_paths(environment):
    from pywebview_app import ApiAdapter
    tmp, folder, excel = environment
    bridge = WebBridge()
    adapter = ApiAdapter(bridge)
    adapter._window = Mock()
    before = deepcopy(config.load_settings())
    adapter._window.create_file_dialog.return_value = [str(folder / EXAMPLE)]
    chosen = json.loads(adapter.choosePdfFilenameExample())
    assert chosen == {"ok": True, "company_id": "a", "filename": EXAMPLE}
    adapter._window.create_file_dialog.return_value = [str(folder)]
    result = json.loads(adapter.choosePdfFilenameFolder(json.dumps({"company_id": "a", "rule": RULE})))
    assert result["ok"] and result["matched"] == 2
    assert config.load_settings() == before
    adapter._window.create_file_dialog.return_value = None
    assert json.loads(adapter.choosePdfFilenameExample())["cancelled"]


def test_corrupt_saved_rule_is_not_silently_used_as_standard(environment):
    tmp, folder, excel = environment
    settings = config.load_settings()
    settings["companies"][0]["pdf_filename_rule"] = {"mode": "broken"}
    config.save_settings(settings)
    state = json.loads(WebBridge().getPdfFilenameState())
    assert not state["ok"] and state["message"]
    with pytest.raises(ValueError, match="Unbekanntes PDF-Dateiformat"):
        jobs.run_main_job("check", folder, excel, config.load_settings(), True)


@pytest.mark.parametrize("saved_rule", [RULE, {"mode": "content"}])
def test_rule_change_invalidates_prepared_results_and_restart(environment, saved_rule):
    bridge = WebBridge()
    settings = config.load_settings()
    bridge._processing_company_id = bridge._validation_company_id = bridge._shipping_company_id = "a"
    bridge._processing_input_signature = bridge._validation_input_signature = bridge._input_signature(settings)
    bridge._shipping_input_signature = bridge._shipping_signature(settings)
    bridge._validation_state = {"ready": True, "rows": []}
    bridge._shipping_rows = [{"persnr": "00022", "status": "Dry-Run"}]
    bridge._shipping_source_rows = [{"PersNr": "00022", "Status": "Dry-Run"}]
    old_signature = bridge._input_signature(settings)
    bridge._persist_workflow_session(settings)
    assert json.loads(bridge.savePdfFilenameRule(json.dumps({"company_id": "a", "rule": saved_rule})))["ok"]
    assert bridge._input_signature(config.load_settings()) != old_signature
    assert not bridge._validation_state["ready"] and not bridge._shipping_source_rows
    bridge = WebBridge()
    assert not bridge._validation_state["ready"]
    assert not json.loads(bridge.previewSelectedShippingSend('["00022"]'))["ok"]
    # Even an old workflow copied back cannot re-authorize stale attachments.
    WorkflowSessionStore(environment[0] / "workflows.json").save("a", {
        "processing_input_signature": list(old_signature),
        "validation_state": {"ready": True}, "shipping_rows": [{"status": "Dry-Run"}]})
    assert not WebBridge()._validation_state["ready"]


@pytest.mark.parametrize("saved_rule", [RULE, {"mode": "content"}])
def test_total_pdf_signature_unchanged_by_filename_rule(environment, saved_rule):
    settings = config.load_settings()
    settings["ui"]["last_pdf_input_mode"] = "single_pdf"
    bridge = WebBridge()
    before = bridge._input_signature(settings)
    settings["companies"][0]["pdf_filename_rule"] = saved_rule
    assert bridge._input_signature(settings) == before


@pytest.mark.parametrize("mode", ["folder", "single_pdf"])
def test_previous_text_recognizer_results_require_recheck(environment, mode):
    settings = config.load_settings()
    settings["ui"]["last_pdf_input_mode"] = mode
    settings["companies"][0]["pdf_filename_rule"] = {"mode": "content"}
    config.save_settings(settings)
    bridge = WebBridge()
    signature = bridge._input_signature(settings)
    old_signature = (*signature[:-1], signature[-1].split("|")[0])
    assert signature[-1].endswith("|labelled-personnel-v2")
    WorkflowSessionStore(environment[0] / "workflows.json").save("a", {
        "processing_input_signature": list(old_signature),
        "validation_state": {"ready": True},
        "shipping_rows": [{"persnr": "00022", "status": "Dry-Run"}],
    })
    restored = WebBridge()
    assert not restored._validation_state["ready"]
    assert not json.loads(restored.previewSelectedShippingSend('["00022"]'))["ok"]


@pytest.mark.parametrize("spaced_paths", [False, True])
@pytest.mark.parametrize("saved_rule", [RULE, {"mode": "content"}])
def test_full_check_prepare_mock_send_same_mapping(environment, monkeypatch, saved_rule, spaced_paths):
    tmp, folder, excel = environment
    if spaced_paths:
        if sys.platform == "win32":
            pytest.skip("Win32 normalizes trailing-space directory names; POSIX filesystem regression.")
        from pywebview_app import ApiAdapter
        folder = folder.rename(tmp / " PDF input ")
        excel_dir = tmp / " Excel input "
        excel_dir.mkdir()
        excel = excel.rename(excel_dir / " employees.xlsx")
        output = tmp / " Output "
        output.mkdir()
        adapter = ApiAdapter(WebBridge())
        adapter._window = Mock()
        for method, chosen in [
            (adapter.choosePdfInput, folder),
            (adapter.chooseExcelInput, excel),
            (adapter.chooseOutputFolder, output),
        ]:
            adapter._window.create_file_dialog.return_value = [str(chosen)]
            method()
        restored = config.load_settings()
        assert restored["companies"][0]["pdf_input"] == str(folder)
        assert restored["companies"][0]["email_excel_file"] == str(excel)
        assert config.company_output_dir(restored) == output
        bridge = WebBridge()
        assert bridge._inputs_ready(restored)
        assert bridge._path_state(str(folder), "folder")["path"] == str(folder)
        assert bridge._dialog_start_path(str(folder)) == str(folder)
        assert bridge._input_signature(restored)[2] == str(folder.resolve())
        bridge.selectCompany("b")
        bridge.selectCompany("a")
        assert config.load_settings()["ui"]["last_pdf_dir"] == str(folder)
    settings = config.load_settings()
    settings["companies"][0]["pdf_filename_rule"] = saved_rule
    if saved_rule["mode"] == "content":
        for index, path in enumerate(sorted(folder.iterdir())):
            text_pdf(path, [f"Personal-Nr. Geburtsdatum\n*Pers.-Nr. 00022*\nDocument {index}"])
    settings["smtp"]["from_email"] = "sender@example.invalid"
    config.save_settings(settings)
    from core import mailer
    transport = Mock()
    monkeypatch.setattr(mailer, "test_smtp_connection", Mock())
    monkeypatch.setattr(mailer, "send_email_with_attachment", transport)
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir()}
    checked = jobs.run_main_job("check", folder, excel, settings, True)
    assert checked["summary"]["valid_pdf_files"] == 2
    assert list(checked["grouped"]) == ["00022"]
    prepared = jobs.run_main_job("send", folder, excel, settings, True, {"00022"})
    row = prepared["table_rows"][0]
    assert row["Count"] == 2 and row["Status"] == "Dry-Run"
    assert transport.call_count == 0
    reader = PdfReader(str(prepared["run_dir"] / "prepared_pdfs" / row["Attachment"]))
    assert reader.decrypt("00022") and len(reader.pages) == 2
    if saved_rule["mode"] == "content":
        assert all(f"Document {index}" in page.extract_text() for index, page in enumerate(reader.pages))
    sent = jobs.run_main_job("send", folder, excel, settings, False, {"00022"})
    assert sent["table_rows"][0]["Status"] == "Gesendet" and transport.call_count == 1
    assert hashes == {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir()}


def test_content_sends_all_selected_employee_documents_without_foreign_or_ambiguous_pages(environment, monkeypatch):
    from core import mailer
    tmp, folder, excel = environment
    for index, path in enumerate(sorted(folder.iterdir())):
        text_pdf(path, [f"*Pers.-Nr. 00022*\nSelected document {index}"])
    text_pdf(folder / "other.pdf", ["*Pers.-Nr. 00023*\nOther employee"])
    text_pdf(folder / "conflict.pdf", ["Pers.-Nr. 00022\nPersonalnummer: 00023\nConflict"])
    text_pdf(folder / "mixed.pdf", ["Pers.-Nr. 00022", "Pers.-Nr. 00023"])
    text_pdf(folder / "unknown.pdf", ["Pers.-Nr. 00999\nUnknown employee"])
    workbook(excel, [[22, "selected@example.invalid", "Muster", "Max"],
                     [23, "other@example.invalid", "Beispiel", "Anna"]])
    settings = config.load_settings()
    settings["companies"][0]["pdf_filename_rule"] = {"mode": "content"}
    settings["smtp"]["from_email"] = "sender@example.invalid"
    config.save_settings(settings)
    monkeypatch.setattr(mailer, "test_smtp_connection", Mock())
    transport = Mock()
    monkeypatch.setattr(mailer, "send_email_with_attachment", transport)
    result = jobs.run_main_job("send", folder, excel, settings, False, {"00022"})
    transport.assert_called_once()
    assert transport.call_args.kwargs["to_email"] == "selected@example.invalid"
    attachment = PdfReader(str(transport.call_args.kwargs["attachment_path"]))
    assert attachment.decrypt("00022") and len(attachment.pages) == 2
    assert all(f"Selected document {index}" in page.extract_text()
               for index, page in enumerate(attachment.pages))
    assert len(result["filename_errors"]) == 3
    assert result["table_rows"][0]["Count"] == 2


@pytest.mark.skipif(sys.platform == "win32", reason="Win32 aliases trailing-space directory names.")
def test_paths_differing_only_by_space_are_not_interchangeable(environment):
    tmp, folder, excel = environment
    spaced = tmp / "input "
    spaced.mkdir()
    bridge = WebBridge()
    settings = config.load_settings()
    original = bridge._input_signature(settings)
    settings["ui"]["last_pdf_dir"] = str(spaced)
    assert bridge._input_signature(settings) != original
    assert bridge._path_state(str(spaced), "folder")["path"] == str(spaced)
    # Do not silently choose an existing trimmed sibling for a missing selection.
    missing = str(tmp / "input  ")
    assert not bridge._path_state(missing, "folder")["valid"]


def test_legacy_path_migration_preserves_whitespace(environment):
    tmp, folder, excel = environment
    settings = config.load_settings()
    settings["companies"] = [{"id": "a", "name": "Demo"}]
    settings["ui"].update(last_pdf_dir=str(tmp / "input "),
                          last_excel_file=str(tmp / " Excel " / "employees.xlsx"))
    config.save_settings(settings)
    company = config.load_settings()["companies"][0]
    assert company["pdf_input"] == settings["ui"]["last_pdf_dir"]
    assert company["email_excel_file"] == settings["ui"]["last_excel_file"]


def test_upgrade_preserves_existing_data_and_old_settings(environment):
    tmp, folder, excel = environment
    from core.storage_paths import atomic_json
    # Exercise the previous committed settings loader on the same isolated store.
    baseline = "3f8acc5acd6a1a210aad809c5e21359d90f7fb28"
    try:
        previous_source = subprocess.run(
            ["git", "show", f"{baseline}:lohnmail-pywebview-test/core/config.py"],
            check=False, capture_output=True, text=True)
    except FileNotFoundError:
        pytest.skip("Previous-version comparison requires git and the recorded baseline commit.")
    if previous_source.returncode:
        pytest.skip("Previous-version comparison requires baseline 3f8acc5 (not included in source ZIP).")
    source = previous_source.stdout
    old = types.ModuleType("previous_config")
    old.__file__ = config.__file__
    exec(compile(source, "previous_config.py", "exec"), old.__dict__)
    old.SETTINGS_PATH = config.SETTINGS_PATH
    old.ensure_default_config = lambda: None
    old._hydrate_smtp_passwords = deepcopy
    old._protect_and_strip_smtp_passwords = deepcopy
    previous = old.load_settings()
    for company in previous["companies"]:
        company.pop("pdf_filename_rule", None)
    atomic_json(config.SETTINGS_PATH, previous)
    files = {}
    for name in ("license.json", "report.txt"):
        path = tmp / name
        path.write_bytes(b"synthetic preserved sentinel")
        files[path] = path.read_bytes()
    with sqlite3.connect(tmp / "history.sqlite3") as db:
        db.execute("CREATE TABLE synthetic_history (message TEXT)")
        db.execute("INSERT INTO synthetic_history VALUES ('preserve this history')")
    restored = config.load_settings()
    assert company_rule(restored) == {"mode": "standard"}
    assert json.loads(WebBridge().savePdfFilenameRule(json.dumps({"company_id": "a", "rule": RULE})))["ok"]
    after = config.load_settings()
    for key in ("smtp", "license", "ui"):
        assert after[key] == restored[key]
    for before_company, after_company in zip(restored["companies"], after["companies"]):
        assert {k:v for k,v in after_company.items() if k != "pdf_filename_rule"} == {
            k:v for k,v in before_company.items() if k != "pdf_filename_rule"}
    assert all(p.read_bytes() == value for p, value in files.items())
    with sqlite3.connect(tmp / "history.sqlite3") as db:
        assert db.execute("SELECT message FROM synthetic_history").fetchall() == [("preserve this history",)]
        assert db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    # Previous code can still read existing settings after the upgrade.
    legacy_read = old.load_settings()
    assert legacy_read["smtp"] == after["smtp"] and legacy_read["license"] == after["license"]
    assert excel.is_file() and folder.is_dir()

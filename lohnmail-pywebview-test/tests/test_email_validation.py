from core.email_validation import validate_email_records
from core.orchestrator import _email_status
from core import orchestrator
import fitz
from openpyxl import Workbook


CHECKED_AT = "2026-08-18T14:00:00+00:00"


def test_delivery_statuses_keep_specific_validation_reason():
    assert _email_status({"code": "duplicate"}, "same@example.de") == "Doppelte E-Mail"
    assert _email_status({"code": "invalid_format"}, "broken") == "Ungültiges Format"
    assert _email_status({"code": "illegal_characters"}, "bad value@example.de") == "Ungültige Zeichen"
    assert _email_status({"code": "domain_missing"}, "a@missing.invalid") == "Domain nicht gefunden"
    assert _email_status({"code": "mx_missing"}, "a@example.de") == "Keine MX-Einträge"
    assert _email_status({"code": "missing"}, "") == "Keine E-Mail"


def test_action_check_reports_duplicate_email_instead_of_invalid(tmp_path):
    pdf_dir = tmp_path / "pdf"
    pdf_dir.mkdir()
    for persnr in ("00001", "00002"):
        document = fitz.open()
        page = document.new_page()
        page.insert_text((72, 72), f"Mitarbeiter {persnr}")
        document.save(pdf_dir / f"{persnr}.pdf")
        document.close()
    excel_path = tmp_path / "employees.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["PersNr", "Email", "Name"])
    sheet.append(["00001", "same@example.de", "Eins"])
    sheet.append(["00002", "SAME@example.de", "Zwei"])
    workbook.save(excel_path)

    result = orchestrator.action_check(pdf_dir, excel_path, output_dir=tmp_path / "output")

    assert {row["Status"] for row in result["table_rows"]} == {"Doppelte E-Mail"}
    assert {row["EmailValidationCode"] for row in result["table_rows"]} == {"duplicate"}


def _records(*emails: str) -> dict[str, dict[str, str]]:
    return {
        str(index): {
            "Email": email,
            "ExcelRow": str(index + 1),
        }
        for index, email in enumerate(emails, start=1)
    }


def test_local_validation_detects_missing_format_characters_and_duplicates():
    records = _records(
        "",
        "ohne-at-zeichen.example",
        "name mit leerzeichen@example.com",
        "Doppelt@example.com",
        "doppelt@example.com",
    )

    results = validate_email_records(records, check_dns=False, checked_at=CHECKED_AT)

    assert results["1"]["code"] == "missing"
    assert results["2"]["code"] == "invalid_format"
    assert results["3"]["code"] == "illegal_characters"
    assert results["4"]["code"] == "duplicate"
    assert results["5"]["code"] == "duplicate"
    assert all(result["sendable"] is False for result in results.values())
    assert all(result["checked_at"] == CHECKED_AT for result in results.values())


def test_dns_validation_distinguishes_valid_domain_missing_and_missing_mx():
    domain_results = {
        "valid.example": ("valid", "MX-Eintrag gefunden."),
        "missing.example": ("domain_missing", "Die Domain existiert nicht."),
        "nomx.example": ("mx_missing", "Kein MX-Eintrag."),
    }

    results = validate_email_records(
        _records(
            "ok@valid.example",
            "domain@missing.example",
            "mx@nomx.example",
        ),
        domain_checker=lambda domain: domain_results[domain],
        checked_at=CHECKED_AT,
    )

    assert results["1"]["code"] == "valid"
    assert results["1"]["mx_status"] == "Vorhanden"
    assert results["1"]["sendable"] is True
    assert results["2"]["code"] == "domain_missing"
    assert results["2"]["sendable"] is False
    assert results["3"]["code"] == "mx_missing"
    assert results["3"]["sendable"] is False


def test_temporary_dns_failure_is_visible_but_does_not_block_sending():
    results = validate_email_records(
        _records("mitarbeiter@example.com"),
        domain_checker=lambda _domain: ("dns_unavailable", "Zeitüberschreitung"),
        checked_at=CHECKED_AT,
    )

    result = results["1"]
    assert result["code"] == "dns_unavailable"
    assert result["label"] == "DNS nicht geprüft"
    assert result["mx_status"] == "Nicht geprüft"
    assert result["sendable"] is True

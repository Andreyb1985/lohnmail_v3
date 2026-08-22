from datetime import date, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import fitz
from openpyxl import Workbook

from core.excel_io import load_email_records, normalize_birth_date
from core.message_templates import append_pdf_password_notice
from core.orchestrator import (
    _enrich_employee_names_from_pdfs,
    _extract_birth_date_from_pdf,
    _extract_employee_full_name_from_pdf,
    _pdf_password_for_employee,
    _prepare_pdf_input,
)


class PdfPasswordTests(unittest.TestCase):
    @staticmethod
    def _write_payslip(pdf_path: Path, persnr: str, full_name: str) -> None:
        document = fitz.open()
        page = document.new_page()
        page.insert_text((42, 60), f"B/N Pers.-Nr. {persnr} N0E")
        page.insert_text((42, 90), full_name)
        page.insert_text((42, 104), "Musterstr. 12")
        page.insert_text((42, 118), "45127 Essen")
        document.save(pdf_path)
        document.close()

    def test_birth_date_normalization(self) -> None:
        self.assertEqual(normalize_birth_date(date(1990, 2, 3)), "03021990")
        self.assertEqual(normalize_birth_date(datetime(1990, 2, 3, 12, 30)), "03021990")
        self.assertEqual(normalize_birth_date("03.02.1990"), "03021990")
        self.assertEqual(normalize_birth_date("1990-02-03"), "03021990")
        self.assertEqual(normalize_birth_date("03021990"), "03021990")
        self.assertEqual(normalize_birth_date("030290"), "03021990")
        self.assertEqual(normalize_birth_date("180692"), "18061992")
        self.assertEqual(normalize_birth_date(3021990), "03021990")
        self.assertEqual(normalize_birth_date("kein Datum"), "")

    def test_birth_date_is_extracted_from_payslip_pdf(self) -> None:
        with TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "00123.pdf"
            document = fitz.open()
            page = document.new_page()
            page.insert_text((42, 60), "Pers.-Nr.")
            page.insert_text((82, 60), "Geburtsdatum")
            page.insert_text((42, 72), "00123")
            page.insert_text((82, 72), "030290")
            document.save(pdf_path)
            document.close()

            birth_date = _extract_birth_date_from_pdf(pdf_path)

        self.assertEqual(birth_date, "03021990")

    def test_employee_name_is_extracted_from_payslip_pdf(self) -> None:
        with TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "00123.pdf"
            self._write_payslip(pdf_path, "00123", "Max Mustermann")

            full_name = _extract_employee_full_name_from_pdf(pdf_path, "00123")

        self.assertEqual(full_name, "Max Mustermann")

    def test_pdf_name_only_fills_missing_excel_value(self) -> None:
        with TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "00123.pdf"
            self._write_payslip(pdf_path, "00123", "Max Mustermann")
            records = {
                "00123": {
                    "Email": "max@example.de",
                    "Vorname": "Max",
                    "Name": "",
                }
            }

            enriched = _enrich_employee_names_from_pdfs(
                records,
                {"00123": [pdf_path]},
            )

        self.assertEqual(enriched["00123"]["Vorname"], "Max")
        self.assertEqual(enriched["00123"]["Name"], "Mustermann")

    def test_pdf_name_does_not_replace_complete_excel_name(self) -> None:
        with TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "00123.pdf"
            self._write_payslip(pdf_path, "00123", "Andere Person")
            records = {
                "00123": {
                    "Email": "max@example.de",
                    "Vorname": "Max",
                    "Name": "Mustermann",
                }
            }

            enriched = _enrich_employee_names_from_pdfs(
                records,
                {"00123": [pdf_path]},
            )

        self.assertEqual(enriched["00123"]["Vorname"], "Max")
        self.assertEqual(enriched["00123"]["Name"], "Mustermann")

    def test_name_enrichment_works_for_folder_and_combined_pdf(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pdf_folder = root / "payslips"
            pdf_folder.mkdir()
            folder_pdf = pdf_folder / "00123.pdf"
            self._write_payslip(folder_pdf, "00123", "Max Mustermann")

            combined_pdf = root / "gesamt.pdf"
            self._write_payslip(combined_pdf, "00123", "Max Mustermann")

            folder_scan = _prepare_pdf_input(pdf_folder, root / "folder-run")
            combined_scan = _prepare_pdf_input(combined_pdf, root / "combined-run")
            folder_records = _enrich_employee_names_from_pdfs(
                {},
                folder_scan["grouped"],
            )
            combined_records = _enrich_employee_names_from_pdfs(
                {},
                combined_scan["grouped"],
            )

        self.assertEqual(folder_records["00123"]["Vorname"], "Max")
        self.assertEqual(folder_records["00123"]["Name"], "Mustermann")
        self.assertEqual(combined_records["00123"]["Vorname"], "Max")
        self.assertEqual(combined_records["00123"]["Name"], "Mustermann")

    def test_birth_date_is_loaded_from_excel_column_after_first_name(self) -> None:
        with TemporaryDirectory() as temp_dir:
            excel_path = Path(temp_dir) / "employees.xlsx"
            workbook = Workbook()
            worksheet = workbook.active
            worksheet.append(["PersNr", "Name", "Vorname", "Geburtsdatum", "Email"])
            worksheet.append([123, "Muster", "Max", date(1990, 2, 3), "max@example.de"])
            workbook.save(excel_path)

            records = load_email_records(excel_path)

        self.assertEqual(records["00123"]["Geburtsdatum"], "03021990")

    def test_personnel_number_is_default_password_basis(self) -> None:
        settings = {"enabled": True, "prefix": "LM-", "suffix": "-PDF"}
        password = _pdf_password_for_employee(settings, "00123", {})
        self.assertEqual(password, "LM-00123-PDF")

    def test_birth_date_can_be_used_as_password_basis(self) -> None:
        settings = {
            "enabled": True,
            "source": "birth_date",
            "prefix": "LM-",
            "suffix": "-PDF",
        }
        password = _pdf_password_for_employee(
            settings,
            "00123",
            {"Geburtsdatum": "03021990"},
        )
        self.assertEqual(password, "LM-03021990-PDF")

    def test_pdf_birth_date_has_priority_over_excel_fallback(self) -> None:
        settings = {
            "enabled": True,
            "source": "birth_date",
            "prefix": "LM-",
            "suffix": "-PDF",
        }
        password = _pdf_password_for_employee(
            settings,
            "00123",
            {
                "PdfGeburtsdatum": "04031991",
                "Geburtsdatum": "03021990",
            },
        )
        self.assertEqual(password, "LM-04031991-PDF")

    def test_missing_birth_date_stops_password_creation(self) -> None:
        settings = {"enabled": True, "source": "birth_date"}
        with self.assertRaisesRegex(ValueError, "Geburtsdatum fehlt"):
            _pdf_password_for_employee(settings, "00123", {})

    def test_birth_date_password_notice_is_added_to_plain_and_html_mail(self) -> None:
        settings = {"enabled": True, "source": "birth_date"}
        body, body_html = append_pdf_password_notice(
            "Guten Tag,\nim Anhang finden Sie Ihre Abrechnung.",
            "<html><body><p>Guten Tag</p></body></html>",
            settings,
        )

        notice = "Ihr PDF-Passwort ist Ihr Geburtsdatum im Format TTMMJJJJ"
        self.assertIn(notice, body)
        self.assertIn(notice, body_html)
        self.assertLess(body_html.index(notice), body_html.index("</body>"))

        repeated_body, repeated_html = append_pdf_password_notice(body, body_html, settings)
        self.assertEqual(repeated_body.count(notice), 1)
        self.assertEqual(repeated_html.count('data-lohnmail-password-notice="birth-date"'), 1)

    def test_birth_date_password_notice_includes_prefix_and_suffix(self) -> None:
        body, _ = append_pdf_password_notice(
            "Ihre Abrechnung.",
            "",
            {
                "enabled": True,
                "source": "birth_date",
                "prefix": "LM-",
                "suffix": "-PDF",
            },
        )

        self.assertIn("Format: LM-TTMMJJJJ-PDF", body)
        self.assertIn("z. B. LM-18061992-PDF", body)

    def test_password_notice_is_not_added_for_personnel_number(self) -> None:
        body, body_html = append_pdf_password_notice(
            "Ihre Abrechnung.",
            "<p>Ihre Abrechnung.</p>",
            {"enabled": True, "source": "persnr"},
        )

        self.assertEqual(body, "Ihre Abrechnung.")
        self.assertEqual(body_html, "<p>Ihre Abrechnung.</p>")


if __name__ == "__main__":
    unittest.main()

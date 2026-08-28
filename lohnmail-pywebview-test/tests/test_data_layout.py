from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from core.config import (
    APP_INSTALL_DIR,
    COMPANIES_DIR,
    SETTINGS_DIR,
    _deep_merge_settings,
    build_default_settings,
    company_output_dir,
    user_data_dir,
)


class DataLayoutTests(unittest.TestCase):
    def test_clean_install_has_no_default_company(self) -> None:
        settings = _deep_merge_settings(build_default_settings())
        self.assertEqual(settings["companies"], [])
        self.assertEqual(settings["selected_company_id"], "")

    def test_user_data_layout_has_three_named_areas(self) -> None:
        self.assertEqual(APP_INSTALL_DIR.name, "App")
        self.assertEqual(SETTINGS_DIR.name, "Settings")
        self.assertEqual(COMPANIES_DIR.name, "Companies")
        self.assertEqual(APP_INSTALL_DIR.parent, SETTINGS_DIR.parent)
        self.assertEqual(APP_INSTALL_DIR.parent, COMPANIES_DIR.parent)

    def test_company_output_uses_company_name(self) -> None:
        settings = {
            "selected_company_id": "brauck",
            "companies": [{"id": "brauck", "name": "Brauck GmbH & Co. KG"}],
        }
        self.assertEqual(
            company_output_dir(settings),
            COMPANIES_DIR / "Lohn_Brauck_GmbH_&_Co._KG",
        )

    def test_company_output_removes_windows_path_characters(self) -> None:
        settings = {
            "selected_company_id": "unsafe",
            "companies": [{"id": "unsafe", "name": 'Nord/West: Lohn*? "Test"'}],
        }
        self.assertEqual(
            company_output_dir(settings).name,
            "Lohn_Nord_West_Lohn_Test",
        )

    def test_portable_layout_uses_parent_of_app_folder(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory) / "LohnMail"
            app = root / "App"
            app.mkdir(parents=True)
            (root / "Settings").mkdir()
            (root / "Companies").mkdir()
            with patch.dict("os.environ", {"LOHNMAIL_DATA_DIR": ""}), patch(
                "core.config.app_dir", return_value=app
            ):
                self.assertEqual(user_data_dir(), root)

    def test_explicit_data_directory_has_priority(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            requested = Path(temporary_directory) / "CustomLohnMail"
            with patch.dict("os.environ", {"LOHNMAIL_DATA_DIR": str(requested)}):
                self.assertEqual(user_data_dir(), requested.resolve())

    def test_company_pdf_and_mail_settings_survive_normalization(self) -> None:
        settings = _deep_merge_settings(
            {
                "companies": [
                    {
                        "id": "alpha",
                        "name": "Alpha GmbH",
                        "email_excel_file": "alpha.xlsx",
                        "pdf_input": "alpha-pdf",
                        "pdf_input_mode": "single_pdf",
                        "mail_settings": {"scope": "custom", "smtp": {"server": "smtp.example.de"}},
                    }
                ],
                "selected_company_id": "alpha",
            }
        )
        company = settings["companies"][0]
        self.assertEqual(company["pdf_input"], "alpha-pdf")
        self.assertEqual(company["pdf_input_mode"], "single_pdf")
        self.assertEqual(company["mail_settings"]["smtp"]["server"], "smtp.example.de")


if __name__ == "__main__":
    unittest.main()

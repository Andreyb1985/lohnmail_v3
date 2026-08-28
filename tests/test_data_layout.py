from __future__ import annotations

import unittest

from core.config import APP_INSTALL_DIR, COMPANIES_DIR, SETTINGS_DIR, company_output_dir


class DataLayoutTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()

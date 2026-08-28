from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import fitz

from core import orchestrator


class PdfMergeIntegrityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _create_pdf(self, filename: str, label: str) -> Path:
        pdf_path = self.root / filename
        doc = fitz.open()
        page = doc.new_page(width=420, height=260)
        page.insert_text((36, 90), label, fontsize=28)
        page.insert_text((36, 140), f"Quelle: {filename}", fontsize=14)
        doc.save(pdf_path)
        doc.close()
        return pdf_path

    @staticmethod
    def _page_texts(pdf_path: Path) -> list[str]:
        doc = fitz.open(pdf_path)
        try:
            return [page.get_text("text") for page in doc]
        finally:
            doc.close()

    def test_verified_merge_preserves_every_source_page_in_order(self) -> None:
        source_files = [
            self._create_pdf(f"{index:05d}.pdf", f"Mitarbeiter {index:05d}")
            for index in range(1, 81)
        ]
        output = self.root / "merged.pdf"

        stats = orchestrator._merge_pdf_files_verified(source_files, output)

        self.assertTrue(output.is_file())
        self.assertEqual(stats["expected_page_count"], 80)
        self.assertEqual(stats["merged_page_count"], 80)
        self.assertTrue(stats["content_check_ok"])
        self.assertEqual(
            self._page_texts(output),
            [text for source in source_files for text in self._page_texts(source)],
        )

    def test_missing_email_bundle_uses_verified_merge(self) -> None:
        grouped: dict[str, list[Path]] = {}
        missing_email_persnr: list[str] = []
        for index in range(1, 41):
            persnr = f"{index:05d}"
            grouped[persnr] = [
                self._create_pdf(f"{persnr}.pdf", f"Ohne E-Mail {persnr}")
            ]
            missing_email_persnr.append(persnr)

        output = self.root / "ohne_email_gesamt.pdf"
        stats = orchestrator.build_missing_email_bundle(
            grouped,
            missing_email_persnr,
            output,
        )

        self.assertEqual(stats["pdf_file_count"], 40)
        self.assertEqual(stats["expected_page_count"], 40)
        self.assertEqual(stats["merged_page_count"], 40)
        self.assertTrue(stats["content_check_ok"])
        self.assertEqual(len(self._page_texts(output)), 40)

    def test_corrupt_result_is_never_published(self) -> None:
        source = self._create_pdf("00001.pdf", "Mitarbeiter 00001")
        output = self.root / "merged.pdf"
        original_hashes = orchestrator._pdf_visual_page_hashes

        def mismatching_output_hashes(pdf_path: Path) -> list[str]:
            hashes = original_hashes(pdf_path)
            if "lohnmail-tmp" in pdf_path.name:
                hashes[0] = "0" * 64
            return hashes

        with patch.object(
            orchestrator,
            "_pdf_visual_page_hashes",
            side_effect=mismatching_output_hashes,
        ):
            with self.assertRaisesRegex(RuntimeError, "Abweichende Seite"):
                orchestrator._merge_pdf_files_verified([source], output)

        self.assertFalse(output.exists())
        self.assertFalse((self.root / ".merged.lohnmail-tmp.pdf").exists())


if __name__ == "__main__":
    unittest.main()

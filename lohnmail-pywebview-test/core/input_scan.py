# core/input_scan.py
import re
from pathlib import Path

from .excel_io import normalize_persnr

PDF_NAME_RE = re.compile(r"^(\d{1,5})(?:_(\d+))?\.pdf$", re.IGNORECASE)


def _sort_key(path: Path):
    """
    Sortierung:
    02548.pdf   -> zuerst
    02548_1.pdf -> danach
    02548_2.pdf -> usw.
    """
    m = PDF_NAME_RE.match(path.name)
    if not m:
        return (999999, 999999, path.name.lower())

    persnr_raw = m.group(1)
    suffix_raw = m.group(2)

    persnr = int(persnr_raw)
    suffix = int(suffix_raw) if suffix_raw is not None else 0
    return (persnr, suffix, path.name.lower())


def scan_pdf_folder(folder: Path) -> dict:
    """
    Erwartete Dateinamen:
      02548.pdf
      02548_1.pdf
      02548_2.pdf
      2548.pdf
      2548_1.pdf

    Rückgabe:
    {
        "grouped": { "02548": [Path(...), Path(...)] },
        "invalid_files": [Path(...), ...],
        "total_pdf_files": int,
        "valid_pdf_files": int,
        "unique_persnr_count": int,
    }
    """
    if not folder.exists() or not folder.is_dir():
        raise ValueError("Der ausgewählte PDF-Ordner existiert nicht oder ist kein Ordner.")

    all_pdfs = sorted(folder.glob("*.pdf"))
    grouped: dict[str, list[Path]] = {}
    invalid_files: list[Path] = []

    for pdf_path in all_pdfs:
        m = PDF_NAME_RE.match(pdf_path.name)
        if not m:
            invalid_files.append(pdf_path)
            continue

        persnr_raw = m.group(1)
        persnr = normalize_persnr(persnr_raw)

        if not persnr:
            invalid_files.append(pdf_path)
            continue

        grouped.setdefault(persnr, []).append(pdf_path)

    for persnr in grouped:
        grouped[persnr] = sorted(grouped[persnr], key=_sort_key)

    return {
        "grouped": grouped,
        "invalid_files": invalid_files,
        "total_pdf_files": len(all_pdfs),
        "valid_pdf_files": sum(len(v) for v in grouped.values()),
        "unique_persnr_count": len(grouped),
    }
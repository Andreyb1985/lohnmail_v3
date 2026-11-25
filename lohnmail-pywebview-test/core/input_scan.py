# core/input_scan.py
import re
from pathlib import Path

from .pdf_filename import match_pdf_file, validate_rule

FOLDER_AUDIT_REVISION = "folder-paper-bundle-v1"

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


def scan_pdf_folder(folder: Path, rule=None, records: dict | None = None,
                    *, keep_without_excel: bool = False) -> dict:
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

    rule = validate_rule(rule)
    all_pdfs = sorted((p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"),
                      key=lambda p: (p.name.casefold(), p.name))
    grouped: dict[str, list[Path]] = {}
    invalid_files: list[Path] = []
    matches = []

    for pdf_path in all_pdfs:
        match = match_pdf_file(pdf_path, rule, records)
        matches.append(match)
        persnr = match["persnr"]
        # Preview still reports an unmatched employee. The processing pipeline
        # must retain clearly identified documents for the no-email paper bundle,
        # even when the employee is absent from the address workbook.
        if match["reason"] and not (keep_without_excel and match.get("missing_excel")):
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
        "filename_matches": matches,
        "filename_errors": [
            {"file": m["file"], "persnr": m["persnr"], "reason": m["reason"]}
            for m in matches if m["reason"]
        ],
    }

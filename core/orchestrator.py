from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Callable
import hashlib
import inspect
import re

from openpyxl import Workbook
import fitz

try:
    from PyPDF2 import PdfReader, PdfWriter
except ModuleNotFoundError:
    PdfReader = None
    PdfWriter = None

from .config import GESOB_DIR
from .excel_io import load_email_records
from .input_scan import scan_pdf_folder
from .message_templates import build_mail_context, format_message_template, format_name_vorname
from .report import write_audit_check_xlsx

ProgressCb = Callable[[str], None] | None
PERSNR_TEXT_RE = re.compile(r"Pers\.-Nr\.\s*([0-9]{4,})")


def _p(cb: ProgressCb, msg: str) -> None:
    if cb:
        cb(msg)


def _require_pdf_support() -> None:
    if PdfReader is None or PdfWriter is None:
        raise RuntimeError(
            "Die PDF-Funktion ist nicht verfügbar: Das Paket 'PyPDF2' ist nicht installiert."
        )


def _persnr_sort_key(persnr: str):
    digits = "".join(ch for ch in str(persnr) if ch.isdigit())
    return (int(digits) if digits else 999999, str(persnr))


def _count_pdf_pages(pdf_path: Path) -> int:
    if PdfReader is None:
        return 0
    try:
        return len(PdfReader(str(pdf_path)).pages)
    except Exception:
        return 0


def _pdf_path_key(pdf_path: Path) -> str:
    try:
        return str(pdf_path.resolve())
    except Exception:
        return str(pdf_path)


def _read_pdf_page_count(pdf_path: Path) -> int:
    _require_pdf_support()
    try:
        page_count = len(PdfReader(str(pdf_path)).pages)
    except Exception as exc:
        raise ValueError(f"PDF nicht lesbar: {exc}") from exc

    if page_count <= 0:
        raise ValueError("PDF enthält keine Seiten.")

    return page_count


def _validate_grouped_pdf_files(grouped: dict[str, list[Path]]) -> dict:
    valid_grouped: dict[str, list[Path]] = {}
    page_counts: dict[str, int] = {}
    errors_by_persnr: dict[str, list[str]] = {}
    error_details: list[dict] = []

    for persnr, files in grouped.items():
        for pdf_path in _dedup_pdf_paths(files):
            try:
                page_counts[_pdf_path_key(pdf_path)] = _read_pdf_page_count(pdf_path)
                valid_grouped.setdefault(persnr, []).append(pdf_path)
            except Exception as exc:
                reason = str(exc)
                errors_by_persnr.setdefault(persnr, []).append(f"{pdf_path.name}: {reason}")
                error_details.append({
                    "persnr": persnr,
                    "file": pdf_path.name,
                    "reason": reason,
                })

    return {
        "valid_grouped": valid_grouped,
        "page_counts": page_counts,
        "errors_by_persnr": errors_by_persnr,
        "error_details": error_details,
    }


def _file_sha256(pdf_path: Path) -> str:
    h = hashlib.sha256()
    with pdf_path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _dedup_pdf_paths(pdf_files: list[Path]) -> list[Path]:
    """
    Entfernt doppelte Pfade innerhalb einer PDF-Liste,
    behält aber die ursprüngliche Reihenfolge bei.
    """
    seen: set[str] = set()
    result: list[Path] = []

    for pdf_path in pdf_files:
        try:
            key = str(pdf_path.resolve())
        except Exception:
            key = str(pdf_path)

        if key in seen:
            continue
        seen.add(key)
        result.append(pdf_path)

    return result


def _email_map_from_records(email_records: dict[str, dict[str, str]]) -> dict[str, str]:
    return {
        persnr: str(record.get("Email", "") or "")
        for persnr, record in email_records.items()
        if str(record.get("Email", "") or "").strip()
    }


def _person_values(email_records: dict[str, dict[str, str]], persnr: str) -> dict[str, str]:
    record = email_records.get(persnr, {})
    return {
        "Name": str(record.get("Name", "") or ""),
        "Vorname": str(record.get("Vorname", "") or ""),
    }


def make_run_id(source_name: str, prefix: str = "") -> str:
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    safe = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in source_name.strip())
    safe = safe.strip("_") or "PDF_Ordner"
    return f"{ts}_{prefix}{safe}" if prefix else f"{ts}_{safe}"


def run_dir_from_id(run_id: str) -> Path:
    return GESOB_DIR / run_id


def _extract_persnr_from_pdf(pdf_path: Path) -> str | None:
    doc = fitz.open(pdf_path)
    try:
        for page in doc:
            text = page.get_text("text") or ""
            match = PERSNR_TEXT_RE.search(text)
            if match:
                return match.group(1).zfill(5)
    finally:
        doc.close()
    return None


def _split_single_pdf_to_employee_pages(source_pdf: Path, out_dir: Path, progress_cb: ProgressCb = None) -> None:
    _require_pdf_support()

    out_dir.mkdir(parents=True, exist_ok=True)
    reader = PdfReader(str(source_pdf))
    total_pages = len(reader.pages)
    persnr_counts: dict[str, int] = {}
    unmatched_count = 0

    for index, page in enumerate(reader.pages, start=1):
        writer = PdfWriter()
        writer.add_page(page)

        temp_path = out_dir / f"{source_pdf.stem}_p{index:03d}.pdf"
        with temp_path.open("wb") as f:
            writer.write(f)

        persnr = _extract_persnr_from_pdf(temp_path)
        if persnr:
            suffix_no = persnr_counts.get(persnr, 0)
            filename = f"{persnr}.pdf" if suffix_no == 0 else f"{persnr}_{suffix_no}.pdf"
            persnr_counts[persnr] = suffix_no + 1
            temp_path.rename(out_dir / filename)
        else:
            unmatched_count += 1
            temp_path.rename(out_dir / f"unmatched_{unmatched_count:03d}.pdf")

        _p(progress_cb, f"PDF wird aufgeteilt: Seite {index}/{total_pages}")


def _prepare_pdf_input(pdf_input: Path, run_dir: Path, progress_cb: ProgressCb = None) -> dict:
    if pdf_input.is_dir():
        _p(progress_cb, "PDF-Ordner wird analysiert...")
        scan_result = scan_pdf_folder(pdf_input)
        scan_result["source_kind"] = "folder"
        scan_result["prepared_folder"] = pdf_input
        return scan_result

    if pdf_input.is_file() and pdf_input.suffix.lower() == ".pdf":
        prepared_folder = run_dir / "output_pages"
        _p(progress_cb, "Einzelne PDF wird in Seiten aufgeteilt und nach PersNr benannt...")
        _split_single_pdf_to_employee_pages(pdf_input, prepared_folder, progress_cb=progress_cb)
        scan_result = scan_pdf_folder(prepared_folder)
        scan_result["source_kind"] = "single_pdf"
        scan_result["prepared_folder"] = prepared_folder
        return scan_result

    raise ValueError("Bitte einen gültigen PDF-Ordner oder eine einzelne PDF-Datei auswählen.")


def build_missing_email_bundle(
    grouped: dict[str, list[Path]],
    missing_email_persnr: list[str],
    out_pdf: Path,
) -> dict:
    """
    Baut ohne_email_gesamt.pdf nach folgendem Prinzip:

    - PersNr kommt aus dem Dateinamen (bereits in grouped vorbereitet)
    - wenn Mitarbeiter keine E-Mail hat -> ALLE seine PDF-Dateien kommen ins Bundle
    - Reihenfolge: PersNr numerisch aufsteigend
    - innerhalb einer PersNr: Reihenfolge wie scan_pdf_folder() sie bereits sortiert geliefert hat
    - doppelte Pfade innerhalb derselben PersNr werden vorher entfernt
    - exakte physische PDF-Duplikate werden zusätzlich per SHA256 ausgeschlossen
    """
    _require_pdf_support()

    file_rows: list[tuple[str, Path, int, str]] = []
    seen_hashes: dict[str, str] = {}  # hash -> first filename
    details: list[dict] = []

    for persnr in sorted(missing_email_persnr, key=_persnr_sort_key):
        pdf_list = _dedup_pdf_paths(grouped.get(persnr, []))

        for pdf_path in pdf_list:
            pages = _count_pdf_pages(pdf_path)
            file_hash = _file_sha256(pdf_path)
            short_hash = file_hash[:16]

            if file_hash in seen_hashes:
                details.append(
                    {
                        "persnr": persnr,
                        "file": pdf_path.name,
                        "pages": pages,
                        "included": "Nein",
                        "reason": "Exaktes Datei-Duplikat",
                        "file_hash": short_hash,
                        "duplicate_of": seen_hashes[file_hash],
                    }
                )
                continue

            seen_hashes[file_hash] = pdf_path.name
            file_rows.append((persnr, pdf_path, pages, short_hash))
            details.append(
                {
                    "persnr": persnr,
                    "file": pdf_path.name,
                    "pages": pages,
                    "included": "Ja",
                    "reason": "Keine E-Mail",
                    "file_hash": short_hash,
                    "duplicate_of": "",
                }
            )

    if not file_rows:
        out_pdf.unlink(missing_ok=True)
        return {
            "pdf_file_count": 0,
            "duplicate_pdf_file_count": 0,
            "expected_page_count": 0,
            "merged_page_count": 0,
            "details": details,
        }

    writer = PdfWriter()
    expected_page_count = 0

    for _persnr, pdf_path, pages, _hash in file_rows:
        reader = PdfReader(str(pdf_path))
        expected_page_count += pages
        for page in reader.pages:
            writer.add_page(page)

    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    with out_pdf.open("wb") as f:
        writer.write(f)

    merged_page_count = _count_pdf_pages(out_pdf)
    duplicate_count = sum(1 for row in details if row.get("included") == "Nein")

    return {
        "pdf_file_count": len(file_rows),
        "duplicate_pdf_file_count": duplicate_count,
        "expected_page_count": expected_page_count,
        "merged_page_count": merged_page_count,
        "details": details,
    }


def _write_audit_compat(
    out_path: Path,
    grouped: dict[str, list[Path]],
    email_map: dict[str, str],
    email_records: dict[str, dict[str, str]],
    invalid_files: list[Path],
    invalid_pdf_details: list[dict],
    pdf_errors_by_persnr: dict[str, list[str]],
    missing_email_persnr: list[str],
    missing_files_persnr: list[str],
    bundle_details: list[dict],
    validation: dict,
) -> None:
    params = inspect.signature(write_audit_check_xlsx).parameters
    kwargs = {
        "out_path": out_path,
        "grouped": grouped,
        "email_map": email_map,
        "invalid_files": invalid_files,
        "missing_email_persnr": missing_email_persnr,
        "missing_files_persnr": missing_files_persnr,
    }
    if "bundle_details" in params:
        kwargs["bundle_details"] = bundle_details
    if "validation" in params:
        kwargs["validation"] = validation
    if "email_records" in params:
        kwargs["email_records"] = email_records
    if "invalid_pdf_details" in params:
        kwargs["invalid_pdf_details"] = invalid_pdf_details
    if "pdf_errors_by_persnr" in params:
        kwargs["pdf_errors_by_persnr"] = pdf_errors_by_persnr
    write_audit_check_xlsx(**kwargs)


def _merge_employee_pdfs(pdf_files: list[Path], out_pdf: Path) -> None:
    _require_pdf_support()

    if not pdf_files:
        raise ValueError("Keine PDF-Dateien zum Zusammenführen vorhanden.")

    pdf_files = _dedup_pdf_paths(pdf_files)

    writer = PdfWriter()
    for pdf_path in pdf_files:
        reader = PdfReader(str(pdf_path))
        for page in reader.pages:
            writer.add_page(page)

    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    with out_pdf.open("wb") as f:
        writer.write(f)


def _encrypt_pdf(in_pdf: Path, out_pdf: Path, password: str) -> None:
    _require_pdf_support()

    reader = PdfReader(str(in_pdf))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    if password:
        writer.encrypt(password)
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    with out_pdf.open("wb") as f:
        writer.write(f)


def _write_send_report_xlsx(out_path: Path, rows: list[dict]) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Versand"
    ws.append(
        [
            "PersNr",
            "Name, Vorname",
            "Email",
            "Dateien",
            "Anzahl",
            "Status",
            "Anhang",
            "Passwort",
            "Fehler",
        ]
    )
    for row in rows:
        ws.append(
            [
                row.get("PersNr", ""),
                format_name_vorname(row.get("Name", ""), row.get("Vorname", "")),
                row.get("Email", ""),
                row.get("Files", ""),
                row.get("Count", 0),
                row.get("Status", ""),
                row.get("Attachment", ""),
                "",
                row.get("Error", ""),
            ]
        )

    for col in ws.columns:
        max_len = 0
        col_letter = col[0].column_letter
        for cell in col:
            val = "" if cell.value is None else str(cell.value)
            max_len = max(max_len, len(val))
        ws.column_dimensions[col_letter].width = min(max_len + 2, 80)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)


def action_check(pdf_input: Path, excel_path: Path, progress_cb: ProgressCb = None) -> dict:
    run_id = make_run_id(pdf_input.name, prefix="check_")
    run_dir = run_dir_from_id(run_id)
    run_dir.mkdir(parents=True, exist_ok=True)

    scan_result = _prepare_pdf_input(pdf_input, run_dir, progress_cb=progress_cb)

    grouped = scan_result["grouped"]
    invalid_files = scan_result["invalid_files"]

    _p(progress_cb, "PDF-Dateien werden geprüft...")
    pdf_validation = _validate_grouped_pdf_files(grouped)
    valid_grouped = pdf_validation["valid_grouped"]
    pdf_page_counts = pdf_validation["page_counts"]
    pdf_errors_by_persnr = pdf_validation["errors_by_persnr"]
    invalid_pdf_details = pdf_validation["error_details"]

    _p(progress_cb, "Excel-Datei wird gelesen…")
    email_records = load_email_records(excel_path)
    email_map = _email_map_from_records(email_records)

    _p(progress_cb, "PDF-Dateien und E-Mail-Adressen werden abgeglichen…")
    grouped_persnr = set(grouped.keys())
    email_persnr = set(email_map.keys())

    missing_email_persnr = sorted(grouped_persnr - email_persnr, key=_persnr_sort_key)
    missing_files_persnr = sorted(email_persnr - grouped_persnr, key=_persnr_sort_key)

    _p(progress_cb, "Sammel-PDF ohne E-Mail wird erstellt…")
    missing_pdf_path = run_dir / "ohne_email_gesamt.pdf"
    bundle_stats = build_missing_email_bundle(
        grouped=valid_grouped,
        missing_email_persnr=missing_email_persnr,
        out_pdf=missing_pdf_path,
    )

    validation = {
        "total_input_pdf_files": scan_result["total_pdf_files"],
        "valid_input_pdf_files": scan_result["valid_pdf_files"],
        "invalid_input_pdf_files": len(invalid_files),
        "unreadable_pdf_files": len(invalid_pdf_details),
        "employees_with_email": len(grouped_persnr & email_persnr),
        "employees_without_email": len(missing_email_persnr),
        "expected_bundle_pdf_files": bundle_stats["pdf_file_count"],
        "duplicate_bundle_pdf_files": bundle_stats["duplicate_pdf_file_count"],
        "expected_bundle_pages": bundle_stats["expected_page_count"],
        "actual_bundle_pages": bundle_stats["merged_page_count"],
        "page_check_ok": bundle_stats["expected_page_count"] == bundle_stats["merged_page_count"],
    }

    _p(progress_cb, "Audit-Datei wird erstellt…")
    audit_path = run_dir / "audit_check.xlsx"
    _write_audit_compat(
        out_path=audit_path,
        grouped=grouped,
        email_map=email_map,
        email_records=email_records,
        invalid_files=invalid_files,
        invalid_pdf_details=invalid_pdf_details,
        pdf_errors_by_persnr=pdf_errors_by_persnr,
        missing_email_persnr=missing_email_persnr,
        missing_files_persnr=missing_files_persnr,
        bundle_details=bundle_stats["details"],
        validation=validation,
    )

    table_rows: list[dict] = []
    for persnr in sorted(grouped.keys(), key=_persnr_sort_key):
        files = _dedup_pdf_paths(grouped[persnr])
        email = email_map.get(persnr, "")
        pdf_errors = pdf_errors_by_persnr.get(persnr, [])
        status = "Fehler" if pdf_errors else ("OK" if email else "Keine E-Mail")
        total_pages = sum(pdf_page_counts.get(_pdf_path_key(p), 0) for p in files)
        table_rows.append(
            {
                "PersNr": persnr,
                **_person_values(email_records, persnr),
                "Email": email,
                "Files": ", ".join(p.name for p in files),
                "Count": len(files),
                "Pages": total_pages,
                "Status": status,
                "Attachment": "",
                "Password": "",
                "Error": "; ".join(pdf_errors),
            }
        )

    for persnr in missing_files_persnr:
        table_rows.append(
            {
                "PersNr": persnr,
                **_person_values(email_records, persnr),
                "Email": email_map.get(persnr, ""),
                "Files": "",
                "Count": 0,
                "Pages": 0,
                "Status": "Keine Dateien",
                "Attachment": "",
                "Password": "",
                "Error": "",
            }
        )

    summary = {
        "total_pdf_files": scan_result["total_pdf_files"],
        "valid_pdf_files": scan_result["valid_pdf_files"],
        "invalid_pdf_files": len(invalid_files),
        "unreadable_pdf_files": len(invalid_pdf_details),
        "unique_persnr_count": scan_result["unique_persnr_count"],
        "missing_email_count": len(missing_email_persnr),
        "missing_files_count": len(missing_files_persnr),
        "missing_pdf_count": bundle_stats["pdf_file_count"],
        "duplicate_bundle_pdf_files": bundle_stats["duplicate_pdf_file_count"],
        "expected_bundle_pages": bundle_stats["expected_page_count"],
        "actual_bundle_pages": bundle_stats["merged_page_count"],
        "page_check_ok": validation["page_check_ok"],
    }

    _p(progress_cb, "Prüfung abgeschlossen.")
    return {
        "mode": "check",
        "run_id": run_id,
        "run_dir": run_dir,
        "audit_path": audit_path,
        "missing_pdf_path": missing_pdf_path if missing_pdf_path.exists() else None,
        "summary": summary,
        "table_rows": table_rows,
        "grouped": grouped,
        "prepared_folder": scan_result.get("prepared_folder"),
        "source_kind": scan_result.get("source_kind"),
        "email_map": email_map,
        "email_records": email_records,
        "invalid_files": invalid_files,
        "invalid_pdf_details": invalid_pdf_details,
        "pdf_errors_by_persnr": pdf_errors_by_persnr,
        "missing_email_persnr": missing_email_persnr,
        "missing_files_persnr": missing_files_persnr,
        "bundle_stats": bundle_stats,
        "validation": validation,
    }


def action_send(
    pdf_input: Path,
    excel_path: Path,
    settings: dict,
    company_id: str | None = None,
    dry_run: bool = True,
    allowed_persnr: set[str] | None = None,
    progress_cb: ProgressCb = None,
) -> dict:
    try:
        from .mailer import (
            send_email_with_attachment,
            send_outlook_email_with_attachment,
            test_outlook_connection,
            test_smtp_connection,
        )
    except Exception as exc:
        raise ImportError(
            "mailer.py fehlt oder enthält Fehler. Bitte legen Sie core/mailer.py in den Projektordner."
        ) from exc

    run_id = make_run_id(pdf_input.name, prefix="send_")
    run_dir = run_dir_from_id(run_id)
    run_dir.mkdir(parents=True, exist_ok=True)

    scan_result = _prepare_pdf_input(pdf_input, run_dir, progress_cb=progress_cb)
    grouped = scan_result["grouped"]
    invalid_files = scan_result["invalid_files"]

    _p(progress_cb, "PDF-Dateien werden geprüft...")
    pdf_validation = _validate_grouped_pdf_files(grouped)
    valid_grouped = pdf_validation["valid_grouped"]
    pdf_errors_by_persnr = pdf_validation["errors_by_persnr"]
    invalid_pdf_details = pdf_validation["error_details"]

    _p(progress_cb, "Excel-Datei wird gelesen…")
    email_records = load_email_records(excel_path)
    email_map = _email_map_from_records(email_records)
    if allowed_persnr is not None:
        grouped = {persnr: files for persnr, files in grouped.items() if persnr in allowed_persnr}
        valid_grouped = {persnr: files for persnr, files in valid_grouped.items() if persnr in allowed_persnr}
        pdf_errors_by_persnr = {
            persnr: errors for persnr, errors in pdf_errors_by_persnr.items() if persnr in allowed_persnr
        }
        invalid_pdf_details = [
            row for row in invalid_pdf_details if str(row.get("persnr", "") or "") in allowed_persnr
        ]
        email_records = {persnr: record for persnr, record in email_records.items() if persnr in allowed_persnr}
        email_map = {persnr: email for persnr, email in email_map.items() if persnr in allowed_persnr}

    grouped_persnr = set(grouped.keys())
    email_persnr = set(email_map.keys())
    missing_email_persnr = sorted(grouped_persnr - email_persnr, key=_persnr_sort_key)
    missing_files_persnr = sorted(email_persnr - grouped_persnr, key=_persnr_sort_key)

    mail_mode = str(settings.get("mail_mode", "smtp") or "smtp").strip().lower()
    smtp_settings = settings.get("smtp", {})
    from_email = str(smtp_settings.get("from_email") or "").strip()
    mail_text = settings.get("mail_text", {})
    subject_template = mail_text.get("subject", "Ihre Entgeltabrechnung für {monat} {jahr}")
    body_template = mail_text.get("body", "")
    body_html_template = mail_text.get("body_html", "")
    pdf_password_settings = settings.get("pdf_password", {})
    password_enabled = bool(pdf_password_settings.get("enabled", True))
    password_prefix = str(pdf_password_settings.get("prefix", "") or "")
    password_suffix = str(pdf_password_settings.get("suffix", "") or "")

    if mail_mode == "smtp":
        test_connection = lambda: test_smtp_connection(smtp_settings)
        send_message = lambda to_email, subject, body, attachment_path, html_body="": send_email_with_attachment(
            smtp_settings=smtp_settings,
            to_email=to_email,
            subject=subject,
            body=body,
            attachment_path=attachment_path,
            html_body=html_body,
        )
    elif mail_mode == "outlook":
        test_connection = lambda: test_outlook_connection(from_email)
        send_message = lambda to_email, subject, body, attachment_path, html_body="": send_outlook_email_with_attachment(
            to_email=to_email,
            subject=subject,
            body=body,
            attachment_path=attachment_path,
            from_email=from_email,
            html_body=html_body,
        )
    else:
        raise ValueError(
            f"Die Versandmethode '{mail_mode}' wird derzeit nicht unterstützt."
        )

    prepared_dir = run_dir / "prepared_pdfs"
    prepared_dir.mkdir(parents=True, exist_ok=True)

    audit_path = run_dir / "audit_check.xlsx"
    bundle_stats = build_missing_email_bundle(
        grouped=valid_grouped,
        missing_email_persnr=missing_email_persnr,
        out_pdf=(run_dir / "ohne_email_gesamt.pdf"),
    )
    validation = {
        "total_input_pdf_files": scan_result["total_pdf_files"],
        "valid_input_pdf_files": scan_result["valid_pdf_files"],
        "invalid_input_pdf_files": len(invalid_files),
        "unreadable_pdf_files": len(invalid_pdf_details),
        "employees_with_email": len(grouped_persnr & email_persnr),
        "employees_without_email": len(missing_email_persnr),
        "expected_bundle_pdf_files": bundle_stats["pdf_file_count"],
        "duplicate_bundle_pdf_files": bundle_stats["duplicate_pdf_file_count"],
        "expected_bundle_pages": bundle_stats["expected_page_count"],
        "actual_bundle_pages": bundle_stats["merged_page_count"],
        "page_check_ok": bundle_stats["expected_page_count"] == bundle_stats["merged_page_count"],
    }
    _write_audit_compat(
        out_path=audit_path,
        grouped=grouped,
        email_map=email_map,
        email_records=email_records,
        invalid_files=invalid_files,
        invalid_pdf_details=invalid_pdf_details,
        pdf_errors_by_persnr=pdf_errors_by_persnr,
        missing_email_persnr=missing_email_persnr,
        missing_files_persnr=missing_files_persnr,
        bundle_details=bundle_stats["details"],
        validation=validation,
    )

    missing_pdf_path = run_dir / "ohne_email_gesamt.pdf"

    if not dry_run:
        _p(progress_cb, f"Versandmethode '{mail_mode}' wird geprüft…")
        test_connection()

    sent_count = 0
    failed_count = 0
    skipped_count = 0
    rows: list[dict] = []

    _p(progress_cb, "Mitarbeiter-PDFs werden erstellt…")
    for persnr in sorted(grouped.keys(), key=_persnr_sort_key):
        files = _dedup_pdf_paths(grouped[persnr])
        email = email_map.get(persnr, "")
        file_names = ", ".join(p.name for p in files)
        pdf_errors = pdf_errors_by_persnr.get(persnr, [])

        row = {
            "PersNr": persnr,
            **_person_values(email_records, persnr),
            "Email": email,
            "Files": file_names,
            "Count": len(files),
            "Status": "",
            "Attachment": "",
            "Password": "",
            "Error": "",
        }

        if pdf_errors:
            row["Status"] = "Fehler"
            row["Error"] = "; ".join(pdf_errors)
            failed_count += 1
            rows.append(row)
            _p(progress_cb, f"Fehler bei {persnr}: {row['Error']}")
            continue

        if not email:
            row["Status"] = "Keine E-Mail"
            skipped_count += 1
            rows.append(row)
            continue

        merged_pdf = prepared_dir / f"{persnr}.pdf"
        final_pdf = prepared_dir / f"{persnr}_protected.pdf" if password_enabled else merged_pdf
        password = f"{password_prefix}{persnr}{password_suffix}" if password_enabled else ""

        try:
            _merge_employee_pdfs(files, merged_pdf)
            if password_enabled:
                _encrypt_pdf(merged_pdf, final_pdf, password)
                try:
                    merged_pdf.unlink(missing_ok=True)
                except Exception:
                    pass

            context = build_mail_context(settings, persnr, company_id=company_id)
            subject = format_message_template(subject_template, context)
            body = format_message_template(body_template, context)
            body_html = format_message_template(body_html_template, context) if body_html_template else ""

            row["Attachment"] = final_pdf.name
            row["Password"] = password

            if dry_run:
                row["Status"] = "Dry-Run"
                sent_count += 1
                _p(progress_cb, f"[Dry-Run] {persnr} -> {email}")
            else:
                send_message(email, subject, body, final_pdf, body_html)
                row["Status"] = "Gesendet"
                sent_count += 1
                _p(progress_cb, f"Gesendet via {mail_mode}: {persnr} -> {email}")
        except Exception as exc:
            row["Status"] = "Fehler"
            row["Error"] = str(exc)
            failed_count += 1
            _p(progress_cb, f"Fehler bei {persnr}: {exc}")

        rows.append(row)

    for persnr in missing_files_persnr:
        rows.append(
            {
                "PersNr": persnr,
                **_person_values(email_records, persnr),
                "Email": email_map.get(persnr, ""),
                "Files": "",
                "Count": 0,
                "Status": "Keine Dateien",
                "Attachment": "",
                "Password": "",
                "Error": "",
            }
        )

    send_report_path = run_dir / "send_report.xlsx"
    _write_send_report_xlsx(send_report_path, rows)

    summary = {
        "total_pdf_files": scan_result["total_pdf_files"],
        "valid_pdf_files": scan_result["valid_pdf_files"],
        "invalid_pdf_files": len(invalid_files),
        "unreadable_pdf_files": len(invalid_pdf_details),
        "unique_persnr_count": scan_result["unique_persnr_count"],
        "missing_email_count": len(missing_email_persnr),
        "missing_files_count": len(missing_files_persnr),
        "missing_pdf_count": bundle_stats["pdf_file_count"],
        "duplicate_bundle_pdf_files": bundle_stats["duplicate_pdf_file_count"],
        "expected_bundle_pages": bundle_stats["expected_page_count"],
        "actual_bundle_pages": bundle_stats["merged_page_count"],
        "page_check_ok": validation["page_check_ok"],
        "prepared_or_sent_count": sent_count,
        "failed_count": failed_count,
        "skipped_count": skipped_count,
        "dry_run": dry_run,
        "mail_mode": mail_mode,
    }

    _p(progress_cb, "Versandlauf abgeschlossen.")
    return {
        "mode": "send",
        "run_id": run_id,
        "run_dir": run_dir,
        "audit_path": audit_path,
        "send_report_path": send_report_path,
        "missing_pdf_path": missing_pdf_path if missing_pdf_path.exists() else None,
        "summary": summary,
        "table_rows": rows,
        "grouped": grouped,
        "prepared_folder": scan_result.get("prepared_folder"),
        "source_kind": scan_result.get("source_kind"),
        "email_map": email_map,
        "email_records": email_records,
        "invalid_files": invalid_files,
        "invalid_pdf_details": invalid_pdf_details,
        "pdf_errors_by_persnr": pdf_errors_by_persnr,
        "missing_email_persnr": missing_email_persnr,
        "missing_files_persnr": missing_files_persnr,
        "bundle_stats": bundle_stats,
        "validation": validation,
    }

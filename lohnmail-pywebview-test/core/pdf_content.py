"""Conservative personnel assignment from text; no OCR or filename fallback."""
import re
from pathlib import Path

import fitz

from .excel_io import normalize_persnr


PERSONNEL_RECOGNITION_REVISION = "labelled-personnel-v2"


PERSONNEL_LABEL = re.compile(
    r"(?<!\w)(?:Pers\.\s*-\s*Nr\.?|Personal(?:nummer|[\s.-]*Nr\.?))"
    r"(?![A-Za-zÄÖÜäöüß])",
    re.IGNORECASE,
)


def recognize_personnel_text(text: str) -> dict:
    """Read all explicit fields on one page, never guess among arbitrary numbers.

    DATEV can contain both a table heading ``Personal-Nr. Geburtsdatum``
    (not a value) and an explicit ``*Pers.-Nr. 03028*`` elsewhere. Only the
    known adjacent heading is ignored; malformed values still fail closed.
    """
    def result(persnr="", reason=""):
        return {"persnr": persnr, "reason": reason, "source": "PDF-Inhalt"}

    if not text.strip():
        return result(reason="kein lesbarer Text. OCR wird nicht unterstützt.")
    numbers = set()
    labels = list(PERSONNEL_LABEL.finditer(text))
    for index, label in enumerate(labels):
        end = labels[index + 1].start() if index + 1 < len(labels) else len(text)
        value = re.match(r"\s*:?\s*(\S+)", text[label.end():end])
        raw = value.group(1).strip("*") if value else ""
        if raw.casefold().rstrip(":") == "geburtsdatum":
            continue
        if not re.fullmatch(r"[0-9]{1,5}", raw):
            return result(reason="Personalnummer ist nicht eindeutig lesbar (1–5 Ziffern erwartet).")
        numbers.add(normalize_persnr(raw))
    if not numbers:
        return result(reason="keine gekennzeichnete Personalnummer gefunden.")
    if len(numbers) != 1:
        return result(reason="unterschiedliche Personalnummern gefunden.")
    return result(persnr=next(iter(numbers)))


def recognize_pdf_content(path: Path) -> dict:
    """Require one consistent, explicitly labelled number on every page."""
    def error(message):
        return {"persnr": "", "reason": message, "source": "PDF-Inhalt"}

    try:
        with fitz.open(path) as document:
            if not document.is_pdf:
                return error("Datei ist kein gültiges PDF.")
            if document.needs_pass:
                return error("PDF ist passwortgeschützt. Inhalt kann nicht geprüft werden.")
            if not document.page_count:
                return error("PDF enthält keine Seiten.")
            numbers = set()
            for index, page in enumerate(document, 1):
                match = recognize_personnel_text(page.get_text("text") or "")
                if match["reason"]:
                    return error(f"Seite {index}: {match['reason']}")
                numbers.add(match["persnr"])
                if len(numbers) != 1:
                    return error("PDF enthält unterschiedliche Personalnummern auf mehreren Seiten. Keine Zuordnung.")
            return {"persnr": next(iter(numbers)), "reason": "", "source": "PDF-Inhalt"}
    except Exception:
        # PDF parser errors may contain document data/paths: return only a safe reason.
        return error("PDF ist beschädigt oder kann nicht gelesen werden.")

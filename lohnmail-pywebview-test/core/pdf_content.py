"""Conservative personnel assignment from text; no OCR or filename fallback."""
import re
from pathlib import Path

import fitz

from .excel_io import normalize_persnr


PERSONNEL_RECOGNITION_REVISION = "labelled-personnel-v3"


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


def recognize_personnel_page(page) -> dict:
    """Associate standalone field headings with the value directly below them.

    DATEV social-insurance forms store headings before values in the PDF stream:
    ``Pers.-Nr. / Datum: / Seite: ...``. Stream order is not visual field order.
    Reconnect only the immediate value in the personnel column, then use the
    same strict parser for every occurrence (including the address-block number).
    Never search the page for an arbitrary numeric candidate.
    """
    words = page.get_text("words") or []
    source_lines = [line for block in page.get_text("dict").get("blocks", [])
                    for line in block.get("lines", [])]
    texts = ["".join(span.get("text", "") for span in line.get("spans", []))
             for line in source_lines]
    lines = []
    for index, line in enumerate(source_lines):
        text = texts[index]
        label = text.strip().rstrip(":").strip()
        following = texts[index + 1].strip() if index + 1 < len(texts) else ""
        # Reconstruct only displaced fields followed by a known heading.
        # Never overwrite an already adjacent value with a number below it.
        displaced = re.match(r"(?:Geburtsdatum\b|Datum\s*:|Seite\s*:)", following, re.IGNORECASE)
        if PERSONNEL_LABEL.fullmatch(label) and displaced:
            x0, y0, x1, y1 = line["bbox"]
            # A narrow column and one line-height below the heading. The
            # insurance number, date and page number are separate fields.
            candidates = [w for w in words
                          if x0 - 3 <= w[0] <= x0 + 8
                          and w[2] <= x0 + max(x1 - x0 + 12, 60)
                          and y0 + (y1 - y0) / 2 <= w[1] <= y1 + 12]
            if candidates:
                first_y = min(w[1] for w in candidates)
                row = [w for w in words
                       if x0 - 3 <= w[0] and w[2] <= x0 + max(x1 - x0 + 12, 60)
                       and abs(w[1] - first_y) <= 2]
                # Overlapping values must fail, not silently pick one.
                value = str(row[0][4]) if len(row) == 1 else "?"
                text += " " + value
        lines.append(text)
    return recognize_personnel_text("\n".join(lines))


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
                match = recognize_personnel_page(page)
                if match["reason"]:
                    return error(f"Seite {index}: {match['reason']}")
                numbers.add(match["persnr"])
                if len(numbers) != 1:
                    return error("PDF enthält unterschiedliche Personalnummern auf mehreren Seiten. Keine Zuordnung.")
            return {"persnr": next(iter(numbers)), "reason": "", "source": "PDF-Inhalt"}
    except Exception:
        # PDF parser errors may contain document data/paths: return only a safe reason.
        return error("PDF ist beschädigt oder kann nicht gelesen werden.")

"""Company-scoped PDF assignment rules. Never search arbitrary numbers."""
import re

from .excel_io import normalize_persnr

STANDARD_RULE = {"mode": "standard"}
STANDARD_NAME = re.compile(r"^([0-9]{1,5})(?:_([0-9]+))?\.pdf$", re.IGNORECASE)
SEPARATORS = ("_", "-", " ")


def validate_rule(value=None) -> dict:
    if value is None:
        return dict(STANDARD_RULE)
    if not isinstance(value, dict):
        raise ValueError("PDF-Dateiformat ist ungültig. Bitte in den Einstellungen neu festlegen.")
    if value.get("mode") in {"standard", "content"}:
        return {"mode": value["mode"]}
    if value.get("mode") != "custom":
        raise ValueError("Unbekanntes PDF-Dateiformat. Bitte Standardformat wiederherstellen.")
    sep, index, count = value.get("separator"), value.get("index"), value.get("parts")
    if (sep not in SEPARATORS or type(index) is not int or type(count) is not int
            or not 2 <= count <= 40 or not 0 <= index < count):
        raise ValueError("Bitte Trennzeichen und den Teil mit der Personalnummer auswählen.")
    return {"mode": "custom", "separator": sep, "index": index, "parts": count}


def company_rule(settings: dict, company_id=None) -> dict:
    selected = settings.get("selected_company_id") if company_id is None else company_id
    for company in settings.get("companies", []):
        if isinstance(company, dict) and company.get("id") == selected:
            return validate_rule(company.get("pdf_filename_rule"))
    return dict(STANDARD_RULE)


def recognize_filename(name: str, rule=None) -> dict:
    rule = validate_rule(rule)
    if rule["mode"] == "content":
        return {"persnr": "", "reason": "PDF-Inhalt muss gelesen werden. Bitte am PDF-Ordner prüfen."}
    if not isinstance(name, str) or "/" in name or "\\" in name or not name.lower().endswith(".pdf"):
        return {"persnr": "", "reason": "Keine gültige PDF-Datei."}
    standard = STANDARD_NAME.fullmatch(name)
    if standard:
        # A two-part custom rule can overlap the legacy suffix syntax.
        # Refuse conflicting interpretations rather than assigning a payroll
        # document to whichever employee happens to be found first.
        if rule["mode"] == "custom":
            parts = name[:-4].split(rule["separator"])
            if len(parts) == rule["parts"]:
                raw = parts[rule["index"]]
                if re.fullmatch(r"[0-9]{1,5}", raw) and normalize_persnr(raw) != normalize_persnr(standard[1]):
                    return {"persnr": "", "reason": "Mehrdeutig: Standardformat und eigenes Dateiformat ergeben unterschiedliche Personalnummern."}
        return {"persnr": normalize_persnr(standard[1]), "reason": ""}
    if rule["mode"] == "standard":
        return {"persnr": "", "reason": "Dateiname entspricht nicht dem Standardformat (00022.pdf / 00022_1.pdf)."}
    parts = name[:-4].split(rule["separator"])
    if len(parts) != rule["parts"] or any(not p.strip() for p in parts):
        return {"persnr": "", "reason": f"Struktur passt nicht: {rule['parts']} nicht leere Teile mit „{rule['separator']}“ erwartet."}
    raw = parts[rule["index"]]
    if not re.fullmatch(r"[0-9]{1,5}", raw):
        return {"persnr": "", "reason": f"Teil {rule['index'] + 1} muss eine Personalnummer mit 1–5 Ziffern enthalten."}
    return {"persnr": normalize_persnr(raw), "reason": ""}


def match_filename(name: str, rule, records: dict) -> dict:
    result = recognize_filename(name, rule)
    return _match_records(result, name, records)


def _match_records(result: dict, name: str, records: dict | None) -> dict:
    number = result["persnr"]
    if number and records is not None and number not in records:
        result["reason"] = "Personalnummer nicht in der Excel-Liste gefunden."
    record = (records or {}).get(number, {}) if not result["reason"] else {}
    result.update(file=name, matched=bool(number and not result["reason"]),
                  employee=" ".join(str(record.get(k) or "") for k in ("Vorname", "Name")).strip())
    return result


def match_pdf_file(path, rule=None, records=None) -> dict:
    """Single assignment entry point for preview, check, prepare and send."""
    rule = validate_rule(rule)
    if rule["mode"] == "content":
        from .pdf_content import recognize_pdf_content
        result = recognize_pdf_content(path)
    else:
        result = {**recognize_filename(path.name, rule), "source": "Dateiname"}
    return _match_records(result, path.name, records)

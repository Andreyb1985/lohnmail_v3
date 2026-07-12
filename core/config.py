from copy import deepcopy
import json
import os
import shutil
import sys
from datetime import date, datetime
from pathlib import Path

APP_NAME = "LohnMail"
APP_TAGLINE = "Versand von Lohnabrechnungen \u2013 kompatibel mit DATEV"
APP_COPYRIGHT = "\u00a9 2026 Andrii Bakanov"
DEVELOPER_NAME = "Andrii Bakanov"
SUPPORT_EMAIL = "andriibakanov@gmail.com"
DSGVO_CLAIM = "DSGVO-konforme Verarbeitung. Alle Daten bleiben lokal auf Ihrem Rechner."

def build_default_settings(today: date | None = None) -> dict:
    resolved_today = today or date.today()
    return {
        "mail_mode": "smtp",
        "smtp": {
            "server": "",
            "port": 587,
            "username": "",
            "password": "",
            "security": "tls",
            "timeout_sec": 30,
            "from_email": "",
            "from_name": "Personalabteilung",
        },
        "pdf_password": {
            "enabled": True,
            "prefix": "",
            "suffix": "",
        },
        "mail_text": {
            "subject": "Ihre Entgeltabrechnung für {monat} {jahr}",
            "body": (
                "Sehr geehrte Damen und Herren,\n\n"
                "anbei erhalten Sie Ihre Entgeltabrechnung für {monat} {jahr}.\n\n"
                "Mit freundlichen Grüßen\n"
                "{from_name}\n"
                "{company_name}"
            ),
            "body_html": "",
        },
        "companies": [
            {"id": "gesob", "name": "GeSoB GmbH", "email_excel_file": ""}
        ],
        "selected_company_id": "gesob",
        "period": {
            "mode": "automatic_current_month",
            "month": resolved_today.month,
            "year": resolved_today.year,
        },
        "ui": {
            "dry_run_default": True,
            "remember_last_paths": True,
            "last_pdf_dir": "",
            "last_pdf_input_mode": "folder",
            "last_excel_file": "",
            "window_width": 1100,
            "window_height": 720,
        },
        "notifications": {
            "show_badge": True,
            "workflow_warnings": True,
            "validation_warnings": True,
            "processing_errors": True,
            "delivery_events": True,
            "auto_open_on_start": False,
        },
        "licensee": {
            "name": "",
            "email": "",
            "address": "",
            "company_number": "",
        },
        "license": {
            "key": "",
            "status": "unregistered",
            "server_url": "",
        },
    }


DEFAULT_SETTINGS = build_default_settings()


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def user_config_dir() -> Path:
    if sys.platform == "win32" and os.environ.get("APPDATA"):
        return Path(os.environ["APPDATA"]) / APP_NAME
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / APP_NAME


BASE_DIR = app_dir()
SETTINGS_TEMPLATE_PATH = BASE_DIR / "settings_template.json"
LEGACY_PROJECT_SETTINGS_PATH = BASE_DIR / "settings.json"
SETTINGS_DIR = user_config_dir()
SETTINGS_PATH = SETTINGS_DIR / "settings.json"
GESOB_DIR = BASE_DIR / "Gesob_Lohn"
GESOB_DIR.mkdir(parents=True, exist_ok=True)
_LAST_SETTINGS_WARNING = ""


def _merge_dict(defaults: dict, data: dict | None) -> dict:
    result = deepcopy(defaults)
    if isinstance(data, dict):
        result.update(data)
    return result


def _deep_merge_settings(data: dict) -> dict:
    merged = deepcopy(DEFAULT_SETTINGS)
    if isinstance(data, dict):
        merged.update(data)

    merged["smtp"] = _merge_dict(DEFAULT_SETTINGS["smtp"], merged.get("smtp"))
    merged["pdf_password"] = _merge_dict(DEFAULT_SETTINGS["pdf_password"], merged.get("pdf_password"))
    merged["mail_text"] = _merge_dict(DEFAULT_SETTINGS["mail_text"], merged.get("mail_text"))
    merged["period"] = _merge_dict(DEFAULT_SETTINGS["period"], merged.get("period"))
    merged["ui"] = _merge_dict(DEFAULT_SETTINGS["ui"], merged.get("ui"))
    merged["notifications"] = _merge_dict(DEFAULT_SETTINGS["notifications"], merged.get("notifications"))
    merged["licensee"] = _merge_dict(DEFAULT_SETTINGS["licensee"], merged.get("licensee"))
    merged["license"] = _merge_dict(DEFAULT_SETTINGS["license"], merged.get("license"))

    companies = merged.get("companies")
    has_company_excel_file = False
    if not isinstance(companies, list) or not companies:
        merged["companies"] = deepcopy(DEFAULT_SETTINGS["companies"])
    else:
        normalized = []
        for item in companies:
            if not isinstance(item, dict):
                continue
            has_company_excel_file = has_company_excel_file or "email_excel_file" in item
            company_id = str(item.get("id", "") or "").strip()
            company_name = str(item.get("name", "") or "").strip()
            if not company_id:
                continue
            if not company_name:
                company_name = company_id
            email_excel_file = str(item.get("email_excel_file", "") or item.get("excel_file", "") or "").strip()
            normalized.append({
                "id": company_id,
                "name": company_name,
                "email_excel_file": email_excel_file,
            })
        if not normalized:
            normalized = deepcopy(DEFAULT_SETTINGS["companies"])
        merged["companies"] = normalized

    selected_company_id = str(merged.get("selected_company_id", "") or "").strip()
    known_ids = {c["id"] for c in merged["companies"]}
    if not selected_company_id or selected_company_id not in known_ids:
        merged["selected_company_id"] = merged["companies"][0]["id"]

    last_excel_file = str(merged.get("ui", {}).get("last_excel_file", "") or "").strip()
    if last_excel_file and not has_company_excel_file:
        for company in merged["companies"]:
            if company["id"] == merged["selected_company_id"] and not company.get("email_excel_file"):
                company["email_excel_file"] = last_excel_file
                break

    return merged


def ensure_default_config() -> None:
    if SETTINGS_PATH.exists():
        return

    for candidate_path in [SETTINGS_TEMPLATE_PATH, LEGACY_PROJECT_SETTINGS_PATH]:
        if not candidate_path.exists():
            continue
        try:
            with candidate_path.open("r", encoding="utf-8") as f:
                seed_data = json.load(f)
            if isinstance(seed_data, dict):
                save_settings(seed_data)
                return
        except Exception:
            continue

    save_settings(DEFAULT_SETTINGS)


def _backup_broken_settings() -> Path | None:
    if not SETTINGS_PATH.exists():
        return None

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_path = SETTINGS_PATH.with_name(f"{SETTINGS_PATH.stem}.broken_{timestamp}{SETTINGS_PATH.suffix}")
    shutil.copy2(SETTINGS_PATH, backup_path)
    return backup_path


def consume_settings_warning() -> str:
    global _LAST_SETTINGS_WARNING
    warning = _LAST_SETTINGS_WARNING
    _LAST_SETTINGS_WARNING = ""
    return warning


def ensure_settings_file() -> None:
    ensure_default_config()


def load_settings() -> dict:
    global _LAST_SETTINGS_WARNING
    ensure_default_config()
    try:
        with SETTINGS_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError("settings.json enth\u00e4lt kein g\u00fcltiges JSON-Objekt.")
    except Exception as exc:
        backup_path = _backup_broken_settings()
        data = deepcopy(DEFAULT_SETTINGS)
        save_settings(data)
        if backup_path:
            _LAST_SETTINGS_WARNING = (
                "settings.json konnte nicht gelesen werden. "
                f"Eine Sicherung wurde erstellt: {backup_path}. "
                "Ein neuer Standard-Settings-File wurde angelegt."
            )
        else:
            _LAST_SETTINGS_WARNING = f"settings.json konnte nicht gelesen werden: {exc}"

    return _deep_merge_settings(data)


def save_settings(settings: dict) -> None:
    merged = _deep_merge_settings(settings)
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with SETTINGS_PATH.open("w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)


def get_company_name(settings: dict | None = None, company_id: str | None = None) -> str:
    settings = settings or load_settings()
    companies = settings.get("companies", [])
    target_id = str(company_id or settings.get("selected_company_id", "") or "").strip()

    if isinstance(companies, list):
        for company in companies:
            if not isinstance(company, dict):
                continue
            if str(company.get("id", "") or "").strip() == target_id:
                return str(company.get("name", "") or "")
        for company in companies:
            if isinstance(company, dict) and company.get("name"):
                return str(company.get("name"))

    return ""


def get_company_email_excel_file(settings: dict | None = None, company_id: str | None = None) -> str:
    settings = settings or load_settings()
    companies = settings.get("companies", [])
    target_id = str(company_id or settings.get("selected_company_id", "") or "").strip()

    if isinstance(companies, list):
        for company in companies:
            if not isinstance(company, dict):
                continue
            if str(company.get("id", "") or "").strip() == target_id:
                return str(company.get("email_excel_file", "") or "")

    return ""

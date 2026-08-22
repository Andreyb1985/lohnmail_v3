import html
import re
from collections.abc import Mapping

from .config import get_company_name
from .period import get_payroll_period

_MAIL_PLACEHOLDER_RE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")
_BIRTH_DATE_PASSWORD_NOTICE_MARKER = 'data-lohnmail-password-notice="birth-date"'


def _birth_date_password_notice(password_settings: Mapping[str, object]) -> str:
    if not bool(password_settings.get("enabled", True)):
        return ""
    source = str(password_settings.get("source", "persnr") or "persnr").strip().lower()
    if source != "birth_date":
        return ""

    prefix = str(password_settings.get("prefix", "") or "")
    suffix = str(password_settings.get("suffix", "") or "")
    if prefix or suffix:
        return (
            "Ihr PDF-Passwort wird aus Ihrem Geburtsdatum gebildet. "
            f"Format: {prefix}TTMMJJJJ{suffix} (Tag, Monat, Jahr), "
            f"z. B. {prefix}18061992{suffix}."
        )
    return (
        "Ihr PDF-Passwort ist Ihr Geburtsdatum im Format TTMMJJJJ "
        "(Tag, Monat, Jahr), z. B. 18061992."
    )


def append_pdf_password_notice(
    body: str,
    body_html: str,
    password_settings: Mapping[str, object] | None,
) -> tuple[str, str]:
    """Add the birth-date password hint to rendered payslip messages."""
    resolved_settings = password_settings if isinstance(password_settings, Mapping) else {}
    notice = _birth_date_password_notice(resolved_settings)
    plain_body = str(body or "")
    html_body = str(body_html or "")
    if not notice:
        return plain_body, html_body

    if notice not in plain_body:
        plain_body = f"{plain_body.rstrip()}\n\n{notice}" if plain_body.strip() else notice

    if html_body and _BIRTH_DATE_PASSWORD_NOTICE_MARKER not in html_body:
        notice_html = (
            f'<p {_BIRTH_DATE_PASSWORD_NOTICE_MARKER}>'
            f"{html.escape(notice)}"
            "</p>"
        )
        closing_body = re.search(r"</body\s*>", html_body, flags=re.IGNORECASE)
        if closing_body:
            html_body = (
                html_body[:closing_body.start()].rstrip()
                + "\n"
                + notice_html
                + "\n"
                + html_body[closing_body.start():]
            )
        else:
            html_body = f"{html_body.rstrip()}\n{notice_html}"

    return plain_body, html_body


def format_message_template(template: str, context: Mapping[str, object]) -> str:
    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in context:
            raise ValueError(f"Unbekannter Platzhalter im Mailtext: {{{key}}}")
        return str(context[key])

    return _MAIL_PLACEHOLDER_RE.sub(replace, str(template or ""))


def format_name_vorname(name: str = "", vorname: str = "") -> str:
    return ", ".join(
        part.strip()
        for part in [str(name or ""), str(vorname or "")]
        if part.strip()
    )


def format_name_vorname_row(row: Mapping[str, object]) -> str:
    return format_name_vorname(
        name=str(row.get("Name", "") or ""),
        vorname=str(row.get("Vorname", "") or ""),
    )


def build_mail_context(
    settings: dict,
    persnr: str,
    company_id: str | None = None,
    company_name: str | None = None,
) -> dict[str, str | int]:
    period = get_payroll_period(settings)
    resolved_company_id = str(company_id or settings.get("selected_company_id", "") or "").strip()
    resolved_company_name = str(company_name or get_company_name(settings, resolved_company_id) or "")

    return {
        "persnr": str(persnr or "").strip(),
        "monat": period["monat"],
        "jahr": period["jahr"],
        "company_name": resolved_company_name,
        "from_name": str(settings.get("smtp", {}).get("from_name", "") or "Personalabteilung"),
    }


def build_subject_preview(settings: dict, table_rows: list[dict]) -> str:
    sample_persnr = "10001"
    for row in table_rows:
        if row.get("Email") and int(row.get("Count", 0) or 0) > 0:
            sample_persnr = str(row.get("PersNr", "") or sample_persnr)
            break

    context = build_mail_context(
        settings,
        sample_persnr,
        company_id=str(settings.get("selected_company_id", "") or "").strip() or None,
    )
    template = str(settings.get("mail_text", {}).get("subject", "") or "")
    return format_message_template(template, context)


def build_send_preview_data(
    settings: dict,
    table_rows: list[dict],
    dry_run: bool,
    summary: dict | None = None,
    selected_persnr: set[str] | None = None,
) -> dict[str, object]:
    active_rows = table_rows
    if selected_persnr:
        active_rows = [
            row for row in table_rows if str(row.get("PersNr", "") or "") in selected_persnr
        ]

    sendable_rows = [
        row
        for row in active_rows
        if row.get("Email")
        and int(row.get("Count", 0) or 0) > 0
        and str(row.get("Status", "") or "").strip().lower() != "fehler"
    ]

    password_enabled = bool(settings.get("pdf_password", {}).get("enabled", True))
    preview_rows: list[dict[str, str]] = []
    for row in sendable_rows:
        persnr = str(row.get("PersNr", "") or "")
        attachment_name = f"{persnr}_protected.pdf" if password_enabled else f"{persnr}.pdf"
        preview_rows.append({
            "PersNr": persnr,
            "Name": str(row.get("Name", "") or ""),
            "Vorname": str(row.get("Vorname", "") or ""),
            "Email": str(row.get("Email", "") or ""),
            "AttachmentPreview": attachment_name,
            "Files": str(row.get("Files", "") or ""),
        })

    resolved_summary = summary or {}
    missing_email_count = sum(1 for row in active_rows if row.get("Status") == "Keine E-Mail")
    missing_files_count = sum(1 for row in active_rows if row.get("Status") == "Keine Dateien")
    summary_lines = [
        f"Versand an Mitarbeiter: {len(sendable_rows)}",
        f"Ohne E-Mail: {missing_email_count if selected_persnr else resolved_summary.get('missing_email_count', 0)}",
        f"Ohne PDF: {missing_files_count if selected_persnr else resolved_summary.get('missing_files_count', 0)}",
        f"Verschlüsselung: {'Ja' if password_enabled else 'Nein'}",
        f"Modus: {'Dry-Run' if dry_run else 'Reale Sendung'}",
    ]

    return {
        "summary_lines": summary_lines,
        "preview_rows": preview_rows,
        "subject_preview": build_subject_preview(settings, active_rows),
    }

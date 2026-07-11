from pathlib import Path
from typing import Callable

from .config import get_company_name
from .excel_io import load_email_records
from .message_templates import build_mail_context, format_message_template
from .orchestrator import action_check, action_send

ProgressCb = Callable[[str], None] | None


def _emit_progress(progress_cb: ProgressCb, message: str) -> None:
    if progress_cb is not None:
        progress_cb(message)


def load_mass_message_rows(excel_path: Path) -> list[dict[str, str]]:
    email_records = load_email_records(excel_path)
    return [
        {
            "PersNr": persnr,
            "Name": str(record.get("Name", "") or ""),
            "Vorname": str(record.get("Vorname", "") or ""),
            "Email": str(record.get("Email", "") or ""),
        }
        for persnr, record in sorted(email_records.items())
        if str(record.get("Email", "") or "").strip()
    ]


def run_main_job(
    mode: str,
    pdf_input: Path,
    excel_path: Path,
    settings: dict,
    dry_run: bool,
    selected_persnr: set[str] | None = None,
    progress_cb: ProgressCb = None,
) -> dict:
    if mode == "check":
        return action_check(pdf_input, excel_path, progress_cb=progress_cb)
    if mode == "send_preview":
        result = action_check(pdf_input, excel_path, progress_cb=progress_cb)
        result["mode"] = "send_preview"
        return result

    return action_send(
        pdf_input,
        excel_path,
        settings=settings,
        company_id=settings.get("selected_company_id"),
        dry_run=dry_run,
        allowed_persnr=selected_persnr,
        progress_cb=progress_cb,
    )


def run_mass_message_job(
    settings: dict,
    company_id: str,
    subject_template: str,
    body_template: str,
    recipients: list[dict],
    progress_cb: ProgressCb = None,
) -> dict:
    if not recipients:
        raise ValueError("Keine Empfänger vorhanden.")

    mail_mode = str(settings.get("mail_mode", "smtp") or "smtp").strip().lower()
    smtp_settings = settings.get("smtp", {})
    from_email = str(smtp_settings.get("from_email", "") or "").strip()

    if mail_mode == "smtp":
        from .mailer import send_email, test_smtp_connection

        _emit_progress(progress_cb, "SMTP-Verbindung wird geprüft...")
        test_smtp_connection(smtp_settings)
        send_message = lambda to_email, subject, body: send_email(
            smtp_settings=smtp_settings,
            to_email=to_email,
            subject=subject,
            body=body,
        )
    elif mail_mode == "outlook":
        from .mailer import send_outlook_email, test_outlook_connection

        _emit_progress(progress_cb, "Outlook-Verbindung wird geprüft...")
        test_outlook_connection(from_email)
        send_message = lambda to_email, subject, body: send_outlook_email(
            to_email=to_email,
            subject=subject,
            body=body,
            from_email=from_email,
        )
    else:
        raise ValueError(f"Unbekannte Versandmethode: {mail_mode}")

    errors = []
    sent_count = 0
    total_count = len(recipients)

    for index, row in enumerate(recipients, start=1):
        persnr = str(row.get("PersNr", "") or "")
        email = str(row.get("Email", "") or "").strip()
        context = build_mail_context(settings, persnr, company_id=company_id)
        subject = format_message_template(subject_template, context)
        body = format_message_template(body_template, context)

        try:
            send_message(email, subject, body)
            sent_count += 1
            _emit_progress(progress_cb, f"Nachricht gesendet ({index}/{total_count}): {persnr} -> {email}")
        except Exception as exc:
            errors.append({"PersNr": persnr, "Email": email, "Error": str(exc)})
            _emit_progress(progress_cb, f"Fehler ({index}/{total_count}): {persnr} -> {email}: {exc}")

    return {
        "mode": "mass_message",
        "sent_count": sent_count,
        "error_count": len(errors),
        "total_count": total_count,
        "errors": errors,
        "company_name": get_company_name(settings, company_id),
    }

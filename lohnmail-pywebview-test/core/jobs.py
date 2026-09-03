from pathlib import Path
from typing import Callable

from .config import company_output_dir, get_company_name
from .email_validation import validate_email_records
from .excel_io import load_email_records
from .message_templates import build_mail_context, format_message_template
from .orchestrator import action_check, action_send

ProgressCb = Callable[[str], None] | None


def _emit_progress(progress_cb: ProgressCb, message: str) -> None:
    if progress_cb is not None:
        progress_cb(message)


def load_mass_message_rows(excel_path: Path) -> list[dict]:
    email_records = load_email_records(excel_path)
    validations = validate_email_records(email_records)
    rows = []
    for persnr, record in sorted(email_records.items()):
        email = str(record.get("Email", "") or "").strip()
        if not email:
            continue
        validation = validations.get(persnr, {})
        rows.append({
            "PersNr": persnr,
            "Name": str(record.get("Name", "") or ""),
            "Vorname": str(record.get("Vorname", "") or ""),
            "Email": email,
            "EmailValidationCode": str(validation.get("code", "") or ""),
            "EmailValidationLabel": str(validation.get("label", "") or ""),
            "EmailValidationHint": str(validation.get("hint", "") or ""),
            "EmailValidationSendable": bool(validation.get("sendable", False)),
        })
    return rows


def validate_mass_message_recipients(recipients: list[dict], *, check_dns: bool) -> list[dict]:
    records = {
        str(index): {
            "Email": str(row.get("Email", "") or "").strip(),
            "ExcelRow": index + 1,
        }
        for index, row in enumerate(recipients)
    }
    validations = validate_email_records(records, check_dns=check_dns)
    return [
        {
            **row,
            "EmailValidationCode": str(validations[str(index)].get("code", "") or ""),
            "EmailValidationLabel": str(validations[str(index)].get("label", "") or ""),
            "EmailValidationHint": str(validations[str(index)].get("hint", "") or ""),
            "EmailValidationSendable": bool(validations[str(index)].get("sendable", False)),
        }
        for index, row in enumerate(recipients)
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
    output_dir = company_output_dir(settings, settings.get("selected_company_id"))
    if mode == "check":
        return action_check(pdf_input, excel_path, progress_cb=progress_cb, output_dir=output_dir)
    if mode == "send_preview":
        result = action_check(pdf_input, excel_path, progress_cb=progress_cb, output_dir=output_dir)
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
        output_dir=output_dir,
    )


def run_mass_message_job(
    settings: dict,
    company_id: str,
    subject_template: str,
    body_template: str,
    recipients: list[dict],
    attachment_paths: list[Path] | None = None,
    progress_cb: ProgressCb = None,
) -> dict:
    if not recipients:
        raise ValueError("Keine Empfänger vorhanden.")

    recipients = validate_mass_message_recipients(recipients, check_dns=False)
    invalid = [row for row in recipients if not row.get("EmailValidationSendable")]
    if invalid:
        labels = sorted({str(row.get("EmailValidationLabel") or "Ungültige E-Mail") for row in invalid})
        raise ValueError(
            f"Massennachricht wurde nicht gestartet: {len(invalid)} ungültige oder doppelte E-Mail-Adresse(n) "
            f"({', '.join(labels)}). Bitte Excel-Datei korrigieren und Vorschau neu laden."
        )

    mail_mode = str(settings.get("mail_mode", "smtp") or "smtp").strip().lower()
    smtp_settings = settings.get("smtp", {})
    from_email = str(smtp_settings.get("from_email", "") or "").strip()
    attachments = [Path(path) for path in (attachment_paths or [])]
    for attachment_path in attachments:
        if not attachment_path.is_file():
            raise ValueError(f"Der ausgewählte Anhang ist nicht mehr verfügbar: {attachment_path.name}")

    if mail_mode == "smtp":
        from .mailer import send_email, send_email_with_attachments, test_smtp_connection

        _emit_progress(progress_cb, "SMTP-Verbindung wird geprüft...")
        test_smtp_connection(smtp_settings)
        if attachments:
            send_message = lambda to_email, subject, body: send_email_with_attachments(
                smtp_settings=smtp_settings,
                to_email=to_email,
                subject=subject,
                body=body,
                attachment_paths=attachments,
            )
        else:
            send_message = lambda to_email, subject, body: send_email(
                smtp_settings=smtp_settings,
                to_email=to_email,
                subject=subject,
                body=body,
            )
    elif mail_mode == "outlook":
        from .mailer import send_outlook_email, send_outlook_email_with_attachments, test_outlook_connection

        _emit_progress(progress_cb, "Outlook-Verbindung wird geprüft...")
        test_outlook_connection(from_email)
        if attachments:
            send_message = lambda to_email, subject, body: send_outlook_email_with_attachments(
                to_email=to_email,
                subject=subject,
                body=body,
                attachment_paths=attachments,
                from_email=from_email,
            )
        else:
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
            from .mailer import user_facing_mail_error

            message = user_facing_mail_error(exc)
            errors.append({"PersNr": persnr, "Email": email, "Error": message})
            _emit_progress(progress_cb, f"Fehler ({index}/{total_count}): {persnr} -> {email}: {message}")

    return {
        "mode": "mass_message",
        "sent_count": sent_count,
        "error_count": len(errors),
        "total_count": total_count,
        "errors": errors,
        "attachment_count": len(attachments),
        "company_name": get_company_name(settings, company_id),
    }

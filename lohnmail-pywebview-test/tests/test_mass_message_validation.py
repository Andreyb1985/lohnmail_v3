from __future__ import annotations

from unittest.mock import patch

import pytest

from core.jobs import run_mass_message_job, validate_mass_message_recipients


def test_mass_message_validation_detects_duplicate_and_invalid_addresses():
    rows = validate_mass_message_recipients(
        [
            {"PersNr": "1", "Email": "same@example.de"},
            {"PersNr": "2", "Email": "same@example.de"},
            {"PersNr": "3", "Email": "broken"},
            {"PersNr": "4", "Email": "valid@example.de"},
        ],
        check_dns=False,
    )
    assert [row["EmailValidationCode"] for row in rows] == [
        "duplicate",
        "duplicate",
        "invalid_format",
        "valid",
    ]


def test_mass_message_job_blocks_all_sending_when_recipient_is_invalid():
    settings = {
        "mail_mode": "smtp",
        "smtp": {
            "server": "smtp.example.de",
            "port": 587,
            "username": "sender@example.de",
            "from_email": "sender@example.de",
        },
    }
    recipients = [
        {"PersNr": "1", "Email": "valid@example.de"},
        {"PersNr": "2", "Email": "broken"},
    ]
    with patch("core.mailer.test_smtp_connection") as connection, patch(
        "core.mailer.send_email"
    ) as send:
        with pytest.raises(ValueError, match="Massennachricht wurde nicht gestartet"):
            run_mass_message_job(settings, "test", "Betreff", "Text", recipients)
    connection.assert_not_called()
    send.assert_not_called()


def test_mass_message_job_sends_selected_common_attachments(tmp_path):
    attachment_one = tmp_path / "Information.pdf"
    attachment_two = tmp_path / "Hinweise.txt"
    attachment_one.write_bytes(b"pdf")
    attachment_two.write_text("text", encoding="utf-8")
    settings = {
        "mail_mode": "smtp",
        "smtp": {
            "server": "smtp.example.de",
            "port": 587,
            "username": "sender@example.de",
            "from_email": "sender@example.de",
        },
    }
    recipients = [{"PersNr": "1", "Email": "valid@example.de"}]
    with patch("core.mailer.test_smtp_connection"), patch(
        "core.mailer.send_email_with_attachments"
    ) as send:
        result = run_mass_message_job(
            settings,
            "test",
            "Betreff",
            "Text",
            recipients,
            attachment_paths=[attachment_one, attachment_two],
        )

    assert result["sent_count"] == 1
    assert result["attachment_count"] == 2
    assert send.call_args.kwargs["attachment_paths"] == [attachment_one, attachment_two]

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
        "duplicate", "duplicate", "invalid_format", "valid"
    ]


def test_mass_message_job_blocks_all_sending_when_recipient_is_invalid():
    settings = {
        "mail_mode": "smtp",
        "smtp": {
            "server": "smtp.example.de", "port": 587,
            "username": "sender@example.de", "from_email": "sender@example.de",
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

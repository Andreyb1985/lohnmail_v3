from unittest.mock import patch

import pytest

from core.mailer import test_smtp_connection as check_smtp_connection
from core.mailer import validate_sender_email


def test_sender_email_requires_domain():
    with pytest.raises(ValueError, match="vollständige gültige Adresse"):
        validate_sender_email("lohnbuchhaltung")


def test_sender_email_accepts_complete_address():
    assert validate_sender_email(" payroll@example.de ") == "payroll@example.de"


def test_smtp_connection_rejects_sender_before_opening_network_connection():
    settings = {
        "server": "smtp.example.de",
        "port": 587,
        "security": "tls",
        "username": "payroll@example.de",
        "password": "secret",
        "from_email": "payroll",
    }
    with patch("core.mailer.smtplib.SMTP") as smtp:
        with pytest.raises(ValueError, match="vollständige gültige Adresse"):
            check_smtp_connection(settings)
    smtp.assert_not_called()

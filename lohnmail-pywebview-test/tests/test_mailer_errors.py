import smtplib
import socket
import ssl
from unittest.mock import patch

import pytest

from core.mailer import test_smtp_connection as check_smtp_connection
from core.mailer import user_facing_mail_error


def test_dns_error_is_explained_without_technical_details():
    message = user_facing_mail_error(socket.gaierror(11001, "getaddrinfo failed"))
    assert "SMTP-Server konnte nicht gefunden" in message
    assert "getaddrinfo" not in message
    assert "keine E-Mails gesendet" in message


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (smtplib.SMTPAuthenticationError(535, b"bad credentials"), "Benutzername und Passwort"),
        (TimeoutError(), "nicht rechtzeitig geantwortet"),
        (ConnectionRefusedError(), "Verbindung abgelehnt"),
        (ssl.SSLError("wrong version"), "TLS-/SSL-Einstellung"),
        (smtplib.SMTPSenderRefused(550, b"no", "from@example.de"), "Absenderadresse"),
        (smtplib.SMTPRecipientsRefused({"to@example.de": (550, b"no")}), "Empfängeradresse"),
        (PermissionError(13, "denied"), "Zugriffsrechte"),
    ],
)
def test_common_mail_errors_are_actionable(error, expected):
    message = user_facing_mail_error(error)
    assert expected in message
    assert "Errno" not in message


def test_connection_test_translates_dns_error():
    settings = {
        "server": "smtp.invalid",
        "port": 587,
        "security": "tls",
        "username": "payroll@example.de",
        "password": "secret",
        "from_email": "payroll@example.de",
    }
    with patch("core.mailer.smtplib.SMTP", side_effect=socket.gaierror(11001, "getaddrinfo failed")):
        with pytest.raises(RuntimeError, match="SMTP-Server konnte nicht gefunden") as raised:
            check_smtp_connection(settings)
    assert "getaddrinfo" not in str(raised.value)

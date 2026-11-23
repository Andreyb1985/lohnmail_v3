"""Local, actionable preparation/delivery errors (no change to telemetry schema)."""
import errno
import smtplib
import socket
import ssl


ERRORS = {
    "BIRTH_DATE_MISSING": (
        "Geburtsdatum fehlt oder ist ungültig",
        "Im PDF wurde kein Geburtsdatum erkannt. Auch in der Excel-Liste fehlt für diesen Mitarbeiter "
        "ein gültiges Geburtsdatum. Bitte in der Spalte „Geburtsdatum“ bei der passenden Personalnummer "
        "das Datum eintragen (z. B. 03.02.1990), die Excel-Datei speichern und die Vorbereitung erneut starten. "
        "Ohne gültiges Datum werden die Dokumente dieses Mitarbeiters nicht für den Versand vorbereitet "
        "und nicht gesendet. Die automatische Erkennung im PDF unterstützt DATEV-Lohnabrechnungen; "
        "für andere PDF-Formate hilft der Support."
    ),
    "BIRTH_DATE_MISMATCH": (
        "Geburtsdatum in PDF und Excel stimmt nicht überein",
        "Für diesen Mitarbeiter wurden unterschiedliche Geburtsdaten im PDF und in der Excel-Spalte "
        "„Geburtsdatum“ gefunden. Bitte die Personalnummer und beide Angaben prüfen, die falsche Angabe "
        "korrigieren und die Vorbereitung erneut starten. Die Dokumente dieses Mitarbeiters werden "
        "bis dahin nicht für den Versand vorbereitet und nicht gesendet."
    ),
    "BIRTH_DATE_CONFLICT": ("Widersprüchliche Geburtsdaten", "Die zugeordneten PDF-Seiten enthalten unterschiedliche Geburtsdaten. Dokumente und Personalnummer prüfen und erneut vorbereiten. Es wird kein Passwort geraten."),
    "PDF_LOCKED": ("Eingabe-PDF ist passwortgeschützt", "Eine unverschlüsselte Originaldatei auswählen und die Prüfung erneut starten."),
    "PDF_EMPTY": ("PDF enthält keine Seiten", "Eine vollständige PDF-Datei aus dem Abrechnungsprogramm exportieren und erneut prüfen."),
    "PDF_UNREADABLE": ("PDF nicht lesbar", "Die Originaldatei öffnen und prüfen; gegebenenfalls erneut als PDF exportieren. Danach die Prüfung erneut starten."),
    "PDF_MERGE": ("PDF-Zusammenführung fehlgeschlagen", "Die Originaldateien dieses Mitarbeiters prüfen und erneut vorbereiten. Bei erneutem Fehler einen Diagnosebericht an den Support senden."),
    "PDF_ENCRYPTION": ("PDF-Verschlüsselung fehlgeschlagen", "Die PDF-Datei wurde nicht zum Versand freigegeben. Erneut vorbereiten; bei erneutem Fehler einen Diagnosebericht an den Support senden."),
    "FILE_MISSING": ("Datei nicht gefunden", "PDF-/Excel-Pfad und angeschlossenes Laufwerk prüfen. Dateien erneut auswählen und die Prüfung wiederholen."),
    "FILE_ACCESS": ("Zugriff auf Datei verweigert", "Geöffnete Dateien schließen und Lese-/Schreibrechte für Eingabe und Ausgabe prüfen. Danach erneut vorbereiten."),
    "DISK_FULL": ("Nicht genügend Speicherplatz", "Speicherplatz auf dem Ausgabelaufwerk freigeben oder einen anderen Ausgabeordner wählen. Danach erneut vorbereiten."),
    "FILE_IO": ("Datei konnte nicht gelesen oder gespeichert werden", "Eingabe- und Ausgabelaufwerk sowie Schreibrechte prüfen. Danach erneut vorbereiten."),
    "EMAIL_INVALID": ("E-Mail-Adresse fehlt oder ist nicht versandbereit", "E-Mail-Adresse und mögliche doppelte Zuordnungen in Excel prüfen. Danach die Prüfung erneut starten."),
    "PDF_MISSING": ("Kein PDF zugeordnet", "PDF-Dateien, Personalnummer in Excel und das Dateiformat unter Einstellungen → PDF-Dateien prüfen. Danach erneut prüfen."),
    "SMTP_AUTH": ("SMTP-Anmeldung fehlgeschlagen", "Benutzername und Passwort unter Einstellungen → E-Mail prüfen und die Verbindung testen."),
    "SMTP_DNS": ("SMTP-Server nicht gefunden", "Serveradresse und Internetverbindung unter Einstellungen → E-Mail prüfen und die Verbindung testen."),
    "SMTP_TIMEOUT": ("Zeitüberschreitung beim Mailserver", "Verbindung und Serververfügbarkeit prüfen. Bei einem Abbruch während der Übertragung zuerst den Versandstatus beim Mailanbieter prüfen, um doppelte E-Mails zu vermeiden."),
    "SMTP_TLS": ("Sichere SMTP-Verbindung fehlgeschlagen", "Serveradresse, Port, TLS/SSL und Computerzeit prüfen. Die Zertifikatsprüfung nicht ausschalten."),
    "SMTP_RECIPIENT": ("Empfänger vom Mailserver abgelehnt", "E-Mail-Adresse in Excel prüfen und anschließend die Prüfung erneut starten."),
    "SMTP_SENDER": ("Absender vom Mailserver abgelehnt", "Absenderadresse und Versandberechtigung unter Einstellungen → E-Mail prüfen."),
    "SMTP_DATA": ("Nachricht vom Mailserver abgelehnt", "Anhangsgröße und Versandlimits beim Mailanbieter prüfen. Bei Bedarf den Administrator kontaktieren."),
    "MAIL_CONNECTION": ("Verbindung zum Mailserver unterbrochen", "Verbindung testen. Bei einem Abbruch während der Übertragung zuerst den Versandstatus beim Mailanbieter prüfen, bevor erneut gesendet wird."),
    "MAIL_FAILED": ("E-Mail konnte nicht gesendet werden", "E-Mail-Einstellungen bzw. Outlook prüfen und die Verbindung testen. Bei erneutem Fehler einen Diagnosebericht an den Support senden."),
    "PREPARATION_FAILED": ("PDF-Vorbereitung fehlgeschlagen", "Originaldateien und Ausgabeordner prüfen. Bei erneutem Fehler einen Diagnosebericht an den Support senden."),
}


class ShippingError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(ERRORS[code][0])


def issue_fields(code):
    title, action = ERRORS[code]
    return {"ErrorCode": code, "ErrorTitle": title, "ErrorAction": action,
            "Error": f"{title}. {action}"}


def describe_shipping_error(exc, stage="prepare"):
    # Preserve explicit domain errors, but unwrap transport and filesystem wrappers.
    chain = []
    current = exc
    while current is not None and id(current) not in {id(item) for item in chain}:
        chain.append(current)
        current = current.__cause__
    for item in chain:
        if isinstance(item, ShippingError):
            return issue_fields(item.code)
    for item in reversed(chain):
        for kind, code in (
            (smtplib.SMTPAuthenticationError, "SMTP_AUTH"),
            (socket.gaierror, "SMTP_DNS"), (TimeoutError, "SMTP_TIMEOUT"),
            (ssl.SSLError, "SMTP_TLS"),
            (smtplib.SMTPRecipientsRefused, "SMTP_RECIPIENT"),
            (smtplib.SMTPSenderRefused, "SMTP_SENDER"),
            (smtplib.SMTPDataError, "SMTP_DATA"),
            (smtplib.SMTPServerDisconnected, "MAIL_CONNECTION"),
            (ConnectionError, "MAIL_CONNECTION"),
            (FileNotFoundError, "FILE_MISSING"), (PermissionError, "FILE_ACCESS"),
        ):
            if isinstance(item, kind):
                return issue_fields(code)
        if isinstance(item, OSError) and item.errno == errno.ENOSPC:
            return issue_fields("DISK_FULL")
    if any(isinstance(item, OSError) for item in chain):
        return issue_fields("MAIL_FAILED" if stage == "send" else "FILE_IO")
    return issue_fields({"read": "PDF_UNREADABLE", "merge": "PDF_MERGE",
                         "encrypt": "PDF_ENCRYPTION", "send": "MAIL_FAILED"}.get(stage, "PREPARATION_FAILED"))

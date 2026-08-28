# core/mailer.py
import smtplib
import ssl
import subprocess
import sys
from email.message import EmailMessage
from pathlib import Path


def _build_from_header(from_email: str, from_name: str) -> str:
    if from_name and from_email:
        return f'{from_name} <{from_email}>'
    return from_email or from_name


def test_smtp_connection(smtp_settings: dict) -> None:
    host = smtp_settings.get("server", "").strip()
    port = int(smtp_settings.get("port", 0) or 0)
    username = smtp_settings.get("username", "").strip()
    password = smtp_settings.get("password", "")
    security = smtp_settings.get("security", "tls").strip().lower()
    timeout = int(smtp_settings.get("timeout_sec", 30) or 30)

    if not host or not port:
        raise ValueError("SMTP Server und Port müssen ausgefüllt werden.")

    if security == "ssl":
        with smtplib.SMTP_SSL(host, port, timeout=timeout, context=ssl.create_default_context()) as server:
            if username:
                server.login(username, password)
    else:
        with smtplib.SMTP(host, port, timeout=timeout) as server:
            if security == "tls":
                server.starttls(context=ssl.create_default_context())
            if username:
                server.login(username, password)


def _run_osascript(script: str, args: list[str]) -> None:
    try:
        subprocess.run(
            ["osascript", "-", *args],
            input=script,
            text=True,
            capture_output=True,
            check=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("osascript ist auf diesem System nicht verfügbar.") from exc
    except subprocess.CalledProcessError as exc:
        details = (exc.stderr or exc.stdout or "").strip()
        if details:
            raise RuntimeError(
                f"Outlook-AppleScript fehlgeschlagen: {details}. "
                "Unter macOS ist eine Outlook-Version mit AppleScript-Unterstützung erforderlich."
            ) from exc
        raise RuntimeError(
            "Outlook-AppleScript fehlgeschlagen. Unter macOS ist eine Outlook-Version "
            "mit AppleScript-Unterstützung erforderlich."
        ) from exc


def _ensure_outlook_supported() -> None:
    if sys.platform not in {"darwin", "win32"}:
        raise RuntimeError(
            "Outlook-Classic-Versand wird derzeit nur unter macOS oder Windows unterstützt."
        )


def _with_windows_com(action) -> None:
    try:
        import pythoncom
    except ImportError as exc:
        raise RuntimeError(
            "Für Outlook Classic unter Windows wird das Paket 'pywin32' benötigt."
        ) from exc

    pythoncom.CoInitialize()
    try:
        action()
    finally:
        pythoncom.CoUninitialize()


def _get_windows_outlook_app():
    try:
        import win32com.client
    except ImportError as exc:
        raise RuntimeError(
            "Für Outlook Classic unter Windows wird das Paket 'pywin32' benötigt."
        ) from exc

    try:
        return win32com.client.DispatchEx("Outlook.Application")
    except Exception as exc:
        raise RuntimeError(
            "Microsoft Outlook Classic konnte unter Windows nicht gestartet werden. "
            "Das neue Outlook für Windows wird nicht unterstützt. Öffnen Sie Outlook Classic "
            "und prüfen Sie das aktive Profil."
        ) from exc


def _get_windows_mapi_namespace(outlook):
    try:
        namespace = outlook.GetNamespace("MAPI")
    except Exception as exc:
        raise RuntimeError("Outlook-Classic-MAPI konnte nicht initialisiert werden.") from exc

    try:
        namespace.Logon("", "", False, False)
    except Exception:
        pass

    return namespace


def _normalize_outlook_value(value: object) -> str:
    return str(value or "").strip()


_OUTLOOK_SEND_USING_ACCOUNT_DISPID = 64209


def _friendly_windows_outlook_error(exc: Exception) -> RuntimeError:
    raw = str(exc or "")
    normalized = raw.lower()
    if "-2147221231" in raw or "server steht nicht zur verfügung" in normalized:
        return RuntimeError(
            "Outlook Classic ist geöffnet, aber das aktive MAPI-Profil kann nicht auf das Postfach zugreifen. "
            "Öffnen Sie Outlook Classic, warten Sie bis unten 'Verbunden' angezeigt wird und prüfen Sie, ob "
            "das Postfach ohne Anmeldefehler geöffnet werden kann. Falls nur das neue Outlook installiert ist, "
            "wechseln Sie zu Outlook Classic. In einer Firmenumgebung muss MAPI für das Postfach aktiviert sein."
        )
    return RuntimeError(
        "Outlook-Classic-Konten konnten nicht gelesen werden. Öffnen Sie Outlook Classic, wählen Sie das "
        "richtige Profil und warten Sie, bis die Synchronisierung abgeschlossen ist."
    )


def _describe_windows_outlook_account(account) -> dict[str, str]:
    smtp_address = _normalize_outlook_value(getattr(account, "SmtpAddress", ""))
    display_name = _normalize_outlook_value(getattr(account, "DisplayName", ""))
    identifier = smtp_address or display_name

    if smtp_address and display_name and display_name.lower() != smtp_address.lower():
        label = f"{display_name} <{smtp_address}>"
    else:
        label = identifier

    return {
        "identifier": identifier,
        "smtp_address": smtp_address,
        "display_name": display_name,
        "label": label,
    }


def list_outlook_accounts() -> list[dict[str, str]]:
    _ensure_outlook_supported()
    if sys.platform != "win32":
        return []

    accounts: list[dict[str, str]] = []

    def _collect() -> None:
        outlook = _get_windows_outlook_app()
        namespace = _get_windows_mapi_namespace(outlook)
        seen: set[str] = set()

        try:
            account_collection = namespace.Accounts
        except Exception as exc:
            raise _friendly_windows_outlook_error(exc) from exc

        for account in account_collection:
            try:
                details = _describe_windows_outlook_account(account)
            except Exception:
                continue
            identifier = details["identifier"].lower()
            if not identifier or identifier in seen:
                continue
            seen.add(identifier)
            accounts.append(details)

    try:
        _with_windows_com(_collect)
    except RuntimeError:
        raise
    except Exception as exc:
        raise _friendly_windows_outlook_error(exc) from exc
    return accounts


def _find_windows_outlook_account(namespace, from_email: str):
    target = (from_email or "").strip().lower()
    if not target:
        return None

    for account in namespace.Accounts:
        details = _describe_windows_outlook_account(account)
        candidates = {
            details["identifier"].lower(),
            details["smtp_address"].lower(),
            details["display_name"].lower(),
        }
        candidates.discard("")
        if target in candidates:
            return account

    raise RuntimeError(
        f"Das Outlook-Classic-Absenderkonto '{from_email}' wurde im aktiven Profil nicht gefunden."
    )


def _assign_windows_outlook_account(message, account, from_email: str) -> None:
    if account is None:
        return

    expected = _describe_windows_outlook_account(account)
    expected_addresses = {
        expected["identifier"].lower(),
        expected["smtp_address"].lower(),
    }
    expected_addresses.discard("")

    def _selected_account_matches() -> bool:
        try:
            selected = _describe_windows_outlook_account(message.SendUsingAccount)
        except Exception:
            return False
        selected_addresses = {
            selected["identifier"].lower(),
            selected["smtp_address"].lower(),
        }
        selected_addresses.discard("")
        return bool(expected_addresses & selected_addresses)

    try:
        message.SendUsingAccount = account
        if _selected_account_matches():
            return
    except Exception:
        pass

    try:
        # Outlook's late-bound COM wrapper can reject the normal property setter.
        # DISPID 64209 is MailItem.SendUsingAccount; PROPERTYPUT must receive the
        # actual Account COM object. This selects the sending account itself and
        # is deliberately not replaced by SentOnBehalfOfName.
        message._oleobj_.Invoke(
            _OUTLOOK_SEND_USING_ACCOUNT_DISPID,
            0,
            8,  # DISPATCH_PROPERTYPUT
            0,
            account,
        )
        if _selected_account_matches():
            return
    except Exception:
        pass

    raise RuntimeError(
        f"Outlook Classic konnte das gewählte Absenderkonto '{from_email}' nicht sicher auswählen. "
        "Die Nachricht wurde nicht gesendet, damit sie nicht über ein anderes Konto oder "
        "'im Auftrag von' versendet wird."
    )


def test_outlook_connection(from_email: str = "") -> None:
    _ensure_outlook_supported()
    if sys.platform == "win32":
        def _test() -> None:
            outlook = _get_windows_outlook_app()
            namespace = _get_windows_mapi_namespace(outlook)
            _find_windows_outlook_account(namespace, from_email)

        try:
            _with_windows_com(_test)
        except RuntimeError:
            raise
        except Exception as exc:
            raise _friendly_windows_outlook_error(exc) from exc
        return

    script = """
on run argv
    tell application "Microsoft Outlook"
        get version
    end tell
end run
"""
    _run_osascript(script, [])


def send_email(
    smtp_settings: dict,
    to_email: str,
    subject: str,
    body: str,
    html_body: str = "",
) -> None:
    from_email = (smtp_settings.get("from_email") or smtp_settings.get("username") or "").strip()
    from_name = (smtp_settings.get("from_name") or "").strip()

    if not from_email:
        raise ValueError("Absender-E-Mail fehlt in den SMTP-Einstellungen.")

    msg = EmailMessage()
    msg["From"] = _build_from_header(from_email, from_name)
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)
    if html_body:
        msg.add_alternative(html_body, subtype="html")

    host = smtp_settings.get("server", "").strip()
    port = int(smtp_settings.get("port", 0) or 0)
    username = smtp_settings.get("username", "").strip()
    password = smtp_settings.get("password", "")
    security = smtp_settings.get("security", "tls").strip().lower()
    timeout = int(smtp_settings.get("timeout_sec", 30) or 30)

    if not host or not port:
        raise ValueError("SMTP Server und Port mÃ¼ssen ausgefÃ¼llt werden.")

    if security == "ssl":
        with smtplib.SMTP_SSL(host, port, timeout=timeout, context=ssl.create_default_context()) as server:
            if username:
                server.login(username, password)
            server.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=timeout) as server:
            if security == "tls":
                server.starttls(context=ssl.create_default_context())
            if username:
                server.login(username, password)
            server.send_message(msg)


def send_email_with_attachment(
    smtp_settings: dict,
    to_email: str,
    subject: str,
    body: str,
    attachment_path: Path,
    html_body: str = "",
) -> None:
    if not attachment_path.exists():
        raise FileNotFoundError(f"Anhang nicht gefunden: {attachment_path}")

    from_email = (smtp_settings.get("from_email") or smtp_settings.get("username") or "").strip()
    from_name = (smtp_settings.get("from_name") or "").strip()

    if not from_email:
        raise ValueError("Absender-E-Mail fehlt in den SMTP-Einstellungen.")

    msg = EmailMessage()
    msg["From"] = _build_from_header(from_email, from_name)
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)
    if html_body:
        msg.add_alternative(html_body, subtype="html")

    data = attachment_path.read_bytes()
    msg.add_attachment(
        data,
        maintype="application",
        subtype="pdf",
        filename=attachment_path.name,
    )

    host = smtp_settings.get("server", "").strip()
    port = int(smtp_settings.get("port", 0) or 0)
    username = smtp_settings.get("username", "").strip()
    password = smtp_settings.get("password", "")
    security = smtp_settings.get("security", "tls").strip().lower()
    timeout = int(smtp_settings.get("timeout_sec", 30) or 30)

    if not host or not port:
        raise ValueError("SMTP Server und Port müssen ausgefüllt werden.")

    if security == "ssl":
        with smtplib.SMTP_SSL(host, port, timeout=timeout, context=ssl.create_default_context()) as server:
            if username:
                server.login(username, password)
            server.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=timeout) as server:
            if security == "tls":
                server.starttls(context=ssl.create_default_context())
            if username:
                server.login(username, password)
            server.send_message(msg)


def send_outlook_email(
    to_email: str,
    subject: str,
    body: str,
    from_email: str = "",
    html_body: str = "",
) -> None:
    _ensure_outlook_supported()

    if sys.platform == "win32":
        def _send() -> None:
            outlook = _get_windows_outlook_app()
            namespace = _get_windows_mapi_namespace(outlook)
            message = outlook.CreateItem(0)
            account = _find_windows_outlook_account(namespace, from_email)
            message.To = to_email
            message.Subject = subject
            if html_body:
                message.HTMLBody = html_body
            else:
                message.Body = body
            _assign_windows_outlook_account(message, account, from_email)
            try:
                message.Send()
            except Exception as exc:
                raise RuntimeError(
                    "Outlook Classic konnte die Nachricht nicht senden. "
                    "Prüfen Sie, ob Outlook Classic geöffnet ist, ein Profil geladen ist "
                    "und das Absenderkonto im aktiven Profil vorhanden ist."
                ) from exc

        _with_windows_com(_send)
        return

    script = """
on run argv
    set toEmail to item 1 of argv
    set subjectText to item 2 of argv
    set bodyText to item 3 of argv

    tell application "Microsoft Outlook"
        set newMessage to make new outgoing message with properties {subject:subjectText, content:bodyText & return & return}
        tell newMessage
            make new recipient with properties {email address:{address:toEmail}}
            send
        end tell
    end tell
end run
"""
    _run_osascript(script, [to_email, subject, body])


def send_outlook_email_with_attachment(
    to_email: str,
    subject: str,
    body: str,
    attachment_path: Path,
    from_email: str = "",
    html_body: str = "",
) -> None:
    _ensure_outlook_supported()

    if not attachment_path.exists():
        raise FileNotFoundError(f"Anhang nicht gefunden: {attachment_path}")

    if sys.platform == "win32":
        def _send() -> None:
            outlook = _get_windows_outlook_app()
            namespace = _get_windows_mapi_namespace(outlook)
            message = outlook.CreateItem(0)
            account = _find_windows_outlook_account(namespace, from_email)
            message.To = to_email
            message.Subject = subject
            if html_body:
                message.HTMLBody = html_body
            else:
                message.Body = body
            _assign_windows_outlook_account(message, account, from_email)
            message.Attachments.Add(str(attachment_path))
            try:
                message.Send()
            except Exception as exc:
                raise RuntimeError(
                    "Outlook Classic konnte die Nachricht nicht senden. "
                    "Prüfen Sie, ob Outlook Classic geöffnet ist, ein Profil geladen ist "
                    "und das Absenderkonto im aktiven Profil vorhanden ist."
                ) from exc

        _with_windows_com(_send)
        return

    script = """
on run argv
    set toEmail to item 1 of argv
    set subjectText to item 2 of argv
    set bodyText to item 3 of argv
    set attachmentPath to item 4 of argv

    tell application "Microsoft Outlook"
        set newMessage to make new outgoing message with properties {subject:subjectText, content:bodyText & return & return}
        tell newMessage
            make new recipient with properties {email address:{address:toEmail}}
            make new attachment with properties {file:(POSIX file attachmentPath as alias)}
            send
        end tell
    end tell
end run
"""
    _run_osascript(script, [to_email, subject, body, str(attachment_path)])

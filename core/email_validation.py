from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import re
from typing import Callable


LOCAL_RE = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+$")
DOMAIN_LABEL_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")

DomainChecker = Callable[[str], tuple[str, str]]


def _result(
    *,
    code: str,
    label: str,
    email: str,
    checked_at: str,
    hint: str,
    sendable: bool,
    domain: str = "",
    mx_status: str = "-",
    row: int | str = "",
) -> dict:
    return {
        "code": code,
        "label": label,
        "email": email,
        "domain": domain,
        "mx_status": mx_status,
        "checked_at": checked_at,
        "hint": hint,
        "sendable": sendable,
        "row": row,
    }


def _local_validation(email: str) -> tuple[str, str, str] | None:
    if not email:
        return "missing", "Fehlt", "Keine E-Mail-Adresse eingetragen."

    if any(ord(char) < 33 or ord(char) > 126 for char in email):
        return "illegal_characters", "Ungültige Zeichen", "Die Adresse enthält Leerzeichen oder nicht erlaubte Zeichen."

    if email.count("@") != 1:
        return "invalid_format", "Ungültiges Format", "Die Adresse muss genau ein @-Zeichen enthalten."

    local, domain = email.rsplit("@", 1)
    if (
        not local
        or len(local) > 64
        or not LOCAL_RE.fullmatch(local)
        or local.startswith(".")
        or local.endswith(".")
        or ".." in local
    ):
        return "invalid_format", "Ungültiges Format", "Der Teil vor dem @-Zeichen ist ungültig."

    labels = domain.split(".")
    if (
        not domain
        or len(domain) > 253
        or len(labels) < 2
        or any(not DOMAIN_LABEL_RE.fullmatch(label) for label in labels)
    ):
        return "invalid_format", "Ungültiges Format", "Die Domain der E-Mail-Adresse ist ungültig."

    return None


def _dns_check(domain: str) -> tuple[str, str]:
    try:
        import dns.exception
        import dns.resolver
    except ModuleNotFoundError:
        return "dns_unavailable", "DNS-Prüfung nicht verfügbar (dnspython fehlt)."

    resolver = dns.resolver.Resolver()
    resolver.timeout = 1.5
    resolver.lifetime = 2.5
    try:
        answers = resolver.resolve(domain, "MX")
        if any(str(answer.exchange).strip(".") for answer in answers):
            return "valid", "MX-Eintrag gefunden."
        return "mx_missing", "Für diese Domain wurde kein MX-Eintrag gefunden."
    except dns.resolver.NXDOMAIN:
        return "domain_missing", "Die Domain existiert nicht."
    except dns.resolver.NoAnswer:
        return "mx_missing", "Für diese Domain wurde kein MX-Eintrag gefunden."
    except (dns.resolver.NoNameservers, dns.exception.Timeout, OSError) as exc:
        return "dns_unavailable", f"DNS-Prüfung derzeit nicht möglich: {exc}"
    except Exception as exc:
        return "dns_unavailable", f"DNS-Prüfung derzeit nicht möglich: {exc}"


def validate_email_records(
    records: dict[str, dict[str, str]],
    *,
    check_dns: bool = True,
    domain_checker: DomainChecker | None = None,
    checked_at: str | None = None,
) -> dict[str, dict]:
    """Validate addresses without making a temporary DNS outage block sending."""

    timestamp = checked_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    normalized = {
        persnr: str(record.get("Email", "") or "").strip()
        for persnr, record in records.items()
    }
    duplicate_counts = Counter(email.casefold() for email in normalized.values() if email)
    results: dict[str, dict] = {}
    domains: set[str] = set()

    for persnr, record in records.items():
        email = normalized[persnr]
        row = record.get("ExcelRow", "")
        local_error = _local_validation(email)
        if local_error:
            code, label, hint = local_error
            results[persnr] = _result(
                code=code,
                label=label,
                email=email,
                checked_at=timestamp,
                hint=hint,
                sendable=False,
                row=row,
            )
            continue

        domain = email.rsplit("@", 1)[1].casefold()
        if duplicate_counts[email.casefold()] > 1:
            results[persnr] = _result(
                code="duplicate",
                label="Doppelte Adresse",
                email=email,
                domain=domain,
                checked_at=timestamp,
                hint="Diese Adresse ist mehreren Mitarbeitern zugeordnet.",
                sendable=False,
                row=row,
            )
            continue

        results[persnr] = _result(
            code="pending_dns" if check_dns else "valid",
            label="DNS-Prüfung läuft" if check_dns else "Gültig",
            email=email,
            domain=domain,
            checked_at=timestamp,
            hint="Format der Adresse ist gültig.",
            sendable=True,
            mx_status="Nicht geprüft" if not check_dns else "Prüfung läuft",
            row=row,
        )
        if check_dns:
            domains.add(domain)

    if not domains:
        return results

    checker = domain_checker or _dns_check
    domain_results: dict[str, tuple[str, str]] = {}
    with ThreadPoolExecutor(max_workers=min(8, len(domains))) as executor:
        futures = {executor.submit(checker, domain): domain for domain in domains}
        for future in as_completed(futures):
            domain = futures[future]
            try:
                domain_results[domain] = future.result()
            except Exception as exc:
                domain_results[domain] = ("dns_unavailable", f"DNS-Prüfung derzeit nicht möglich: {exc}")

    for result in results.values():
        if result["code"] != "pending_dns":
            continue
        code, hint = domain_results.get(
            result["domain"],
            ("dns_unavailable", "DNS-Prüfung derzeit nicht möglich."),
        )
        if code == "valid":
            result.update(code="valid", label="Gültig", mx_status="Vorhanden", hint=hint, sendable=True)
        elif code == "domain_missing":
            result.update(code=code, label="Domain nicht gefunden", mx_status="Fehlt", hint=hint, sendable=False)
        elif code == "mx_missing":
            result.update(code=code, label="Keine MX-Einträge", mx_status="Fehlt", hint=hint, sendable=False)
        else:
            result.update(
                code="dns_unavailable",
                label="DNS nicht geprüft",
                mx_status="Nicht geprüft",
                hint=hint,
                sendable=True,
            )

    return results

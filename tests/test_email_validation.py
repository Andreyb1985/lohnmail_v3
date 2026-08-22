from core.email_validation import validate_email_records


CHECKED_AT = "2026-08-18T14:00:00+00:00"


def _records(*emails: str) -> dict[str, dict[str, str]]:
    return {
        str(index): {
            "Email": email,
            "ExcelRow": str(index + 1),
        }
        for index, email in enumerate(emails, start=1)
    }


def test_local_validation_detects_missing_format_characters_and_duplicates():
    records = _records(
        "",
        "ohne-at-zeichen.example",
        "name mit leerzeichen@example.com",
        "Doppelt@example.com",
        "doppelt@example.com",
    )

    results = validate_email_records(records, check_dns=False, checked_at=CHECKED_AT)

    assert results["1"]["code"] == "missing"
    assert results["2"]["code"] == "invalid_format"
    assert results["3"]["code"] == "illegal_characters"
    assert results["4"]["code"] == "duplicate"
    assert results["5"]["code"] == "duplicate"
    assert all(result["sendable"] is False for result in results.values())
    assert all(result["checked_at"] == CHECKED_AT for result in results.values())


def test_dns_validation_distinguishes_valid_domain_missing_and_missing_mx():
    domain_results = {
        "valid.example": ("valid", "MX-Eintrag gefunden."),
        "missing.example": ("domain_missing", "Die Domain existiert nicht."),
        "nomx.example": ("mx_missing", "Kein MX-Eintrag."),
    }

    results = validate_email_records(
        _records(
            "ok@valid.example",
            "domain@missing.example",
            "mx@nomx.example",
        ),
        domain_checker=lambda domain: domain_results[domain],
        checked_at=CHECKED_AT,
    )

    assert results["1"]["code"] == "valid"
    assert results["1"]["mx_status"] == "Vorhanden"
    assert results["1"]["sendable"] is True
    assert results["2"]["code"] == "domain_missing"
    assert results["2"]["sendable"] is False
    assert results["3"]["code"] == "mx_missing"
    assert results["3"]["sendable"] is False


def test_temporary_dns_failure_is_visible_but_does_not_block_sending():
    results = validate_email_records(
        _records("mitarbeiter@example.com"),
        domain_checker=lambda _domain: ("dns_unavailable", "Zeitüberschreitung"),
        checked_at=CHECKED_AT,
    )

    result = results["1"]
    assert result["code"] == "dns_unavailable"
    assert result["label"] == "DNS nicht geprüft"
    assert result["mx_status"] == "Nicht geprüft"
    assert result["sendable"] is True

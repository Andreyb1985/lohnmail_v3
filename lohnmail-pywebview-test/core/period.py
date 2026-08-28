# core/period.py
from datetime import date

GERMAN_MONTHS = {
    1: "Januar",
    2: "Februar",
    3: "März",
    4: "April",
    5: "Mai",
    6: "Juni",
    7: "Juli",
    8: "August",
    9: "September",
    10: "Oktober",
    11: "November",
    12: "Dezember",
}


def previous_month(today: date | None = None) -> tuple[int, int]:
    if today is None:
        today = date.today()

    month = today.month - 1
    year = today.year

    if month == 0:
        month = 12
        year -= 1

    return month, year


def current_month(today: date | None = None) -> tuple[int, int]:
    if today is None:
        today = date.today()
    return today.month, today.year


def format_month(month: int) -> str:
    return GERMAN_MONTHS.get(month, "")


def _safe_int(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def get_payroll_period(settings: dict | None = None) -> dict:
    """
    Bestimmt den Abrechnungsmonat.

    Rückgabe:
    {
        "monat": "März",
        "jahr": 2026,
        "monat_num": 3,
        "monat_jahr": "März 2026"
    }
    """
    today = date.today()

    if settings is None:
        month, year = current_month(today)
    else:
        period = settings.get("period", {})
        mode = period.get("mode", "automatic_current_month")

        if mode == "manual":
            month = _safe_int(period.get("month", today.month), today.month)
            year = _safe_int(period.get("year", today.year), today.year)

            if month < 1 or month > 12:
                month, year = current_month(today)
        elif mode == "automatic_previous_month":
            month, year = previous_month(today)
        else:
            month, year = current_month(today)

    monat_name = format_month(month)

    return {
        "monat": monat_name,
        "jahr": year,
        "monat_num": month,
        "monat_jahr": f"{monat_name} {year}",
    }

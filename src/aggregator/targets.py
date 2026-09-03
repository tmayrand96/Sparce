"""Target-assignment business rules for workforce reports."""

from __future__ import annotations

import re
from datetime import date, datetime

from src.config.target_matrix import TARGET_MATRIX


_FRENCH_MONTHS = {
    "janvier": 1, "janv": 1, "fevrier": 2, "fevr": 2, "mars": 3, "avril": 4,
    "avr": 4, "mai": 5, "juin": 6, "juillet": 7, "juil": 7, "aout": 8,
    "septembre": 9, "sept": 9, "octobre": 10, "oct": 10, "novembre": 11,
    "nov": 11, "decembre": 12, "dec": 12,
}


def _normalized(value: str) -> str:
    return (
        value.casefold()
        .replace("é", "e")
        .replace("è", "e")
        .replace("ê", "e")
        .replace("û", "u")
        .replace("ô", "o")
        .replace("à", "a")
    )


def _is_weekend(report_date: str | None) -> bool:
    if not report_date:
        return False
    normalized_date = _normalized(report_date)
    if re.search(r"\b(?:samedi|dimanche)\b", normalized_date):
        return True
    match = re.search(r"\b(\d{1,2})\s+(\w+)\.?\s+(\d{4})\b", normalized_date)
    if not match:
        return False
    day, month_name, year = match.groups()
    month = _FRENCH_MONTHS.get(month_name.rstrip("."))
    if not month:
        return False
    try:
        return date(int(year), month, int(day)).weekday() >= 5
    except ValueError:
        return False


def target_for(category: str, department: str, shift: str, report_date: str | None = None) -> int:
    """Return the target after date-dependent business rules are applied."""
    if department == "CDJ" and _is_weekend(report_date):
        return 0
    categories = ("Inf", "Aux", "PAB", "AA")
    return TARGET_MATRIX[department][shift][categories.index(category)]
"""Append structured execution diagnostics to the AI execution journal."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo


DEFAULT_JOURNAL_PATH = Path(__file__).resolve().parents[2] / "docs" / "task_journal.md"


def _format_timestamp(timestamp: datetime | None = None) -> str:
    """Format timestamps in the report's local Eastern timezone."""
    eastern = ZoneInfo("America/Toronto")
    value = (timestamp or datetime.now(eastern)).astimezone(eastern)
    return value.strftime("%Y-%m-%d %H:%M:%S %Z")


def _code_tallies(records: Iterable[dict[str, Any]]) -> dict[str, int]:
    return dict(Counter(code for record in records for code in record.get("Codes", []) or []))


def _discrepancies(records: Iterable[dict[str, Any]]) -> list[str]:
    return [
        f"{record.get('Date', 'Date inconnue')} | {record.get('Département', 'Inconnu')} | "
        f"{record.get('Catégorie', 'Inconnue')}: Cible={record.get('Cible', 0)}, "
        f"Présences={record.get('Présences', 0)}"
        for record in records
        if record.get("Cible", 0) != record.get("Présences", 0)
    ]


def log_execution_entry(
    source_file: str,
    anonymized: bool,
    report_date: str,
    shift: str,
    records: list[dict[str, Any]],
    warnings: list[str] | None = None,
    journal_path: str | Path | None = None,
    timestamp: datetime | None = None,
) -> str:
    """Append one execution entry and return the complete journal contents."""
    path = Path(journal_path) if journal_path else DEFAULT_JOURNAL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    warning_details = list(warnings or [])
    discrepancy_details = _discrepancies(records)
    details = discrepancy_details + warning_details
    status = "PASS" if not details else "WARNING"
    departments = list(dict.fromkeys(record.get("Département", "Inconnu") for record in records))
    entry = f"""## 📝 Execution Journal Entry — {_format_timestamp(timestamp)}

- **Source File:** `{Path(source_file).name}`
- **Report Context:** Date: `{report_date}` | Shift: `{shift}`
- **Anonymization Status:** `{'Anonymized (Blank Employee Fields)' if anonymized else 'Standard'}`

### 📊 Parsing Metrics
- **Total Shift Rows Extracted:** `{len(records)}`
- **Departments Identified:** `{', '.join(departments) or 'None'}`
- **Code Tallies (N, DVERS, etc.):** `{_code_tallies(records)}`

### 🔍 Calculation & Alignment Audit
- **Headcount Verification:** `{status}`
- **Discrepancies / Warnings:** `{'; '.join(details) if details else 'None'}`

---
"""
    with path.open("a", encoding="utf-8") as journal:
        journal.write(entry)
    return path.read_text(encoding="utf-8")
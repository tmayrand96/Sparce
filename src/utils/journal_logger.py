"""Append structured execution diagnostics to the AI execution journal."""

from __future__ import annotations

import subprocess
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


def _get_git_commit_info() -> str:
    """Get the latest git commit message."""
    try:
        result = subprocess.run(
            ["git", "-C", str(DEFAULT_JOURNAL_PATH.parent.parent), "log", "-1", "--pretty=format:%s"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    return "Unknown"


def _code_tallies(records: Iterable[dict[str, Any]]) -> str:
    """Return formatted code count by department."""
    code_counter: dict[str, dict[str, int]] = {}
    for record in records:
        dept = record.get("Département", "Unknown")
        codes = record.get("Codes", []) or []
        if dept not in code_counter:
            code_counter[dept] = Counter()
        for code in codes:
            code_counter[dept][code] += 1
    
    if not code_counter:
        return "None"
    
    lines = []
    for dept in sorted(code_counter.keys()):
        codes_str = ", ".join(f"{code}={count}" for code, count in sorted(code_counter[dept].items()))
        lines.append(f"  - {dept}: {codes_str}")
    return "\n".join(lines)


def _validation_checklist(records: Iterable[dict[str, Any]]) -> list[str]:
    """Generate validation checklist items."""
    records_list = list(records)
    checklist = []
    
    # Check if records exist
    if records_list:
        checklist.append("✓ Records parsed successfully")
    
    # Check departments identified
    departments = list(dict.fromkeys(record.get("Département", "Unknown") for record in records_list))
    if departments:
        checklist.append(f"✓ Departments identified: {len(departments)}")
    
    # Check for discrepancies
    discrepancies = [r for r in records_list if r.get("Cible", 0) != r.get("Présences", 0)]
    if not discrepancies:
        checklist.append("✓ No discrepancies between target and presence")
    else:
        checklist.append(f"⚠ {len(discrepancies)} discrepancies detected")
    
    return checklist if checklist else ["✓ Validation passed"]


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
    
    timestamp_str = _format_timestamp(timestamp)
    git_commit = _get_git_commit_info()
    departments = list(dict.fromkeys(record.get("Département", "Unknown") for record in records))
    departments_count = len(departments)
    total_rows = len(records)
    code_counts_str = _code_tallies(records)
    warning_list = list(warnings or []) or ["Aucun avertissement"]
    validation_items = _validation_checklist(records)
    
    # Check if any rows have discrepancies
    discrepancies = [r for r in records if r.get("Cible", 0) != r.get("Présences", 0)]
    if discrepancies:
        audit_status = f"{len(discrepancies)} ligne(s) avec écart détecté(es). Vérification manuelle recommandée."
    else:
        audit_status = "Décompte conforme aux cibles."
    
    entry = f"""## 📝 Execution Journal Entry — {timestamp_str}

- **Dernier Commit Git:** {git_commit}
- **Description de la Mise à Jour:** Rapport de conversion PDF vers Excel avec décompte OCR et validation des codes
- **Source File:** {Path(source_file).name}
- **Report Context:** {report_date} | Shift: {shift}

### 📊 Parsing Metrics
- **Total Shift Rows Extracted:** {total_rows}
- **Total Departments Identified:** {departments_count}
- **Code Count:**
{code_counts_str}

### ⚠️ Execution Warnings
{'; '.join(warning_list) if warning_list else 'Aucun avertissement'}

### ✅ Validation Checklist
{chr(10).join(f"- {item}" for item in validation_items)}

### 📌 Notes
Anonymisation: {'Activée (Champs employé vides)' if anonymized else 'Désactivée'}

### 🔍 Calculation & Alignment Audit
{audit_status}

---
"""
    
    with path.open("a", encoding="utf-8") as journal:
        journal.write(entry)
    
    return path.read_text(encoding="utf-8")
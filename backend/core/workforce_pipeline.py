"""Convert workforce-report PDFs into formatted XLSX workbooks."""

from __future__ import annotations

import logging
import re
from io import BytesIO
from pathlib import Path
from typing import Any, Iterable

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from .pdf_parser import PDFDocumentParser

SHIFT_OPTIONS = ("Nuit", "Soir", "Jour")
VALID_CODES = (
    "N", "S", "J", "TS1.5", "TSS", "TSN", "AIC", "SIC", "FL4", "FL7",
    "FL6", "FL8", "TSTD", "MON", "CHOC", "TRI", "EVAL", "URG", "ETJ",
    "ETS", "ETN", "BRAN", "ACUR", "HSCM",
)
OVERTIME_CODES = {"TS1.5", "TSS", "TSN", "TSTD"}
LOGGER = logging.getLogger(__name__)

DEPARTMENT_PATTERNS = (
    ("HF Unité de Médecine - 4e étage", "4e"),
    ("HF Unité de Médecine - 7e étage", "7e"),
    ("HF Unité de Médecine - 6e étage", "6e"),
    ("HF Chirurgie court séjour", "8e"),
    ("HF Soins intensifs coronariens", "SIC"),
    ("HF Urgence", "URG"),
    ("HF Électrophysiologie", "ECG"),
    ("HF Accueil et réception", "ACUR/GDL"),
    ("CIUSSS Gestion des lits", "ACUR/GDL"),
)
CATEGORY_PATTERNS = (
    ("Infirmière auxiliaire", "Aux"),
    ("Préposé aux bénéficiaire", "PAB"),
    ("Préposé aux bénéficiaires", "PAB"),
    ("Agent Adm 1-2-3-4", "AA"),
    ("Infirmière", "Inf"),
)


class WorkforceReportError(ValueError):
    """Raised when a workforce report cannot be converted safely."""


def extract_report_date(text: str) -> str:
    """Extract and return the report date phrase from the PDF text."""
    match = re.search(
        r"\bLe\s+[^\n\r]+?\s+\d{1,2}\s+[A-Za-zÀ-ÿ.]+\s+\d{4}\b",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        raise WorkforceReportError("Date du rapport introuvable (format attendu: Le [jour] [date] [mois] [année]).")
    return re.sub(r"\s+", " ", match.group(0)).strip()


def _find_label(line: str, patterns: Iterable[tuple[str, str]]) -> str | None:
    folded = line.casefold()
    for label, code in patterns:
        if label.casefold() in folded:
            return code
    return None


def _codes_in(text: str) -> list[str]:
    token_pattern = re.compile(r"(?<![A-Za-z0-9.])(?:" + "|".join(map(re.escape, sorted(VALID_CODES, key=len, reverse=True))) + r")(?![A-Za-z0-9.])")
    return token_pattern.findall(text.upper())


def _error(report_date: str, shift: str, category: str, employment_code: str, detail: str) -> WorkforceReportError:
    return WorkforceReportError(
        f"{detail} | Date: {report_date} | Quart: {shift} | Catégorie d'emploi: {category} | Code d'emploi: {employment_code}"
    )


def parse_workforce_text(
    text: str, shift: str, warnings: list[str] | None = None
) -> list[dict[str, Any]]:
    """Parse report text into validated department/category records."""
    if shift not in SHIFT_OPTIONS:
        raise ValueError(f"Quart invalide: {shift}")
    report_date = extract_report_date(text)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    records: list[dict[str, Any]] = []
    current_department: str | None = None
    for index, line in enumerate(lines):
        department = _find_label(line, DEPARTMENT_PATTERNS)
        if department:
            current_department = department
            continue
        category = _find_label(line, CATEGORY_PATTERNS)
        if not category:
            continue
        if current_department is None:
            raise _error(report_date, shift, category, category, "Département introuvable")

        block = line
        for following in lines[index + 1:]:
            if _find_label(following, DEPARTMENT_PATTERNS) or _find_label(following, CATEGORY_PATTERNS):
                break
            block += " " + following
        codes = _codes_in(block)
        presence = len(codes)
        ratio_match = re.search(r"(?<!\d)(\d+)\s*/\s*(\d+)(?!\d)", block)
        if ratio_match:
            target = int(ratio_match.group(1))
            stated_presence = int(ratio_match.group(2))
            if stated_presence != presence:
                warning = (
                    f"Écart détecté [{report_date} | {shift} | {current_department} | {category}] : "
                    f"Présences indiquées = {stated_presence}, Codes comptés = {presence}. "
                    f"La valeur {presence} a été retenue pour le fichier Excel."
                )
                LOGGER.warning(warning)
                if warnings is not None:
                    warnings.append(warning)
        elif category == "AA" or current_department == "ACUR/GDL":
            target = presence
        else:
            raise _error(report_date, shift, category, category, "Cible/Présences manquant")

        if shift == "Soir" and current_department == "URG":
            target = 3
        extra_codes = codes[target:] if presence > target else []
        if presence > target:
            suffix = f"+{presence - target}TS" if any(code in OVERTIME_CODES for code in extra_codes) else f"+{presence - target}R"
        elif presence < target:
            suffix = f"-{target - presence}"
        else:
            suffix = ""
        records.append({"Département": current_department, "Catégorie": category, "Cible": target, "Présences": presence, "Écart": suffix, "Codes": codes, "Date": report_date})
    if not records:
        raise WorkforceReportError(f"Aucune catégorie d'effectif trouvée | Date: {report_date} | Quart: {shift} | Catégorie d'emploi: inconnue | Code d'emploi: inconnu")
    return records


def build_workforce_workbook(records: list[dict[str, Any]], shift: str) -> BytesIO:
    """Create a formatted workbook from validated workforce records."""
    if not records:
        raise ValueError("Au moins une ligne d'effectif est requise")
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Effectifs"
    report_date = records[0]["Date"]
    sheet.merge_cells("A1:E1")
    sheet["A1"] = shift
    sheet.merge_cells("A2:E2")
    sheet["A2"] = report_date
    headers = ("Département", "Catégorie", "Cible", "Présences", "Écart")
    for column, header in enumerate(headers, 1):
        sheet.cell(row=4, column=column, value=header)
    for row, record in enumerate(records, 5):
        for column, header in enumerate(headers, 1):
            sheet.cell(row=row, column=column, value=record[header])
    navy = "17324D"
    pale = "E8EEF3"
    thin_gray = Side(style="thin", color="B8C2CC")
    for cell in sheet[1] + sheet[2]:
        cell.font = Font(bold=True, size=14 if cell.row == 1 else 11, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor=navy)
        cell.alignment = Alignment(horizontal="center")
    for cell in sheet[4]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor=navy)
        cell.alignment = Alignment(horizontal="center")
    for row in sheet.iter_rows(min_row=4, max_row=sheet.max_row, min_col=1, max_col=5):
        for cell in row:
            cell.border = Border(bottom=thin_gray)
            if cell.row > 4 and cell.row % 2 == 1:
                cell.fill = PatternFill("solid", fgColor=pale)
    for column, width in enumerate((20, 18, 12, 14, 12), 1):
        sheet.column_dimensions[get_column_letter(column)].width = width
    sheet.freeze_panes = "A5"
    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    return output


def convert_workforce_pdf(
    pdf_path: str | Path, shift: str, warnings: list[str] | None = None
) -> BytesIO:
    """Extract a PDF report and return its formatted XLSX representation."""
    try:
        parsed = PDFDocumentParser().parse(pdf_path)
        if parsed.get("status") != "success":
            raise WorkforceReportError(parsed.get("message", "Extraction PDF impossible"))
        records = parse_workforce_text(parsed["raw_text"], shift, warnings)
        return build_workforce_workbook(records, shift)
    except WorkforceReportError:
        raise
    except Exception as exc:
        raise WorkforceReportError(f"Erreur de conversion du rapport: {exc}") from exc
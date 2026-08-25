"""Convert workforce-report PDFs into formatted XLSX workbooks."""

from __future__ import annotations

import logging
import re
from io import BytesIO
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from .pdf_parser import PDFDocumentParser

SHIFT_OPTIONS = ("Nuit", "Soir", "Jour")
VALID_CODES = (
    "N", "S", "J", "TS1.5", "TSS", "TSN", "AIC", "SIC", "FL4", "FL7",
    "FL6", "FL8", "TSTD", "MON", "CHOC", "TRI", "EVAL", "URG", "ETJ",
    "ETS", "ETN", "BRAN", "ACUR", "HSCM", "DVERS",
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
DEPARTMENT_ORDER = ("4e", "7e", "6e", "8e", "SIC", "CDJ", "URG", "ECG", "ACUR/GDL")
CATEGORY_PATTERNS = (
    ("Infirmière auxiliaire", "Aux"),
    ("Préposé aux bénéficiaire", "PAB"),
    ("Préposé aux bénéficiaires", "PAB"),
    ("Agent Adm 1-2-3-4", "AA"),
    ("Infirmière", "Inf"),
)


class WorkforceReportError(ValueError):
    """Raised when a workforce report cannot be converted safely."""


DATE_PATTERN = re.compile(
    r"\b(?:Le\s+)?(?:lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)?\s*"
    r"\d{1,2}(?:\s+au\s+\d{1,2})?\s+"
    r"(?:janv?(?:ier)?|févr?(?:ier)?|mars|avr(?:il)?|mai|juin|juil(?:let)?|"
    r"août|sept?(?:embre)?|oct(?:obre)?|nov(?:embre)?|déc(?:embre)?)\.?\s+\d{4}\b",
    flags=re.IGNORECASE,
)


def _date_phrases(text: str) -> list[str]:
    return [re.sub(r"\s+", " ", match.group(0)).strip() for match in DATE_PATTERN.finditer(text)]


def extract_report_date(text: str) -> str:
    """Extract the complete date range represented in the report text."""
    dates = list(dict.fromkeys(_date_phrases(text)))
    if not dates:
        raise WorkforceReportError("Date du rapport introuvable (format attendu: Le [jour] [date] [mois] [année]).")
    return " | ".join(dates)


def _find_label(line: str, patterns: Iterable[tuple[str, str]]) -> str | None:
    folded = line.casefold()
    for label, code in patterns:
        if label.casefold() in folded:
            return code
    return None


def _find_department(line: str) -> str | None:
    department = _find_label(line, DEPARTMENT_PATTERNS)
    if department:
        return department
    if re.search(r"\b7(?:e|ème|eme)?\s+étage\b", line, re.IGNORECASE):
        return "7e"
    if re.search(r"\b6(?:e|ème|eme)?\s+étage\b", line, re.IGNORECASE):
        return "6e"
    if re.search(r"\bSIC\b", line, re.IGNORECASE) and re.search(r"\bHF\b", line, re.IGNORECASE):
        return "SIC"
    if re.search(r"\bECG\b", line, re.IGNORECASE) and re.search(r"\bHF\b", line, re.IGNORECASE):
        return "ECG"
    return None


def _codes_in(text: str) -> list[str]:
    token_pattern = re.compile(r"(?<![A-Za-z0-9.])(?:" + "|".join(map(re.escape, sorted(VALID_CODES, key=len, reverse=True))) + r")(?![A-Za-z0-9.])")
    return token_pattern.findall(text.upper())


def _codes_in_code_column(block: str) -> list[str]:
    """Count only codes after the row's target/presence ratio."""
    ratio_match = re.search(r"(?<!\d)(\d+)\s*/\s*(\d+)(?!\d)", block)
    code_text = block[ratio_match.end():] if ratio_match else block
    return _codes_in(code_text)


def _codes_for_department(block: str, department: str) -> list[str]:
    codes = _codes_in_code_column(block)
    if department != "URG":
        return [code for code in codes if code != "DVERS"]
    return codes


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
    current_date = report_date.split(" | ")[0]
    sic_occurrence = 0
    for index, line in enumerate(lines):
        dates_on_line = _date_phrases(line)
        if dates_on_line:
            current_date = dates_on_line[0]
        department = _find_department(line)
        if department:
            if department == "SIC":
                sic_occurrence += 1
                current_department = "CDJ" if sic_occurrence in {3, 4} else department
            else:
                current_department = department
            continue
        category = _find_label(line, CATEGORY_PATTERNS)
        if not category:
            continue
        if current_department is None:
            raise _error(report_date, shift, category, category, "Département introuvable")

        block = line
        for following in lines[index + 1:]:
            if _find_department(following) or _find_label(following, CATEGORY_PATTERNS):
                break
            block += " " + following
        codes = _codes_for_department(block, current_department)
        presence = len(codes)
        ratio_match = re.search(r"(?<!\d)(\d+)\s*/\s*(\d+)(?!\d)", block)
        if ratio_match:
            target = int(ratio_match.group(1))
            stated_presence = int(ratio_match.group(2))
            if stated_presence != presence:
                warning = (
                    f"Écart détecté [{current_date} | {shift} | {current_department} | {category}] : "
                    f"Présences indiquées = {stated_presence}, Codes comptés = {presence}. "
                    f"La valeur {presence} a été retenue pour le fichier Excel."
                )
                LOGGER.warning(warning)
                if warnings is not None:
                    warnings.append(warning)
        elif category == "AA" or current_department == "ACUR/GDL":
            target = presence
        else:
            target = 0

        if shift == "Soir" and current_department == "URG":
            target = 3
        if current_department == "URG" and category == "Aux":
            target = 1
        extra_codes = codes[target:] if presence > target else []
        if presence > target:
            suffix = f"+{presence - target}TS" if any(code in OVERTIME_CODES for code in extra_codes) else f"+{presence - target}R"
        elif presence < target:
            suffix = f"-{target - presence}"
        else:
            suffix = ""
        records.append({"Département": current_department, "Catégorie": category, "Cible": target, "Présences": presence, "Décompte des codes": len(codes), "Écart": suffix, "Codes": codes, "Date": current_date})
    if not records:
        raise WorkforceReportError(f"Aucune catégorie d'effectif trouvée | Date: {report_date} | Quart: {shift} | Catégorie d'emploi: inconnue | Code d'emploi: inconnu")
    present_departments = {record["Département"] for record in records}
    required_departments = {"7e", "6e", "SIC", "ECG"}
    for department in sorted(required_departments - present_departments):
        records.append({
            "Département": department,
            "Catégorie": "",
            "Cible": 0,
            "Présences": 0,
            "Décompte des codes": 0,
            "Écart": "",
            "Codes": [],
            "Date": current_date,
        })
    return records


def build_workforce_workbook(records: list[dict[str, Any]], shift: str) -> BytesIO:
    """Create a formatted workbook from validated workforce records."""
    if not records:
        raise ValueError("Au moins une ligne d'effectif est requise")
    output = BytesIO()
    headers = ("Département", "Catégorie", "Cible", "Présences", "Écart (Présences vs Cible)", "Écart (Décompte vs Cible)")
    records_by_date: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        date = record.get("Date", "") or "Date inconnue"
        records_by_date.setdefault(date, []).append(record)

    def sheet_name_for(date: str, used_names: set[str]) -> str:
        base_name = re.sub(r"[\\/*?:\[\]]", "-", date).strip() or "Effectifs"
        base_name = base_name[:31]
        name = base_name
        suffix = 2
        while name in used_names:
            suffix_text = f" ({suffix})"
            name = f"{base_name[:31 - len(suffix_text)]}{suffix_text}"
            suffix += 1
        used_names.add(name)
        return name

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        workbook = writer.book
        used_sheet_names: set[str] = set()
        sheets = []
        for report_date, date_records in records_by_date.items():
            rows = [
                {
                    "Département": record.get("Département", ""),
                    "Catégorie": record.get("Catégorie", ""),
                    "Cible": record.get("Cible", 0),
                    "Présences": record.get("Présences", 0),
                    "_code_count": record.get(
                        "Décompte des codes", len(record.get("Codes", []) or [])
                    ),
                }
                for record in date_records
            ]
            dataframe = pd.DataFrame(rows, columns=(*headers[:-1], "_code_count")).fillna(
                {"Cible": 0, "Présences": 0}
            )
            dataframe["Cible"] = pd.to_numeric(dataframe["Cible"], errors="coerce").fillna(0)
            dataframe["Présences"] = pd.to_numeric(
                dataframe["Présences"], errors="coerce"
            ).fillna(0)
            department_dtype = pd.api.types.CategoricalDtype(
                categories=DEPARTMENT_ORDER, ordered=True
            )
            dataframe["Département"] = dataframe["Département"].astype(department_dtype)
            dataframe = dataframe.sort_values(
                by="Département", kind="stable", na_position="last"
            ).reset_index(drop=True)
            code_counts = pd.to_numeric(
                dataframe.pop("_code_count"),
                errors="coerce",
            ).fillna(0)
            dataframe["Écart (Présences vs Cible)"] = dataframe["Présences"] - dataframe["Cible"]
            dataframe["Écart (Décompte vs Cible)"] = code_counts - dataframe["Cible"]
            sheet_name = sheet_name_for(report_date, used_sheet_names)
            dataframe.to_excel(writer, sheet_name=sheet_name, startrow=3, index=False)
            sheet = writer.sheets[sheet_name]
            sheets.append((sheet, dataframe))

            sheet.merge_cells("A1:F1")
            sheet["A1"] = shift
            sheet.merge_cells("A2:F2")
            sheet["A2"] = report_date
    navy = "17324D"
    pale = "E8EEF3"
    thin_gray = Side(style="thin", color="B8C2CC")
    red_fill = PatternFill("solid", fgColor="FFC7CE")
    green_fill = PatternFill("solid", fgColor="C6EFCE")
    for sheet, dataframe in sheets:
        for cell in sheet[1] + sheet[2]:
            cell.font = Font(bold=True, size=14 if cell.row == 1 else 11, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor=navy)
            cell.alignment = Alignment(horizontal="center")
        for cell in sheet[4]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor=navy)
            cell.alignment = Alignment(horizontal="center")
        for row in sheet.iter_rows(min_row=4, max_row=sheet.max_row, min_col=1, max_col=6):
            for cell in row:
                cell.border = Border(bottom=thin_gray)
                if cell.row > 4 and cell.row % 2 == 1:
                    cell.fill = PatternFill("solid", fgColor=pale)
        for column in ("E", "F"):
            for cell in sheet[column][4:]:
                if cell.value != 0:
                    cell.fill = red_fill
            sheet.conditional_formatting.add(
                f"{column}5:{column}{sheet.max_row}",
                CellIsRule(operator="notEqual", formula=["0"], fill=red_fill),
            )
        for row in range(5, sheet.max_row + 1):
            if sheet.cell(row, 1).value != "ACUR/GDL":
                continue
            if sheet.cell(row, 5).value >= 0 and sheet.cell(row, 6).value >= 0:
                sheet.merge_cells(start_row=row, start_column=3, end_row=row, end_column=6)
                merged_cell = sheet.cell(row, 3)
                merged_cell.value = "OK"
                merged_cell.fill = green_fill
                merged_cell.alignment = Alignment(horizontal="center", vertical="center")
                for column in range(4, 7):
                    sheet.cell(row, column).fill = green_fill
        for column, width in enumerate((20, 18, 12, 14, 24, 24), 1):
            sheet.column_dimensions[get_column_letter(column)].width = width
        sheet.freeze_panes = "A5"
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
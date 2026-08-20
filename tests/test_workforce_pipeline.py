from io import BytesIO

import pytest
from openpyxl import load_workbook

from backend.core.workforce_pipeline import WorkforceReportError, build_workforce_workbook, parse_workforce_text


REPORT_TEXT = """Le vendredi 4 sept. 2026
HF Urgence
Infirmière 1/1 URG
HF Unité de Médecine - 4e étage
Infirmière 3/4 N S J TS1.5
Agent Adm 1-2-3-4 ACUR HSCM
"""


def test_parse_report_applies_shift_exception_and_validates_codes():
    records = parse_workforce_text(REPORT_TEXT, "Soir")

    assert records[0]["Département"] == "URG"
    assert records[0]["Cible"] == 3
    assert records[0]["Présences"] == 1
    assert records[0]["Écart"] == "-2"
    assert records[1]["Écart"] == "+1TS"
    assert records[2]["Cible"] == 2
    assert records[2]["Présences"] == 2


def test_workbook_contains_shift_date_and_formatted_rows():
    records = parse_workforce_text(REPORT_TEXT, "Soir")
    workbook = build_workforce_workbook(records, "Soir")

    sheet = load_workbook(BytesIO(workbook.getvalue())).active
    assert sheet["A1"].value == "Soir"
    assert sheet["A2"].value == "Le vendredi 4 sept. 2026"
    assert sheet["E6"].value == "+1TS"
    assert sheet.freeze_panes == "A5"


def test_ratio_mismatch_has_operational_error_context():
    text = "Le vendredi 4 sept. 2026\nHF Urgence\nInfirmière 2/1 URG N"

    with pytest.raises(WorkforceReportError, match=r"Date: .*Quart: Nuit.*Catégorie d'emploi: Inf.*Code d'emploi: Inf"):
        parse_workforce_text(text, "Nuit")
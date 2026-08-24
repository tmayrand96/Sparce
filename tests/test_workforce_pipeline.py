from io import BytesIO
from openpyxl import load_workbook

from backend.core.workforce_pipeline import build_workforce_workbook, parse_workforce_text


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
    assert sheet["E6"].value == 1
    assert sheet["E6"].fill.fgColor.rgb == "00FFC7CE"
    assert sheet.freeze_panes == "A5"


def test_ratio_mismatch_uses_counted_codes_and_reports_warning():
    text = "Le vendredi 4 sept. 2026\nHF Urgence\nInfirmière 2/1 URG N"

    warnings = []
    records = parse_workforce_text(text, "Nuit", warnings)
    workbook = build_workforce_workbook(records, "Nuit")
    sheet = load_workbook(BytesIO(workbook.getvalue())).active

    assert records[0]["Présences"] == 2
    assert sheet["D5"].value == 2
    assert warnings == [
        "Écart détecté [Le vendredi 4 sept. 2026 | Nuit | URG | Inf] : "
        "Présences indiquées = 1, Codes comptés = 2. "
        "La valeur 2 a été retenue pour le fichier Excel."
    ]


def test_workbook_defaults_missing_target_and_presence_to_zero():
    workbook = build_workforce_workbook(
        [{"Département": "URG", "Catégorie": "Inf", "Date": "Le 4 sept. 2026"}],
        "Nuit",
    )

    sheet = load_workbook(BytesIO(workbook.getvalue())).active

    assert sheet["C5"].value == 0
    assert sheet["D5"].value == 0
    assert sheet["E5"].value == 0
    assert sheet["E5"].fill.fgColor.rgb != "00FFC7CE"
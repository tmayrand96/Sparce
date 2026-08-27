from io import BytesIO
from openpyxl import load_workbook

from backend.core.workforce_pipeline import build_workforce_workbook, parse_ratio, parse_workforce_text


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

    loaded_workbook = load_workbook(BytesIO(workbook.getvalue()))
    sheet = loaded_workbook["Le vendredi 4 sept. 2026"]
    assert sheet["A1"].value == "Soir"
    assert sheet["A2"].value == "Le vendredi 4 sept. 2026"
    fourth_floor_row = next(row for row in range(5, sheet.max_row + 1) if sheet.cell(row, 1).value == "4e")
    assert sheet.cell(fourth_floor_row, 5).value == 1
    assert sheet.cell(fourth_floor_row, 5).fill.fgColor.rgb == "00FFC7CE"
    assert sheet.freeze_panes == "A5"


def test_ratio_mismatch_uses_counted_codes_and_reports_warning():
    text = "Le vendredi 4 sept. 2026\nHF Urgence\nInfirmière 2/1 URG N"

    warnings = []
    records = parse_workforce_text(text, "Nuit", warnings)
    workbook = build_workforce_workbook(records, "Nuit")
    sheet = load_workbook(BytesIO(workbook.getvalue()))["Le vendredi 4 sept. 2026"]

    assert records[0]["Présences"] == 2
    urg_row = next(row for row in range(5, sheet.max_row + 1) if sheet.cell(row, 1).value == "URG")
    assert sheet.cell(urg_row, 4).value == 2
    assert warnings == [
        "Écart détecté [Le vendredi 4 sept. 2026 | Nuit | URG | Inf] : "
        "Présences indiquées = 1, Codes comptés = 2. "
        "La valeur 2 a été retenue pour le fichier Excel."
    ]


def test_anonymized_report_keeps_rows_with_flexible_department_header():
    text = """Le vendredi 4 sept. 2026
HF Unité de Médecine 4e étage
Infirmière Ratio/Présences 1 TE N
"""

    records = parse_workforce_text(text, "Nuit")

    assert records[0]["Département"] == "4e"
    assert records[0]["Présences"] == 1
    assert records[0]["Codes"] == ["N"]


def test_parse_ratio_accepts_complete_partial_and_missing_values():
    assert parse_ratio("Ratio/Présences 3/3") == (3, 3)
    assert parse_ratio("Ratio/Présences 1") == (1, None)
    assert parse_ratio("Ratio/Présences/") == (None, None)


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


def test_workbook_uses_one_sheet_per_report_date():
    text = """Le lundi 7 sept. 2026
HF Urgence
Infirmière 1/1 N
Le mardi 8 sept. 2026
HF Urgence
Infirmière 1/1 J
"""

    records = parse_workforce_text(text, "Nuit")
    workbook = load_workbook(BytesIO(build_workforce_workbook(records, "Nuit").getvalue()))

    assert workbook.sheetnames == ["Rapport_Audit", "Le lundi 7 sept. 2026", "Le mardi 8 sept. 2026"]
    assert workbook[workbook.sheetnames[1]]["A2"].value == "Le lundi 7 sept. 2026"
    assert workbook[workbook.sheetnames[2]]["A2"].value == "Le mardi 8 sept. 2026"


def test_workbook_sorts_departments_in_business_order():
    records = [
        {"Département": department, "Catégorie": "Inf", "Cible": 1, "Présences": 1, "Date": "Le 7 sept. 2026"}
        for department in ("URG", "4e", "ACUR/GDL", "CDJ", "7e", "ECG", "8e", "SIC", "6e")
    ]

    workbook = load_workbook(BytesIO(build_workforce_workbook(records, "Nuit").getvalue()))
    sheet = workbook["Le 7 sept. 2026"]
    departments = list(dict.fromkeys(sheet.cell(row, 1).value for row in range(5, sheet.max_row + 1)))

    assert departments == ["4e", "7e", "6e", "8e", "SIC", "CDJ", "URG", "ECG", "ACUR/GDL"]


def test_each_date_sheet_contains_complete_department_category_skeleton():
    records = [{"Département": "URG", "Catégorie": "Inf", "Cible": 2, "Présences": 1, "Date": "Le 7 sept. 2026"}]

    workbook = load_workbook(BytesIO(build_workforce_workbook(records, "Nuit").getvalue()))
    sheet = workbook["Le 7 sept. 2026"]
    pairs = {(sheet.cell(row, 1).value, sheet.cell(row, 2).value) for row in range(5, sheet.max_row + 1)}

    assert len(pairs) == 36
    assert all((department, category) in pairs for department in ("4e", "7e", "6e", "8e", "SIC", "CDJ", "URG", "ECG", "ACUR/GDL") for category in ("Inf", "Aux", "PAB", "AA"))


def test_audit_tab_records_execution_summary_and_ocr_flags():
    warnings = []
    records = parse_workforce_text(
        "Le lundi 7 sept. 2026\nHF Urgence\nInfirmière 25/1 URG N",
        "Nuit",
        warnings,
    )

    workbook = load_workbook(BytesIO(build_workforce_workbook(records, "Nuit", warnings).getvalue()))
    audit = workbook["Rapport_Audit"]

    assert workbook.sheetnames[0] == "Rapport_Audit"
    assert audit["A1"].value == "Rapport d'audit d'exécution"
    assert audit["A5"].value == "Le lundi 7 sept. 2026"
    assert audit["B5"].value == 0
    assert audit["E5"].value == 2
    assert audit["A8"].value == warnings[0]


def test_business_rules_remap_sic_count_dvers_and_merge_acur_gdl():
    text = """Le lundi 7 sept. 2026
HF Soins intensifs coronariens
Infirmière 1/1 SIC
HF Soins intensifs coronariens
Infirmière auxiliaire 1/1 SIC
HF Soins intensifs coronariens
Infirmière 1/1 SIC
HF Soins intensifs coronariens
Infirmière auxiliaire 1/1 SIC
HF Urgence
Infirmière auxiliaire 2/2 DVERS
HF Accueil et réception
Agent Adm 1-2-3-4 ACUR
"""

    records = parse_workforce_text(text, "Nuit")
    sic_records = [record for record in records if record["Codes"] == ["SIC"]]
    urg_aux = next(record for record in records if record["Département"] == "URG" and record["Catégorie"] == "Aux")
    workbook = load_workbook(BytesIO(build_workforce_workbook(records, "Nuit").getvalue()))
    sheet = workbook["Le lundi 7 sept. 2026"]

    assert [record["Département"] for record in sic_records] == ["SIC", "SIC", "CDJ", "CDJ"]
    assert urg_aux["Présences"] == 1
    assert urg_aux["Cible"] == 1
    acur_row = next(row for row in range(5, sheet.max_row + 1) if sheet.cell(row, 1).value == "ACUR/GDL")
    assert f"C{acur_row}:F{acur_row}" in {str(rng) for rng in sheet.merged_cells.ranges}
    assert sheet.cell(acur_row, 3).value == "OK"
    assert sheet.cell(acur_row, 3).fill.fgColor.rgb == "00C6EFCE"
import datetime
from io import BytesIO

import pandas as pd
from openpyxl import load_workbook

from backend.core.workforce import (
    build_workforce_period_report,
    generate_summary_excel,
    load_cibles_reference,
    parse_workforce_xlsx,
    select_cibles_for_period,
)


def _workbook_bytes():
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        pd.DataFrame(
            [
                ["Jour", "LUNDI"],
                ["Date", "2026-09-21"],
                ["Type de quart", "JOUR"],
                [],
                ["Département", "Catégorie", "Cible", "Présences", "Écart"],
                ["Unité A", "PAB", 4, 2, -2],
                ["Unité B", "Inf", 3, 5, 2],
            ]
        ).to_excel(writer, sheet_name="LUNDI", header=False, index=False)
    output.seek(0)
    return output


def _workbook_with_header_on_line_three():
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        pd.DataFrame(
            [
                ["Jour", "MARDI"],
                ["Date", "2026-09-22"],
                ["Département", "Catégorie", "Cible", "Présences", "Écart"],
                ["Unité C", "Aux", 5, 4, -1],
            ]
        ).to_excel(writer, sheet_name="MARDI", header=False, index=False)
    output.seek(0)
    return output


def test_load_cibles_reference_normalizes_canonical_french_headers(tmp_path):
    reference_path = tmp_path / "Cibles.xlsx"
    weekday_values = [
        ["Departement", "Catégorie", "JOUR", "SOIR", "NUIT"],
        ["Unité A", "PAB", 4, 3, 2],
    ]
    weekend_values = [
        ["Departement", "Catégorie", "JOUR", "SOIR", "NUIT"],
        ["Unité A", "PAB", 5, 4, 3],
    ]
    with pd.ExcelWriter(reference_path, engine="openpyxl") as writer:
        pd.DataFrame(weekday_values).to_excel(
            writer, sheet_name="Cibles", startrow=1, header=False, index=False
        )
        pd.DataFrame(weekend_values).to_excel(
            writer, sheet_name="Cibles", startrow=1, startcol=6, header=False, index=False
        )

    df_semaine, df_fin_semaine = load_cibles_reference(reference_path)
    selected = select_cibles_for_period(
        df_semaine,
        df_fin_semaine,
        datetime.date(2026, 9, 21),
        "JOUR",
    )

    assert selected.to_dict(orient="records") == [
        {"Département": "Unité A", "Catégorie": "PAB", "Cible": 4}
    ]


def test_select_cibles_for_period_uses_selected_quart_and_matching_period_table():
    df_semaine = pd.DataFrame(
        {"Département": ["Unité A"], "Catégorie": ["PAB"], "JOUR": [2], "SOIR": [3], "NUIT": [1]}
    )
    df_fin_semaine = pd.DataFrame(
        {"Département": ["Unité A"], "Catégorie": ["PAB"], "JOUR": [5], "SOIR": [6], "NUIT": [4]}
    )

    weekday_target = select_cibles_for_period(
        df_semaine, df_fin_semaine, datetime.date(2026, 9, 21), "SOIR"
    )
    weekend_target = select_cibles_for_period(
        df_semaine, df_fin_semaine, datetime.date(2026, 9, 26), "SOIR"
    )

    assert weekday_target["Cible"].tolist() == [3]
    assert weekend_target["Cible"].tolist() == [6]


def test_parse_workforce_xlsx_splits_needs_and_surplus():
    needs, surplus, summary = parse_workforce_xlsx(_workbook_bytes())

    assert len(needs) == 1
    assert needs.iloc[0]["Besoins"] == 2
    assert needs.iloc[0]["Quart"] == "JOUR"
    assert len(surplus) == 1
    assert surplus.iloc[0]["Surplus"] == 2
    assert summary["lignes_analysees"] == 2


def test_parse_workforce_xlsx_uses_pandas_index_two_as_header():
    needs, surplus, summary = parse_workforce_xlsx(_workbook_with_header_on_line_three())

    assert len(needs) == 1
    assert needs.iloc[0]["Catégorie"] == "Aux"
    assert needs.iloc[0]["Besoins"] == 1
    assert surplus.empty
    assert summary["lignes_analysees"] == 1


def test_build_workforce_period_report_normalizes_categories_and_selects_weekend_targets():
    workbook_bytes = BytesIO()
    with pd.ExcelWriter(workbook_bytes, engine="openpyxl") as writer:
        for sheet_name in ("Vendredi", "Samedi"):
            pd.DataFrame(
                [
                    ["Département", "Catégorie d'emploi", "Présences"],
                    ["Unité A", "Inf", 3],
                    ["Unité A", "AA", 2],
                ]
            ).to_excel(writer, sheet_name=sheet_name, header=False, index=False)
    workbook_bytes.seek(0)

    df_semaine = pd.DataFrame(
        {"Département": ["Unité A", "Unité A"], "Catégorie": ["AA", "Inf"], "JOUR": [1, 2]}
    )
    df_fin_semaine = pd.DataFrame(
        {"Département": ["Unité A", "Unité A"], "Catégorie": ["AA", "Inf"], "JOUR": [4, 5]}
    )

    df_final = build_workforce_period_report(
        workbook_bytes,
        datetime.date(2026, 9, 25),
        datetime.date(2026, 9, 26),
        df_semaine,
        df_fin_semaine,
        "JOUR",
    )

    assert df_final["Date"].tolist() == [datetime.date(2026, 9, 25)] * 2 + [
        datetime.date(2026, 9, 26)
    ] * 2
    assert df_final["Catégorie"].astype(str).tolist() == ["AA", "Inf", "AA", "Inf"]
    assert df_final["Cible"].tolist() == [1, 2, 4, 5]


def test_generate_summary_excel_has_expected_sheets_and_formatting():
    needs, surplus, _ = parse_workforce_xlsx(_workbook_bytes())

    workbook = load_workbook(generate_summary_excel(needs, surplus))

    assert workbook.sheetnames == ["Sommaire Besoins", "Sommaire Surplus"]
    assert workbook["Sommaire Besoins"]["A1"].value == "Jour"
    assert len(workbook["Sommaire Besoins"].conditional_formatting) == 1
    assert len(workbook["Sommaire Surplus"].conditional_formatting) == 1
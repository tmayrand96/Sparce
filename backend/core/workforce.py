"""Workforce replacement activity transformation and analysis helpers."""

from __future__ import annotations

import datetime
import json
import os
import re
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

import pandas as pd
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Font, PatternFill

from .summarizer import GoogleGeminiSummarizer


OUTPUT_COLUMNS = [
    "Jour",
    "Date",
    "Quart",
    "Département",
    "Catégorie",
    "Cible",
    "Présences",
    "Écart",
    "Besoins",
    "Surplus",
]

# Ordre d'affichage strict des catégories d'emploi, imposé sur tout le module.
CATEGORY_ORDER = ["AA", "Inf", "Aux", "PAB"]

# Emplacement par défaut du dictionnaire de cibles backend (utilisé si la découverte dynamique échoue).
CIBLES_XLSX_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "Cibles.xlsx"

# Les clés sont comparées aux en-têtes une fois nettoyés (strip + suppression des sauts de ligne + upper).
CIBLES_COLUMN_RENAME_MAP = {
    "DÉPARTEMENT": "Département",
    "DEPARTEMENT": "Département",
    "CATÉGORIE": "Catégorie",
    "CATÉGORIE D'EMPLOI": "Catégorie",
    "UNITE": "Département",
    "UNITÉ": "Département",
    "UNITE DE SOINS": "Département",
    "UNITÉ DE SOINS": "Département",
}

# Variantes tolérées des noms de quart (accents/pluriels/espaces déjà neutralisés par le nettoyage
# des en-têtes); permet de faire correspondre un classeur Cibles.xlsx réel même si sa mise en forme
# diverge légèrement du format canonique JOUR/SOIR/NUIT.
QUART_HEADER_ALIASES = {
    "JOUR": {"JOUR", "JOURS", "JR", "J"},
    "SOIR": {"SOIR", "SOIRS", "PM", "S"},
    "NUIT": {"NUIT", "NUITS", "N"},
}

NON_QUART_COLUMNS = {"Département", "Catégorie"}


def _clean_column_headers(df: pd.DataFrame) -> pd.DataFrame:
    """Strip whitespace/newlines and force uppercase headers to survive sloppy Excel input."""
    df = df.copy()
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.replace("\n", "", regex=False)
        .str.replace("\r", "", regex=False)
        .str.upper()
    )
    return df


def _rename_quart_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Map tolerated quart header variants (JOURS, JR, ...) onto the canonical JOUR/SOIR/NUIT names."""
    rename_map: dict[str, str] = {}
    for column in df.columns:
        if column in NON_QUART_COLUMNS or column in QUART_HEADER_ALIASES:
            continue
        for canonical, aliases in QUART_HEADER_ALIASES.items():
            if column in aliases:
                rename_map[column] = canonical
                break
    return df.rename(columns=rename_map) if rename_map else df


def _find_project_root(start: Optional[Path] = None) -> Path:
    """Walk upward from this file to locate the project root (marked by .git or app.py)."""
    current = (start or Path(__file__).resolve()).parent
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists() or (candidate / "frontend" / "app.py").exists():
            return candidate
    return Path(__file__).resolve().parent.parent.parent


def _discover_cibles_path(project_root: Optional[Path] = None) -> Optional[Path]:
    """Recursively search the whole project tree, case-insensitively, for the reference workbook."""
    root = project_root or _find_project_root()
    matches = sorted(root.rglob("[cC]ibles.xlsx"))
    return matches[0] if matches else None


def _report_missing_cibles(project_root: Path) -> str:
    """Build a diagnostic report (and surface it instantly via Streamlit) when Cibles.xlsx is unfindable."""
    def _list_dir(relative: str) -> str:
        target = project_root / relative
        if not target.exists():
            return f"  (répertoire '{relative}/' introuvable sous {project_root})"
        entries = sorted(entry.name for entry in target.iterdir())
        return "\n".join(f"  - {name}" for name in entries) if entries else "  (répertoire vide)"

    diagnostic = (
        "Fichier 'Cibles.xlsx' introuvable après recherche récursive dans le projet.\n\n"
        f"Racine du projet analysée: {project_root}\n\n"
        f"Contenu de 'tests/':\n{_list_dir('tests')}\n\n"
        f"Contenu de 'data/':\n{_list_dir('data')}\n\n"
        "Avertissement: si le fichier existe dans le dépôt Git mais reste introuvable en production, "
        "vérifiez qu'il n'est pas exclu par .gitignore (les fichiers .xlsx y sont parfois listés)."
    )

    try:  # pragma: no cover - Streamlit not guaranteed to be importable in test contexts
        import streamlit as st

        st.error(diagnostic)
    except Exception:
        pass

    return diagnostic



def _normalized(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _find_metadata(rows: list[list[Any]], sheet_name: str) -> dict[str, Any]:
    metadata: dict[str, Any] = {"Jour": sheet_name, "Date": "", "Quart": ""}
    for row in rows[:12]:
        for index, value in enumerate(row):
            label = _normalized(value).rstrip(":")
            if label in {"jour", "date", "quart", "type de quart", "shift"}:
                next_value = row[index + 1] if index + 1 < len(row) else ""
                if label == "jour":
                    metadata["Jour"] = next_value or sheet_name
                elif label == "date":
                    metadata["Date"] = next_value
                else:
                    metadata["Quart"] = next_value
            elif label in {"jour", "date", "quart", "type de quart"}:
                metadata[label.title()] = value

    if not metadata["Quart"]:
        for candidate in (sheet_name, *(str(cell) for row in rows[:8] for cell in row)):
            match = re.search(r"\b(jour|soir|nuit)\b", _normalized(candidate))
            if match:
                metadata["Quart"] = match.group(1).upper()
                break
    return metadata


def _find_table_header(df_raw: pd.DataFrame) -> tuple[int, pd.DataFrame, dict[str, int]]:
    aliases = {
        "Département": {"département", "departement", "department", "unité", "unite"},
        "Catégorie": {"catégorie", "categorie", "catégorie d'emploi", "emploi", "poste"},
        "Cible": {"cible", "besoin", "requis", "effectif requis"},
        "Présences": {"présences", "presences", "présence", "presence", "effectif"},
        "Écart": {"écart", "ecart", "différence", "difference", "delta"},
    }
    def find_positions(columns: Any) -> dict[str, int]:
        normalized = [_normalized(cell) for cell in columns]
        positions: dict[str, int] = {}
        for name, accepted in aliases.items():
            for column_index, value in enumerate(normalized):
                if value in accepted or any(alias in value for alias in accepted if len(alias) > 5):
                    positions[name] = column_index
                    break
        return positions

    header_row_idx = None
    if len(df_raw.index) > 2:
        row_3 = df_raw.iloc[2]
        if any("département" in _normalized(value) for value in row_3):
            header_row_idx = 2

    if header_row_idx is None:
        for row_index in range(min(6, len(df_raw.index))):
            row = df_raw.iloc[row_index]
            if any("département" in _normalized(value) for value in row):
                header_row_idx = row_index
                break

    if header_row_idx is None:
        raise ValueError("Structure invalide: colonne Département introuvable dans les lignes 0 à 5.")

    df = df_raw.copy()
    df.columns = df_raw.iloc[header_row_idx].values
    df_data = df_raw.iloc[header_row_idx + 1:].copy()
    positions = find_positions(df.columns)
    if len(positions) != len(aliases):
        raise ValueError("Structure invalide: colonnes Département, Catégorie, Cible, Présences et Écart introuvables.")
    return header_row_idx, df_data, positions


def _number(value: Any) -> float:
    if pd.isna(value) or value == "":
        raise ValueError("valeur numérique manquante")
    if isinstance(value, str):
        value = value.replace(" ", "").replace(",", ".")
    return float(value)


def load_cibles_reference(path: Optional[Union[str, Path]] = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Load the Semaine and Fin de semaine target dictionaries from Cibles.xlsx.

    Raises:
        FileNotFoundError: If the backend Cibles.xlsx workbook cannot be located anywhere in the project.
        ValueError: If the workbook cannot be parsed with the expected layout.
    """
    project_root = _find_project_root()
    cibles_path = Path(path) if path is not None else (_discover_cibles_path(project_root) or CIBLES_XLSX_PATH)

    if not cibles_path.exists():
        diagnostic = _report_missing_cibles(project_root)
        raise FileNotFoundError(diagnostic)

    try:
        # Lecture brute (sans usecols) car le tableau Semaine (A:E) et le tableau Fin de semaine
        # (G:K) partagent des en-têtes identiques sur la même ligne: lire chaque plage séparément
        # avec usecols pousse pandas à dédoublonner les en-têtes (ex: "Catégorie.1", "JOUR.1"),
        # ce qui casse la correspondance de colonnes de quart pour le tableau Fin de semaine.
        df_raw = pd.read_excel(cibles_path, header=None, skiprows=1)
    except Exception as exc:
        raise ValueError(f"Impossible de lire le fichier de référence Cibles.xlsx: {exc}") from exc

    if df_raw.shape[1] < 11:
        raise ValueError(
            "Structure invalide: Cibles.xlsx doit contenir le tableau Semaine (colonnes A:E) "
            "et le tableau Fin de semaine (colonnes G:K)."
        )

    def _build_table(column_slice: slice) -> pd.DataFrame:
        block = df_raw.iloc[:, column_slice].copy()
        block.columns = df_raw.iloc[0, column_slice].values
        block = block.iloc[1:].reset_index(drop=True)
        return block

    df_semaine = _build_table(slice(0, 5))
    df_fin_semaine = _build_table(slice(6, 11))

    df_semaine = _rename_quart_columns(_clean_column_headers(df_semaine).rename(columns=CIBLES_COLUMN_RENAME_MAP))
    df_fin_semaine = _rename_quart_columns(
        _clean_column_headers(df_fin_semaine).rename(columns=CIBLES_COLUMN_RENAME_MAP)
    )

    # Supprime les lignes totalement vides issues d'éventuelles cellules fantômes en fin de plage.
    df_semaine = df_semaine.dropna(how="all").reset_index(drop=True)
    df_fin_semaine = df_fin_semaine.dropna(how="all").reset_index(drop=True)
    return df_semaine, df_fin_semaine


def get_available_quarts(df_semaine: pd.DataFrame, df_fin_semaine: pd.DataFrame) -> list[str]:
    """Return the shift names present in BOTH the Semaine and Fin de semaine tables.

    This keeps the UI's shift selector consistent with the actual Cibles.xlsx content so a
    date range mixing weekdays and weekend days can never land on a quart missing from either table.
    """
    quarts_semaine = {col for col in df_semaine.columns if col not in NON_QUART_COLUMNS}
    quarts_fin_semaine = {col for col in df_fin_semaine.columns if col not in NON_QUART_COLUMNS}
    common = quarts_semaine & quarts_fin_semaine
    preferred_order = ["JOUR", "SOIR", "NUIT"]
    ordered = [quart for quart in preferred_order if quart in common]
    remaining = sorted(common - set(ordered))
    return ordered + remaining


def select_cibles_for_period(
    df_semaine: pd.DataFrame,
    df_fin_semaine: pd.DataFrame,
    date_selection: datetime.date,
    quart_selection: str,
) -> pd.DataFrame:
    """Pick the Semaine or Fin de semaine dictionary based on the weekday and isolate the shift column."""
    is_weekday = date_selection.weekday() < 5
    df_source = df_semaine if is_weekday else df_fin_semaine
    table_label = "Semaine" if is_weekday else "Fin de semaine"

    # Les en-têtes de quart ont déjà été nettoyés (strip + upper) au chargement; on aligne la clé de recherche.
    quart_key = str(quart_selection).strip().upper()
    if quart_key not in df_source.columns:
        quarts_disponibles = sorted(col for col in df_source.columns if col not in NON_QUART_COLUMNS)
        raise ValueError(
            f"Quart '{quart_selection}' introuvable dans le tableau '{table_label}' de Cibles.xlsx "
            f"pour la date {date_selection.isoformat()}. Quarts disponibles dans '{table_label}': "
            f"{quarts_disponibles or 'aucun'}. Vérifiez que ce quart existe dans les DEUX tableaux "
            "(Semaine et Fin de semaine) puisque la période sélectionnée peut mélanger des jours des deux types."
        )

    df_filtre = df_source[["Département", "Catégorie", quart_key]].copy()
    df_filtre = df_filtre.rename(columns={quart_key: "Cible"})
    return df_filtre


def parse_presences_xlsx(uploaded_file) -> pd.DataFrame:
    """Parse the simplified presences workbook (Département, Catégorie, Présences only)."""
    if uploaded_file is None:
        raise ValueError("Aucun fichier de présences fourni.")

    if hasattr(uploaded_file, "seek"):
        uploaded_file.seek(0)
    try:
        df_raw = pd.read_excel(uploaded_file, header=None)
    except Exception as exc:
        raise ValueError(f"Impossible de lire le fichier de présences: {exc}") from exc

    return _parse_presences_sheet(df_raw)


def _parse_presences_sheet(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Normalize and validate the presence table from one workbook sheet."""

    aliases = {
        "Département": {"département", "departement", "department", "unité", "unite", "unité de soins"},
        "Catégorie": {"catégorie", "categorie", "catégorie d'emploi", "emploi", "poste"},
        "Présences": {"présences", "presences", "présence", "presence", "effectif"},
    }

    def find_positions(columns: Any) -> dict[str, int]:
        normalized = [_normalized(cell) for cell in columns]
        positions: dict[str, int] = {}
        for name, accepted in aliases.items():
            for column_index, value in enumerate(normalized):
                if value in accepted or any(alias in value for alias in accepted if len(alias) > 5):
                    positions[name] = column_index
                    break
        return positions

    header_row_idx = None
    for row_index in range(min(6, len(df_raw.index))):
        row = df_raw.iloc[row_index]
        if any("département" in _normalized(value) for value in row):
            header_row_idx = row_index
            break

    if header_row_idx is None:
        raise ValueError("Structure invalide: colonne Département introuvable dans les lignes 0 à 5.")

    headers = [str(value).strip() for value in df_raw.iloc[header_row_idx].values]
    headers = [
        "Catégorie" if header.casefold() == "catégorie d'emploi".casefold() else header
        for header in headers
    ]
    positions = find_positions(headers)
    if len(positions) != len(aliases):
        raise ValueError("Structure invalide: colonnes Département, Catégorie et Présences introuvables.")

    records: list[dict[str, Any]] = []
    for row in df_raw.iloc[header_row_idx + 1:].values.tolist():
        values = {name: row[index] if index < len(row) else None for name, index in positions.items()}
        if all(pd.isna(values[name]) or values[name] == "" for name in positions):
            continue
        if pd.isna(values["Département"]) or pd.isna(values["Catégorie"]):
            continue
        try:
            presence = _number(values["Présences"])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Ligne invalide dans le fichier de présences: {exc}") from exc
        records.append(
            {
                "Département": str(values["Département"]).strip(),
                "Catégorie": str(values["Catégorie"]).strip(),
                "Présences": presence,
            }
        )

    if not records:
        raise ValueError("Aucune ligne de présence exploitable dans le fichier.")

    df_presences = pd.DataFrame(records, columns=["Département", "Catégorie", "Présences"])
    required_cols = ["Département", "Catégorie", "Présences"]
    if not all(column in df_presences.columns for column in required_cols):
        raise ValueError(f"Schéma invalide. Colonnes requises: {required_cols}")
    return df_presences


def build_workforce_report(df_presences: pd.DataFrame, df_cibles_filtrees: pd.DataFrame) -> pd.DataFrame:
    """Merge presences with the filtered targets dictionary and enforce the strict category order."""
    df_final = pd.merge(df_presences, df_cibles_filtrees, on=["Département", "Catégorie"], how="left")
    df_final["Cible"] = df_final["Cible"].fillna(0).astype(int)
    df_final["Écart"] = df_final["Présences"] - df_final["Cible"]
    df_final["Besoins"] = df_final["Écart"].apply(lambda value: abs(value) if value < 0 else 0)
    df_final["Surplus"] = df_final["Écart"].apply(lambda value: value if value > 0 else 0)

    df_final["Catégorie"] = pd.Categorical(df_final["Catégorie"], categories=CATEGORY_ORDER, ordered=True)
    df_final = df_final.sort_values(by=["Département", "Catégorie"]).reset_index(drop=True)
    return df_final


def build_workforce_period_report(
    uploaded_file,
    start_date: datetime.date,
    end_date: datetime.date,
    df_semaine: pd.DataFrame,
    df_fin_semaine: pd.DataFrame,
    quart_selection: str,
) -> pd.DataFrame:
    """Build one chronologically ordered report from one presence sheet per date."""
    if start_date > end_date:
        raise ValueError("La date de début doit être antérieure ou égale à la date de fin.")
    if hasattr(uploaded_file, "seek"):
        uploaded_file.seek(0)
    try:
        worksheets = pd.read_excel(uploaded_file, sheet_name=None, header=None)
    except Exception as exc:
        raise ValueError(f"Impossible de lire les feuilles du fichier de présences: {exc}") from exc

    dates = pd.date_range(start=start_date, end=end_date, freq="D")
    if len(worksheets) != len(dates):
        raise ValueError(
            f"La période contient {len(dates)} jours, mais le classeur contient "
            f"{len(worksheets)} feuilles. Une feuille par jour est requise."
        )

    daily_reports = []
    for current_date, (sheet_name, df_raw) in zip(dates, worksheets.items()):
        df_presences = _parse_presences_sheet(df_raw)
        df_cibles = select_cibles_for_period(
            df_semaine,
            df_fin_semaine,
            current_date.date(),
            quart_selection,
        )
        df_daily = build_workforce_report(df_presences, df_cibles)
        df_daily.insert(0, "Date", current_date.date())
        df_daily.insert(0, "Jour", str(sheet_name))
        daily_reports.append(df_daily)

    df_final = pd.concat(daily_reports, ignore_index=True)
    df_final["Catégorie"] = pd.Categorical(
        df_final["Catégorie"], categories=CATEGORY_ORDER, ordered=True
    )
    return df_final.sort_values(
        by=["Date", "Département", "Catégorie"]
    ).reset_index(drop=True)


def parse_workforce_xlsx(uploaded_file) -> Tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Parse all workbook sheets into needs, surplus, and metadata summaries."""
    if uploaded_file is None:
        raise ValueError("Aucun fichier Excel fourni.")

    uploaded_file.seek(0) if hasattr(uploaded_file, "seek") else None
    try:
        workbook = pd.ExcelFile(uploaded_file)
    except Exception as exc:
        raise ValueError(f"Impossible de lire le fichier Excel: {exc}") from exc

    records: list[dict[str, Any]] = []
    sheets: list[dict[str, Any]] = []
    for sheet_name in workbook.sheet_names:
        df_raw = pd.read_excel(workbook, sheet_name=sheet_name, header=None)
        if df_raw.empty:
            continue
        rows = df_raw.values.tolist()
        metadata = _find_metadata(rows, sheet_name)
        header_index, df_data, positions = _find_table_header(df_raw)
        sheets.append(metadata.copy())
        for row in df_data.values.tolist():
            values = {name: row[index] if index < len(row) else None for name, index in positions.items()}
            if all(pd.isna(values[name]) or values[name] == "" for name in positions):
                continue
            if pd.isna(values["Département"]) or pd.isna(values["Catégorie"]):
                continue
            try:
                target = _number(values["Cible"])
                presence = _number(values["Présences"])
                difference = _number(values["Écart"])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Ligne invalide dans la feuille {sheet_name}: {exc}") from exc
            if difference == 0:
                difference = presence - target
            records.append(
                {
                    **metadata,
                    "Département": str(values["Département"]).strip(),
                    "Catégorie": str(values["Catégorie"]).strip(),
                    "Cible": target,
                    "Présences": presence,
                    "Écart": difference,
                    "Besoins": abs(difference) if difference < 0 else 0,
                    "Surplus": difference if difference > 0 else 0,
                }
            )

    if not records:
        raise ValueError("Aucune ligne d'activité exploitable dans le classeur.")
    frame = pd.DataFrame(records, columns=OUTPUT_COLUMNS)
    df_besoins = frame[frame["Besoins"] > 0].reset_index(drop=True)
    df_surplus = frame[frame["Surplus"] > 0].reset_index(drop=True)
    summary = {
        "feuilles": sheets,
        "lignes_analysees": len(frame),
        "besoins": df_besoins.to_dict(orient="records"),
        "surplus": df_surplus.to_dict(orient="records"),
    }
    return df_besoins, df_surplus, summary


def generate_summary_excel(df_besoins: pd.DataFrame, df_surplus: pd.DataFrame) -> BytesIO:
    """Create a formatted in-memory workbook containing needs and surplus."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_besoins.to_excel(writer, sheet_name="Sommaire Besoins", index=False)
        df_surplus.to_excel(writer, sheet_name="Sommaire Surplus", index=False)
        for sheet_name, color in (("Sommaire Besoins", "FFC7CE"), ("Sommaire Surplus", "C6EFCE")):
            worksheet = writer.book[sheet_name]
            worksheet.freeze_panes = "A2"
            worksheet.auto_filter.ref = worksheet.dimensions
            for cell in worksheet[1]:
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill("solid", fgColor="1F4E78")
            last_row = worksheet.max_row
            if last_row > 1:
                value_column = "I" if sheet_name == "Sommaire Besoins" else "J"
                worksheet.conditional_formatting.add(
                    f"{value_column}2:{value_column}{last_row}",
                    CellIsRule(operator="greaterThan", formula=["0"], fill=PatternFill("solid", fgColor=color)),
                )
            for column in worksheet.columns:
                letter = column[0].column_letter
                width = min(max(len(str(cell.value or "")) for cell in column) + 2, 32)
                worksheet.column_dimensions[letter].width = width
    output.seek(0)
    return output


TOPO_24H_TEMPLATE = """Hôpital Fleury - état des RH 24 h

SOIR

•\t4e étage : Générez un rapport d'effectif sur cette ligne.
•\t7e étage : Générez un rapport d'effectif sur cette ligne.
•\t6e étage : Générez un rapport d'effectif sur cette ligne.
•\t8e étage : Générez un rapport d'effectif sur cette ligne.
•\tUrgence : Générez un rapport d'effectif sur cette ligne.
•\tValider s'il y a débordement sur les unités.
•\tValider s'il y a un service privé sur les étages.
•\tValider s'il y a des équipes volantes à placer.

NUIT

•\t4e étage : Générez un rapport d'effectif sur cette ligne.
•\t7e étage : Générez un rapport d'effectif sur cette ligne.
•\t6e étage : Générez un rapport d'effectif sur cette ligne.
•\t8e étage : Générez un rapport d'effectif sur cette ligne.
•\tUrgence : Générez un rapport d'effectif sur cette ligne.
•\tValider s'il y a débordement sur les unités.
•\tValider s'il y a un service privé sur les étages.
•\tValider s'il y a des équipes volantes à placer.

JOUR

•\t4e étage : Générez un rapport d'effectif sur cette ligne.
•\t7e étage : Générez un rapport d'effectif sur cette ligne.
•\t6e étage : Générez un rapport d'effectif sur cette ligne.
•\t8e étage : Générez un rapport d'effectif sur cette ligne.
•\tUrgence : Générez un rapport d'effectif sur cette ligne.
•\tValider s'il y a débordement sur les unités.
•\tValider s'il y a un service privé sur les étages.
•\tValider s'il y a des équipes volantes à placer."""


def generate_topo_24h(data_summary: str, api_key: Optional[str] = None) -> str:
    """Ask Gemini to fill the strict Topo 24h hospital template from aggregated data.

    Args:
        data_summary: Textual synthesis (or JSON) of the workforce needs/surplus already computed.
        api_key: Optional Google API key override.

    Returns:
        The completed Topo 24h Markdown document, respecting the mandatory template layout.

    Raises:
        RuntimeError: If the Gemini call fails or returns an unusable response.
    """
    if not data_summary or not isinstance(data_summary, str) or not data_summary.strip():
        raise RuntimeError("Topo 24h impossible: aucune donnée d'effectif disponible.")

    system_instruction = (
        "Tu es un générateur de topo RH hospitalier. Tu dois reproduire EXACTEMENT le gabarit Markdown fourni, "
        "sans en modifier la structure, les titres de quarts (SOIR, NUIT, JOUR), les puces ni leur ordre. "
        "Pour chaque ligne contenant la mention « Générez un rapport d'effectif sur cette ligne. », remplace "
        "uniquement cette mention par une synthèse concise (une phrase courte) de l'effectif présent, de la cible "
        "et de l'écart calculé pour l'unité et le quart concernés, en te basant strictement sur les données fournies. "
        "Si aucune donnée n'est disponible pour une unité/quart donné, indique « Aucune donnée disponible pour ce quart. » "
        "Ne fabrique aucun chiffre. Conserve les lignes de validation (débordement, service privé, équipes volantes) "
        "telles quelles ou complète-les brièvement si les données le permettent. Retourne uniquement le document Markdown final, "
        "sans commentaire ni bloc de code additionnel.\n\n"
        f"Gabarit à respecter:\n{TOPO_24H_TEMPLATE}"
    )

    try:
        summarizer = GoogleGeminiSummarizer(api_key=api_key or os.getenv("GOOGLE_API_KEY"))
        return summarizer.summarize(
            f"Données agrégées de gestion des activités de remplacement:\n{data_summary}",
            max_output_tokens=1500,
            system_instruction=system_instruction,
        )
    except Exception as exc:
        raise RuntimeError(f"Génération du Topo 24h impossible: {exc}") from exc


def query_gemini_analysis(data_summary: dict, user_prompt: str = "", api_key: Optional[str] = None) -> str:
    """Ask Gemini for an executive workforce report based only on aggregated data."""
    if not isinstance(data_summary, dict) or not data_summary.get("lignes_analysees"):
        raise ValueError("Le contexte d'analyse est vide ou invalide.")
    default_instruction = (
        "Produis un rapport exécutif Markdown en français. Identifie les départements sous-effectifs "
        "critiques par quart, compare les ratios de couverture par catégorie (Inf, Aux, PAB, AA), "
        "et recommande des compensations entre unités en surplus et en besoin. Cite les chiffres fournis "
        "et ne fabrique aucune donnée."
    )
    instruction = user_prompt.strip() if isinstance(user_prompt, str) and user_prompt.strip() else default_instruction
    context = json.dumps(data_summary, ensure_ascii=False, default=str, indent=2)
    try:
        summarizer = GoogleGeminiSummarizer(api_key=api_key or os.getenv("GOOGLE_API_KEY"))
        return summarizer.summarize(
            f"Données agrégées de gestion des activités de remplacement:\n{context}",
            max_output_tokens=1200,
            system_instruction=instruction,
        )
    except Exception as exc:
        raise RuntimeError(f"Analyse Gemini impossible: {exc}") from exc
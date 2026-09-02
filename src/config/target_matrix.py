"""Fixed staffing targets transcribed from Cible.xlsx."""

CATEGORY_ORDER = ("Inf", "Aux", "PAB", "AA")

TARGET_MATRIX = {
    "4e": {"Jour": (3, 2, 3, 1), "Soir": (3, 2, 2, 1), "Nuit": (2, 1, 1, 0)},
    "7e": {"Jour": (3, 2, 3, 1), "Soir": (3, 1, 2, 1), "Nuit": (2, 0, 2, 0)},
    "6e": {"Jour": (4, 2, 3, 1), "Soir": (3, 2, 2, 1), "Nuit": (2, 2, 2, 0)},
    "8e": {"Jour": (3, 2, 3, 1), "Soir": (3, 2, 2, 1), "Nuit": (2, 2, 2, 0)},
    "SIC": {"Jour": (5, 0, 1, 0), "Soir": (4, 0, 1, 0), "Nuit": (4, 0, 0, 0)},
    "CDJ": {"Jour": (2, 1, 1, 1), "Soir": (1, 1, 0, 0), "Nuit": (0, 0, 0, 0)},
    "URG": {"Jour": (10, 1, 2, 2), "Soir": (9, 1, 3, 2), "Nuit": (7, 1, 2, 1)},
    "ECG": {"Jour": (0, 0, 1, 0), "Soir": (0, 0, 1, 0), "Nuit": (0, 0, 1, 0)},
    "ACUR/GDL": {"Jour": (0, 0, 0, 2), "Soir": (0, 0, 0, 2), "Nuit": (0, 0, 0, 1)},
}
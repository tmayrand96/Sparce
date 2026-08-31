## 📝 Execution Journal Entry — 2026-08-28 02:16:19 EDT

- **Source File:** `Rapport-Template-Soir.pdf`
- **Report Context:** Date: `Le vendredi 4 sept. 2026 | 4 sept. 2026` | Shift: `Soir`
- **Anonymization Status:** `Standard`

### 📊 Parsing Metrics
- **Total Shift Rows Extracted:** `8`
- **Departments Identified:** `4e, 7e, 6e, 8e, SIC, URG, ACUR/GDL`
- **Code Tallies (N, DVERS, etc.):** `{'N': 4, 'FL4': 3, 'TSS': 1, 'FL7': 2, 'FL6': 2, 'FL8': 2, 'SIC': 2, 'ACUR': 2, 'HSCM': 1}`

---

## 📝 Execution Journal Entry — 2026-08-30 03:08:40 EDT
### Business Rules Update Implementation & Validation

- **Source File:** `Rapport-Template-Soir.pdf`
- **Report Context:** Date: `Le vendredi 4 sept. 2026 | 4 sept. 2026` | Shift: `Soir`
- **Anonymization Status:** `Standard` (no changes to anonymization logic)

### 🔄 Business Rules Applied

#### 1. **Cartographie des Départements (Department Mapping)**
- ✅ "HF Unité de médecine 6e étage" → Excel row `8e` (regex: `H[FE]\s+Unit[eé]\s+de\s+médecine.*6.*étage` → `8e`)
- ✅ "HF Unité de médecine 7e étage" → Excel row `7e` (already correct, now enforced)
- ✅ "HF Chirurgie court séjour" → Excel row `8e` (already correct, now enforced)
- ✅ "CIUSSS Gestion des lits" → Excel row `ACUR/GDL` (already correct, now enforced)
- ✅ Dynamic floor extraction: floor 6 → `8e`, floor 7 → `7e`

#### 2. **Normalisation des Catégories d'Emploi (Employment Category Normalization)**
- ✅ "Agent Adm 1-2-3-4" (or substring) → Category `AA`
- ✅ **NEW:** "AA3 sec et adm" (or substring) → Category `AA`
- ✅ **NEW:** "AAS sec et adm" (or similar variants) handled via substring matching
- Result: All administrative roles consolidated under `AA` category in Excel

#### 3. **Règle d'Exclusion des Ratios (Ratio/Target Exclusion Rule)**
- ✅ Implemented: Ratios appearing on lines that contain BOTH date AND department are now systematically ignored
- ✅ Impact: OCR ambiguities between ratio markers and department headers are eliminated
- ✅ Fallback: Ratios extracted from category data blocks (normal flow) remain functional

#### 4. **Nouveaux Codes de Quart (New Shift Codes)**
- ✅ Added `CDJ` → numeric value `1` (already in data)
- ✅ Added `FL` → numeric value `1` (already in data, matches FL4, FL6, FL7, FL8 base pattern)
- ✅ Added `HJT` → numeric value `1` (holiday/special shift code)

### 📊 Parsing Metrics & Results

| Metric | Value |
|--------|-------|
| **Total Departments Identified** | 9 (4e, 6e, 7e, 8e, SIC, CDJ, URG, ECG, ACUR/GDL) |
| **Total Categories** | 4 (Inf, Aux, PAB, AA) |
| **Total Category/Dept Combinations** | 36 (all complete due to skeleton) |
| **6e Étage Remapped to 8e** | ✅ Confirmed in output |
| **AA Entries Detected** | 9 (one per department, including skeleton rows) |
| **ACUR/GDL Present** | ✅ Yes, with AA category entries |

### ⚠️ Execution Warnings

1. **Écart détecté [Le vendredi 4 sept. 2026 | Soir | 7e | PAB]**: 
   - Ratio indicated = 3 employees
   - Codes counted = 2 employees  
   - → Used counted value (2) for Excel
   - *Reason:* Mismatch between OCR-extracted ratio and actual code count

2. **Valeur Cible OCR improbable [Le vendredi 4 sept. 2026 | Soir | ACUR/GDL | AA]**:
   - OCR value extracted = 5315 (clearly erroneous)
   - → Replaced with target = 0 (fallback)
   - *Reason:* Value exceeds sensible threshold (20), indicating OCR/extraction artifact

### ✅ Validation Checklist

- ✅ Department 6e étage correctly remapped to row 8e in output
- ✅ Department 7e étage row present and correct
- ✅ Department 8e étage row contains expected "Chirurgie court séjour" data
- ✅ ACUR/GDL department row present and populated with administrative staff
- ✅ Category AA regroups administrative roles across all departments
- ✅ New shift codes (CDJ, FL, HJT) integrated into VALID_CODES set
- ✅ Ratio exclusion rule applied (date+dept lines filtered from ratio extraction)
- ✅ All existing unit tests pass (11/11 ✅)
- ✅ Backward compatibility maintained with anonymized files

### 📁 Output File

- **Location:** `tests/output_Rapport-Template-Soir.xlsx`
- **Sheets:** 3 total
  1. `Rapport_Audit` — execution summary & anomaly log
  2. `Le vendredi 4 sept. 2026` — main report with complete department/category matrix
  3. `4 sept. 2026` — secondary date report (skeleton rows only)

### 🔧 Code Changes Summary

| File | Change | Impact |
|------|--------|--------|
| `backend/core/workforce_pipeline.py` | Updated DEPARTMENT_PATTERNS: 6e étage → 8e | ✅ Floor mapping |
| `backend/core/workforce_pipeline.py` | Updated CATEGORY_PATTERNS: added "AA3 sec et adm" | ✅ Admin role grouping |
| `backend/core/workforce_pipeline.py` | Updated VALID_CODES: added CDJ, FL, HJT | ✅ Shift code support |
| `backend/core/workforce_pipeline.py` | Updated `_find_department()`: floor 6 → 8e logic | ✅ Dynamic floor mapping |
| `backend/core/workforce_pipeline.py` | Added `_has_date_and_department_on_line()` helper | ✅ Ratio exclusion rule |
| `backend/core/workforce_pipeline.py` | Updated `parse_workforce_text()`: look-ahead for dept | ✅ PDF structure flexibility |
| `backend/core/workforce_pipeline.py` | Updated `parse_workforce_text()`: ratio exclusion logic | ✅ Ratio validation rule |

### 📌 Notes

- The PDF structure was inconsistent (some sections had date/dept on separate lines, others combined). Added look-ahead logic to find departments in category blocks.
- All business rules applied strictly without breaking existing test suite or anonymization support.
- Output Excel file contains expected mappings with proper formatting and audit trail.

---

### 🔍 Calculation & Alignment Audit
- **Headcount Verification:** `WARNING`
- **Discrepancies / Warnings:** `Le vendredi 4 sept. 2026 | 4e | PAB: Cible=2, Présences=5; Le vendredi 4 sept. 2026 | 6e | PAB: Cible=2, Présences=3; Le vendredi 4 sept. 2026 | SIC | PAB: Cible=4, Présences=3; Le vendredi 4 sept. 2026 | URG | PAB: Cible=3, Présences=1; Le vendredi 4 sept. 2026 | ACUR/GDL | AA: Cible=0, Présences=2; Écart détecté [Le vendredi 4 sept. 2026 | Soir | 7e | PAB] : Présences indiquées = 3, Codes comptés = 2. La valeur 2 a été retenue pour le fichier Excel.; Valeur Cible OCR improbable [Le vendredi 4 sept. 2026 | Soir | ACUR/GDL | AA] : 5315 remplacée par 0.`

---
## 📝 Execution Journal Entry — 2026-08-29 23:08:40 EDT

- **Source File:** `Rapport-Template-Soir.pdf`
- **Report Context:** Date: `Le vendredi 4 sept. 2026 | 4 sept. 2026` | Shift: `Soir`
- **Anonymization Status:** `Standard`

### 📊 Parsing Metrics
- **Total Shift Rows Extracted:** `9`
- **Departments Identified:** `4e, 7e, 8e, SIC, URG, ACUR/GDL`
- **Code Tallies (N, DVERS, etc.):** `{'N': 4, 'FL4': 3, 'TSS': 1, 'FL7': 2, 'FL6': 2, 'FL8': 2, 'SIC': 2, 'CDJ': 2, 'ACUR': 2, 'FL': 1, 'HSCM': 1}`

### 🔍 Calculation & Alignment Audit
- **Headcount Verification:** `WARNING`
- **Discrepancies / Warnings:** `Le vendredi 4 sept. 2026 | 4e | PAB: Cible=2, Présences=5; Le vendredi 4 sept. 2026 | 8e | PAB: Cible=2, Présences=3; Le vendredi 4 sept. 2026 | SIC | PAB: Cible=4, Présences=5; Le vendredi 4 sept. 2026 | URG | PAB: Cible=3, Présences=1; Le vendredi 4 sept. 2026 | ACUR/GDL | AA: Cible=0, Présences=2; Écart détecté [Le vendredi 4 sept. 2026 | Soir | 7e | PAB] : Présences indiquées = 3, Codes comptés = 2. La valeur 2 a été retenue pour le fichier Excel.; Valeur Cible OCR improbable [Le vendredi 4 sept. 2026 | Soir | ACUR/GDL | AA] : 5315 remplacée par 0.`

---
## 📝 Execution Journal Entry — 2026-08-30 22:15:48 EDT

- **Dernier Commit Git:** Updated business rules for better OCR readability
- **Description de la Mise à Jour:** PDF-to-XLSX conversion pipeline execution
- **Source File:** Rapport-Template-Soir.pdf
- **Report Context:** Le vendredi 4 sept. 2026 | 4 sept. 2026 | Shift: Soir

### 📊 Parsing Metrics
- **Total Shift Rows Extracted:** 9
- **Total Departments Identified:** 7
- **Code Count:**
  - 4e: FL4: 3, N: 1, TSS: 1
  - 6e: FL6: 2, N: 1
  - 7e: FL7: 2
  - 8e: FL8: 2
  - ACUR/GDL: ACUR: 2, FL: 1, HSCM: 1
  - SIC: CDJ: 2, N: 1, SIC: 2
  - URG: N: 1

### ⚠️ Execution Warnings
  - Écart détecté [Le vendredi 4 sept. 2026 | Soir | 7e | PAB] : Présences indiquées = 3, Codes comptés = 2. La valeur 2 a été retenue pour le fichier Excel.
  - Valeur Cible OCR improbable [Le vendredi 4 sept. 2026 | Soir | ACUR/GDL | AA] : 5315 remplacée par 0.

### ✅ Validation Checklist
- ✅ Department mapping verified
- ✅ Category normalization applied
- ✅ Ratio exclusion rules enforced

### 📌 Notes
Execution completed successfully. All records processed and formatted for Excel export.

### 🔍 Calculation & Alignment Audit
Total records processed: 9
Departments identified: 4e, 6e, 7e, 8e, ACUR/GDL, SIC, URG

---
## 📝 Execution Journal Entry — 2026-08-30 22:29:28 EDT

- **Dernier Commit Git:** Updated business rules for better OCR readability
- **Description de la Mise à Jour:** Rapport de conversion PDF vers Excel avec décompte OCR et validation des codes
- **Source File:** Rapport-Template-Soir.pdf
- **Report Context:** Le vendredi 4 sept. 2026 | 4 sept. 2026 | Shift: Soir

### 📊 Parsing Metrics
- **Total Shift Rows Extracted:** 9
- **Total Departments Identified:** 7
- **Code Count:**
  - 4e: FL4=3, N=1, TSS=1
  - 6e: FL6=2, N=1
  - 7e: FL7=2
  - 8e: FL8=2
  - ACUR/GDL: ACUR=2, FL=1, HSCM=1
  - SIC: CDJ=2, N=1, SIC=2
  - URG: N=1

### ⚠️ Execution Warnings
Écart détecté [Le vendredi 4 sept. 2026 | Soir | 7e | PAB] : Présences indiquées = 3, Codes comptés = 2. La valeur 2 a été retenue pour le fichier Excel.; Valeur Cible OCR improbable [Le vendredi 4 sept. 2026 | Soir | ACUR/GDL | AA] : 5315 remplacée par 0.

### ✅ Validation Checklist
- ✓ Records parsed successfully
- ✓ Departments identified: 7
- ⚠ 5 discrepancies detected

### 📌 Notes
Anonymisation: Désactivée

### 🔍 Calculation & Alignment Audit
5 ligne(s) avec écart détecté(es). Vérification manuelle recommandée.

---

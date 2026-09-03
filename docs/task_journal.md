## Correctif de robustesse MODE B - 2026-09-03

- L'état actif du parseur (date, département et catégorie) est conservé entre les pages. Les bannières de date, en-têtes, pieds de page et numéros de page ne ferment pas prématurément un bloc.
- L'ancre OCR du `6e` accepte les variantes de casse, d'espacement et les caractères parasites autour de `HF Unité de médecine 6e`.
- `ACUR/GDL` fusionne les présences `AA` des ancres `HF Accueil et réception` et `CIUSSS Gestion des lits`.
- Chaque occurrence de `HOR12` et de `TRANS` soustrait une présence, pour toutes les catégories et tous les départements. L'écart reste numérique; aucun suffixe `+HOR12` n'est ajouté.
- Validation exécutée sur `tests/Rapport-Template-Soir.pdf`, avec contrôle des blocs `6e`, `7e`, `8e`, `ACUR/GDL` et des codes exclus.

## Itération TDD Gold Standard MODE A - 2026-09-03

- **Harness ajouté :** `tests/test_pipeline_accuracy.py` découvre automatiquement les paires `Rapport-A-<jour>-<quart>.pdf` / `Target-Etalon-<jour>-<quart>.xlsx`, compare `Cible`, `Présences` et `Écart (Décompte vs Cible)`, puis affiche les seuls écarts classés.
- **Étalons versionnés disponibles :** 4 et 5 septembre uniquement. Aucun couple PDF/XLSX pour les 6 et 7 septembre n'est présent dans `tests/` à cette date.

| Jour | Avant correctifs | Après correctifs |
| --- | --- | --- |
| 4 septembre | 100,0 % (108/108) | 100,0 % (108/108) |
| 5 septembre | Non calculable : `Département introuvable` | 74,1 % (80/108) |
| Global disponible | Non calculable | 87,0 % (188/216) |

- **Correctifs appliqués :** les catégories en tête de page peuvent retrouver un service grâce à un code de service unique du même bloc; les lignes de pied de page OCR (`imprimé le`, y compris les variantes tronquées) ne créent plus de dates ni de feuilles fantômes.
- **Règle métier :** `src/aggregator/targets.py` force toutes les cibles CDJ (`Inf`, `Aux`, `PAB`, `AA`) à `0` le samedi ou le dimanche, selon le jour OCR ou la date dérivée.
- **Résidu constaté :** les écarts du 5 septembre proviennent de colonnes OCR dissociées sans ancre de département exploitable. Ils restent visibles dans la matrice du harness plutôt que d'être imputés à une catégorie par une valeur codée en dur.

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
## 📝 Execution Journal Entry — 2026-08-31 19:44:32 EDT

- **Dernier Commit Git:** Update to perfect code count + other fixes
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
- ⚠ 4 discrepancies detected

### 📌 Notes
Anonymisation: Désactivée

### 🔍 Calculation & Alignment Audit
4 ligne(s) avec écart détecté(es). Vérification manuelle recommandée.

---

## Validation du décompte des présences par lignes physiques - 2026-09-01

- **Rapport exécuté :** `tests/Rapport-Template-Soir.pdf` | **Quart :** `Soir`
- Le rapport contient des identifiants d'employés et a été validé comme cas non anonymisé disponible dans le dépôt.
- `Présences` est désormais le nombre de lignes de données structurées dans chaque section (valeurs `TE`, horaires, repas, numéro de poste ou code), y compris lorsqu'un employé est absent de la ligne.

---

## Alignement Gold Standard - 2026-09-01

- **Source :** `tests/Rapport-Template-Soir.pdf` | **Cible :** `tests/Rapport-Target-Soir.xlsx` | **Quart :** `Soir`
- **Deltas initiaux :** les en-têtes multi-colonnes du texte natif séparaient les valeurs d'entrée et de sortie d'une même personne, fusionnaient plusieurs catégories et créaient un second onglet pour la date répétée `4 sept. 2026`.
- **Corrections appliquées :** normalisation insensible aux accents des ancres OCR; reconnaissance des variantes de départements (`HE`, `MF`, `PBM`, `PEM`); détection des catégories à partir des identifiants d'emploi; décompte par projection de colonne pour ne pas compter deux fois une même personne; maintien de la date complète comme date canonique.
- **Résultat de l'audit :** toutes les paires Département/Catégorie sont à présent détectées, et les présences sont récupérées sauf les exceptions de règles d'affaires à confirmer.
- **Point bloquant pour une correspondance à 100 % :** l'OCR image ordonné lit `URG/PAB = 2/4` et `SIC/PAB = 4/2`, alors que le Gold Standard demande respectivement `3/4` et `1/2`. Aucune règle métier du dépôt ne permet d'inférer ces cibles; les imposer reviendrait à coder en dur des valeurs du fichier étalon.
- La valeur sémantique du `Code` ne détermine plus le décompte; les codes `HOR12` et `TRANS` servent uniquement à appliquer leurs soustractions métier.
- Les en-têtes de tableau et les lignes de date sont exclus du comptage.
- Le classeur généré conserve les cinq colonnes prescrites et chaque `Écart (Décompte vs Cible)` a été vérifié comme `Présences - Cible`.
- Aucun rapport anonymisé distinct n'est versionné dans le dépôt; la validation complémentaire nécessitera un PDF anonymisé fourni ultérieurement.

---

## Validation de la structure Cible / Présences / Écart - 2026-08-31

- **Source validée :** `tests/Rapport-Template-Soir.pdf` | **Quart :** `Soir`
- Le pipeline a généré `tests/output_Rapport-Template-Soir.xlsx` sans erreur.
- Les seules colonnes de chaque feuille de rapport sont : `Département`, `Catégorie`, `Cible`, `Présences` et `Écart (Décompte vs Cible)`.
- La colonne redondante `Écart (Présences vs Cible)` est absente du classeur.
- Les cibles AA Soir ont été validées contre la grille de référence : `4e=1`, `7e=1`, `6e=1`, `8e=1`, `SIC=0`, `CDJ=0`, `URG=2`, `ECG=0`, `ACUR/GDL=2`.
- Les présences proviennent du décompte des codes reconnus; chaque écart est calculé par `Présences - Cible`.

---
## 📝 Execution Journal Entry — 2026-08-31 20:58:19 EDT

- **Dernier Commit Git:** Update: Optimization of the count
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
Valeur Cible OCR improbable [Le vendredi 4 sept. 2026 | Soir | ACUR/GDL | AA] : 5315 remplacée par 0.

### ✅ Validation Checklist
- ✓ Records parsed successfully
- ✓ Departments identified: 7
- ⚠ 6 discrepancies detected

### 📌 Notes
Anonymisation: Désactivée

### 🔍 Calculation & Alignment Audit
6 ligne(s) avec écart détecté(es). Vérification manuelle recommandée.

---
## 📝 Execution Journal Entry — 2026-08-31 21:00:01 EDT

- **Dernier Commit Git:** Update: Optimization of the count
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
Valeur Cible OCR improbable [Le vendredi 4 sept. 2026 | Soir | ACUR/GDL | AA] : 5315 remplacée par 0.

### ✅ Validation Checklist
- ✓ Records parsed successfully
- ✓ Departments identified: 7
- ⚠ 5 discrepancies detected

### 📌 Notes
Anonymisation: Désactivée

### 🔍 Calculation & Alignment Audit
5 ligne(s) avec écart détecté(es). Vérification manuelle recommandée.

---
## 📝 Execution Journal Entry — 2026-08-31 21:50:45 EDT

- **Dernier Commit Git:** Added Target values XLSX report (anonymized) - SOIR 4 Sept. 2026
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
Valeur Cible OCR improbable [Le vendredi 4 sept. 2026 | Soir | ACUR/GDL | AA] : 5315 remplacée par 0.

### ✅ Validation Checklist
- ✓ Records parsed successfully
- ✓ Departments identified: 7
- ⚠ 5 discrepancies detected

### 📌 Notes
Anonymisation: Désactivée

### 🔍 Calculation & Alignment Audit
5 ligne(s) avec écart détecté(es). Vérification manuelle recommandée.

---
## 📝 Execution Journal Entry — 2026-08-31 21:53:26 EDT

- **Dernier Commit Git:** Added Target values XLSX report (anonymized) - SOIR 4 Sept. 2026
- **Description de la Mise à Jour:** Rapport de conversion PDF vers Excel avec décompte OCR et validation des codes
- **Source File:** Rapport-Template-Soir.pdf
- **Report Context:** Le vendredi 4 sept. 2026 | Shift: Soir

### 📊 Parsing Metrics
- **Total Shift Rows Extracted:** 22
- **Total Departments Identified:** 9
- **Code Count:**
  - 4e: AIC=1, FL4=5, N=1, TSS=1
  - 6e: AIC=1, FL6=7, N=1
  - 7e: AIC=1, FL=1, FL7=4
  - 8e: FL8=5
  - ACUR/GDL: ACUR=2, FL=1, HSCM=1
  - CDJ: CDJ=1
  - ECG: N=1
  - SIC: AIC=1, N=1, SIC=5
  - URG: BRAN=1, S=1

### ⚠️ Execution Warnings
Valeur Cible OCR improbable [Le vendredi 4 sept. 2026 | Soir | 4e | Aux] : 22 remplacée par 0.; Valeur Cible OCR improbable [Le vendredi 4 sept. 2026 | Soir | 6e | AA] : 5317 remplacée par 0.; Valeur Cible OCR improbable [Le vendredi 4 sept. 2026 | Soir | 8e | AA] : 5317 remplacée par 0.; Valeur Cible OCR improbable [Le vendredi 4 sept. 2026 | Soir | 8e | Aux] : 202 remplacée par 0.; Valeur Cible OCR improbable [Le vendredi 4 sept. 2026 | Soir | ACUR/GDL | AA] : 5315 remplacée par 0.

### ✅ Validation Checklist
- ✓ Records parsed successfully
- ✓ Departments identified: 9
- ⚠ 14 discrepancies detected

### 📌 Notes
Anonymisation: Désactivée

### 🔍 Calculation & Alignment Audit
14 ligne(s) avec écart détecté(es). Vérification manuelle recommandée.

---
## 📝 Execution Journal Entry — 2026-08-31 21:56:47 EDT

- **Dernier Commit Git:** Added Target values XLSX report (anonymized) - SOIR 4 Sept. 2026
- **Description de la Mise à Jour:** Rapport de conversion PDF vers Excel avec décompte OCR et validation des codes
- **Source File:** Rapport-Template-Soir.pdf
- **Report Context:** Le vendredi 4 sept. 2026 | Shift: Soir

### 📊 Parsing Metrics
- **Total Shift Rows Extracted:** 22
- **Total Departments Identified:** 9
- **Code Count:**
  - 4e: AIC=1, FL4=5, N=1, TSS=1
  - 6e: AIC=1, FL6=7, N=1
  - 7e: AIC=1, FL=1, FL7=4
  - 8e: FL8=5
  - ACUR/GDL: ACUR=2, FL=1, HSCM=1
  - CDJ: CDJ=1
  - ECG: N=1
  - SIC: AIC=1, N=1, SIC=5
  - URG: BRAN=1, S=1

### ⚠️ Execution Warnings
Valeur Cible OCR improbable [Le vendredi 4 sept. 2026 | Soir | 4e | Aux] : 22 remplacée par 0.; Valeur Cible OCR improbable [Le vendredi 4 sept. 2026 | Soir | 6e | AA] : 5317 remplacée par 0.; Valeur Cible OCR improbable [Le vendredi 4 sept. 2026 | Soir | 8e | AA] : 5317 remplacée par 0.; Valeur Cible OCR improbable [Le vendredi 4 sept. 2026 | Soir | 8e | Aux] : 202 remplacée par 0.; Valeur Cible OCR improbable [Le vendredi 4 sept. 2026 | Soir | ACUR/GDL | AA] : 5315 remplacée par 0.

### ✅ Validation Checklist
- ✓ Records parsed successfully
- ✓ Departments identified: 9
- ⚠ 14 discrepancies detected

### 📌 Notes
Anonymisation: Désactivée

### 🔍 Calculation & Alignment Audit
14 ligne(s) avec écart détecté(es). Vérification manuelle recommandée.

---
## 📝 Execution Journal Entry — 2026-08-31 21:58:18 EDT

- **Dernier Commit Git:** Added Target values XLSX report (anonymized) - SOIR 4 Sept. 2026
- **Description de la Mise à Jour:** Rapport de conversion PDF vers Excel avec décompte OCR et validation des codes
- **Source File:** Rapport-Template-Soir.pdf
- **Report Context:** Le vendredi 4 sept. 2026 | Shift: Soir

### 📊 Parsing Metrics
- **Total Shift Rows Extracted:** 27
- **Total Departments Identified:** 9
- **Code Count:**
  - 4e: AIC=1, FL4=5, N=1, TSS=1
  - 6e: AIC=1, FL6=7, N=1
  - 7e: AIC=1, FL=1, FL7=5
  - 8e: FL8=5
  - ACUR/GDL: ACUR=2, FL=1, HSCM=1
  - CDJ: CDJ=2
  - ECG: N=1
  - SIC: AIC=1, N=1, SIC=5
  - URG: AIC=1, BRAN=1, CHOC=1, HOR12=1, MON=2, N=1, S=3, TRI=2, URG=1

### ⚠️ Execution Warnings
Valeur Cible OCR improbable [Le vendredi 4 sept. 2026 | Soir | 4e | Aux] : 22 remplacée par 0.; Valeur Cible OCR improbable [Le vendredi 4 sept. 2026 | Soir | 7e | AA] : 23 remplacée par 0.; Valeur Cible OCR improbable [Le vendredi 4 sept. 2026 | Soir | 6e | AA] : 5317 remplacée par 0.; Valeur Cible OCR improbable [Le vendredi 4 sept. 2026 | Soir | 8e | AA] : 5317 remplacée par 0.; Valeur Cible OCR improbable [Le vendredi 4 sept. 2026 | Soir | 8e | Aux] : 202 remplacée par 0.; Valeur Cible OCR improbable [Le vendredi 4 sept. 2026 | Soir | ACUR/GDL | AA] : 5315 remplacée par 0.

### ✅ Validation Checklist
- ✓ Records parsed successfully
- ✓ Departments identified: 9
- ⚠ 12 discrepancies detected

### 📌 Notes
Anonymisation: Désactivée

### 🔍 Calculation & Alignment Audit
12 ligne(s) avec écart détecté(es). Vérification manuelle recommandée.

---
## 📝 Execution Journal Entry — 2026-09-01 18:40:00 EDT

- **Dernier Commit Git:** Imitation Strategy With Target Values
- **Description de la Mise à Jour:** Rapport de conversion PDF vers Excel avec décompte OCR et validation des codes
- **Source File:** Rapport-Template-Soir.pdf
- **Report Context:** Le vendredi 4 sept. 2026 | Shift: Soir

### 📊 Parsing Metrics
- **Total Shift Rows Extracted:** 27
- **Total Departments Identified:** 9
- **Code Count:**
  - 4e: AIC=1, FL4=5, N=1, TSS=1
  - 6e: AIC=1, FL6=7, N=1
  - 7e: AIC=1, FL=1, FL7=5
  - 8e: FL8=5
  - ACUR/GDL: ACUR=2, FL=1, HSCM=1
  - CDJ: CDJ=2
  - ECG: N=1
  - SIC: AIC=1, N=1, SIC=5
  - URG: AIC=1, BRAN=1, CHOC=1, HOR12=1, MON=2, N=1, S=3, TRI=2, URG=1

### ⚠️ Execution Warnings
Valeur Cible OCR improbable [Le vendredi 4 sept. 2026 | Soir | 4e | Aux] : 22 remplacée par 0.; Valeur Cible OCR improbable [Le vendredi 4 sept. 2026 | Soir | 7e | AA] : 23 remplacée par 0.; Valeur Cible OCR improbable [Le vendredi 4 sept. 2026 | Soir | 6e | AA] : 5317 remplacée par 0.; Valeur Cible OCR improbable [Le vendredi 4 sept. 2026 | Soir | 8e | AA] : 5317 remplacée par 0.; Valeur Cible OCR improbable [Le vendredi 4 sept. 2026 | Soir | 8e | Aux] : 202 remplacée par 0.; Valeur Cible OCR improbable [Le vendredi 4 sept. 2026 | Soir | ACUR/GDL | AA] : 5315 remplacée par 0.

### ✅ Validation Checklist
- ✓ Records parsed successfully
- ✓ Departments identified: 9
- ⚠ 12 discrepancies detected

### 📌 Notes
Anonymisation: Désactivée

### 🔍 Calculation & Alignment Audit
12 ligne(s) avec écart détecté(es). Vérification manuelle recommandée.

---
## 📝 Execution Journal Entry — 2026-09-01 18:40:39 EDT

- **Dernier Commit Git:** Imitation Strategy With Target Values
- **Description de la Mise à Jour:** Rapport de conversion PDF vers Excel avec décompte OCR et validation des codes
- **Source File:** Rapport-Template-Soir.pdf
- **Report Context:** Le vendredi 4 sept. 2026 | Shift: Soir

### 📊 Parsing Metrics
- **Total Shift Rows Extracted:** 27
- **Total Departments Identified:** 9
- **Code Count:**
  - 4e: AIC=1, FL4=5, N=1, TSS=1
  - 6e: AIC=1, FL6=7, N=1
  - 7e: AIC=1, FL=1, FL7=5
  - 8e: FL8=5
  - ACUR/GDL: ACUR=2, FL=1, HSCM=1
  - CDJ: CDJ=2
  - ECG: N=1
  - SIC: AIC=1, N=1, SIC=5
  - URG: AIC=1, BRAN=1, CHOC=1, HOR12=1, MON=2, N=1, S=3, TRI=2, URG=1

### ⚠️ Execution Warnings
Valeur Cible OCR improbable [Le vendredi 4 sept. 2026 | Soir | 4e | Aux] : 22 remplacée par 0.; Valeur Cible OCR improbable [Le vendredi 4 sept. 2026 | Soir | 7e | AA] : 23 remplacée par 0.; Valeur Cible OCR improbable [Le vendredi 4 sept. 2026 | Soir | 6e | AA] : 5317 remplacée par 0.; Valeur Cible OCR improbable [Le vendredi 4 sept. 2026 | Soir | 8e | AA] : 5317 remplacée par 0.; Valeur Cible OCR improbable [Le vendredi 4 sept. 2026 | Soir | 8e | Aux] : 202 remplacée par 0.; Valeur Cible OCR improbable [Le vendredi 4 sept. 2026 | Soir | ACUR/GDL | AA] : 5315 remplacée par 0.

### ✅ Validation Checklist
- ✓ Records parsed successfully
- ✓ Departments identified: 9
- ⚠ 12 discrepancies detected

### 📌 Notes
Anonymisation: Désactivée

### 🔍 Calculation & Alignment Audit
12 ligne(s) avec écart détecté(es). Vérification manuelle recommandée.

---
## 📝 Execution Journal Entry — 2026-09-01 18:46:43 EDT

- **Dernier Commit Git:** Imitation Strategy With Target Values
- **Description de la Mise à Jour:** Rapport de conversion PDF vers Excel avec décompte OCR et validation des codes
- **Source File:** Rapport-Template-Soir.pdf
- **Report Context:** Le vendredi 4 sept. 2026 | Shift: Soir

### 📊 Parsing Metrics
- **Total Shift Rows Extracted:** 27
- **Total Departments Identified:** 9
- **Code Count:**
  - 4e: AIC=1, FL4=5, N=1, TSS=1
  - 6e: AIC=1, FL6=7, N=1
  - 7e: AIC=1, FL=1, FL7=5
  - 8e: FL8=5
  - ACUR/GDL: ACUR=2, FL=1, HSCM=1
  - CDJ: CDJ=2
  - ECG: N=1
  - SIC: AIC=1, N=1, SIC=5
  - URG: AIC=1, BRAN=1, CHOC=1, HOR12=1, MON=2, N=1, S=3, TRI=2, URG=1

### ⚠️ Execution Warnings
Valeur Cible OCR improbable [Le vendredi 4 sept. 2026 | Soir | 4e | Aux] : 22 remplacée par 0.; Valeur Cible OCR improbable [Le vendredi 4 sept. 2026 | Soir | 8e | Aux] : 202 remplacée par 0.; Écart détecté [Le vendredi 4 sept. 2026 | Soir | CDJ | Aux] : Présences indiquées = 4, Lignes comptées = 1. La valeur 1 a été retenue pour le fichier Excel.

### ✅ Validation Checklist
- ✓ Records parsed successfully
- ✓ Departments identified: 9
- ⚠ 15 discrepancies detected

### 📌 Notes
Anonymisation: Désactivée

### 🔍 Calculation & Alignment Audit
15 ligne(s) avec écart détecté(es). Vérification manuelle recommandée.

---
## 📝 Execution Journal Entry — 2026-09-01 18:48:47 EDT

- **Dernier Commit Git:** Imitation Strategy With Target Values
- **Description de la Mise à Jour:** Rapport de conversion PDF vers Excel avec décompte OCR et validation des codes
- **Source File:** Rapport-Template-Soir.pdf
- **Report Context:** Le vendredi 4 sept. 2026 | Shift: Soir

### 📊 Parsing Metrics
- **Total Shift Rows Extracted:** 27
- **Total Departments Identified:** 9
- **Code Count:**
  - 4e: AIC=1, FL4=5, N=1, TSS=1
  - 6e: AIC=1, FL6=7, N=1
  - 7e: AIC=1, FL=1, FL7=5
  - 8e: FL8=5
  - ACUR/GDL: ACUR=2, FL=1, HSCM=1
  - CDJ: CDJ=2
  - ECG: N=1
  - SIC: AIC=1, N=1, SIC=5
  - URG: AIC=1, BRAN=1, CHOC=1, HOR12=1, MON=2, N=1, S=3, TRI=2, URG=1

### ⚠️ Execution Warnings
Valeur Cible OCR improbable [Le vendredi 4 sept. 2026 | Soir | 4e | Aux] : 22 remplacée par 0.; Valeur Cible OCR improbable [Le vendredi 4 sept. 2026 | Soir | 7e | AA] : 23 remplacée par 0.; Écart détecté [Le vendredi 4 sept. 2026 | Soir | CDJ | Aux] : Présences indiquées = 4, Lignes comptées = 1. La valeur 1 a été retenue pour le fichier Excel.

### ✅ Validation Checklist
- ✓ Records parsed successfully
- ✓ Departments identified: 9
- ⚠ 8 discrepancies detected

### 📌 Notes
Anonymisation: Désactivée

### 🔍 Calculation & Alignment Audit
8 ligne(s) avec écart détecté(es). Vérification manuelle recommandée.

---
## 📝 Execution Journal Entry — 2026-09-01 18:49:38 EDT

- **Dernier Commit Git:** Imitation Strategy With Target Values
- **Description de la Mise à Jour:** Rapport de conversion PDF vers Excel avec décompte OCR et validation des codes
- **Source File:** Rapport-Template-Soir.pdf
- **Report Context:** Le vendredi 4 sept. 2026 | Shift: Soir

### 📊 Parsing Metrics
- **Total Shift Rows Extracted:** 27
- **Total Departments Identified:** 9
- **Code Count:**
  - 4e: AIC=1, FL4=5, N=1, TSS=1
  - 6e: AIC=1, FL6=7, N=1
  - 7e: AIC=1, FL=1, FL7=5
  - 8e: FL8=5
  - ACUR/GDL: ACUR=2, FL=1, HSCM=1
  - CDJ: CDJ=2
  - ECG: N=1
  - SIC: AIC=1, N=1, SIC=5
  - URG: AIC=1, BRAN=1, CHOC=1, HOR12=1, MON=2, N=1, S=3, TRI=2, URG=1

### ⚠️ Execution Warnings
Valeur Cible OCR improbable [Le vendredi 4 sept. 2026 | Soir | 4e | Aux] : 22 remplacée par 0.; Écart détecté [Le vendredi 4 sept. 2026 | Soir | CDJ | Aux] : Présences indiquées = 4, Lignes comptées = 1. La valeur 1 a été retenue pour le fichier Excel.

### ✅ Validation Checklist
- ✓ Records parsed successfully
- ✓ Departments identified: 9
- ⚠ 4 discrepancies detected

### 📌 Notes
Anonymisation: Désactivée

### 🔍 Calculation & Alignment Audit
4 ligne(s) avec écart détecté(es). Vérification manuelle recommandée.

---
## 📝 Execution Journal Entry — 2026-09-01 18:50:29 EDT

- **Dernier Commit Git:** Imitation Strategy With Target Values
- **Description de la Mise à Jour:** Rapport de conversion PDF vers Excel avec décompte OCR et validation des codes
- **Source File:** Rapport-Template-Soir.pdf
- **Report Context:** Le vendredi 4 sept. 2026 | Shift: Soir

### 📊 Parsing Metrics
- **Total Shift Rows Extracted:** 27
- **Total Departments Identified:** 9
- **Code Count:**
  - 4e: AIC=1, FL4=5, N=1, TSS=1
  - 6e: AIC=1, FL6=7, N=1
  - 7e: AIC=1, FL=1, FL7=5
  - 8e: FL8=5
  - ACUR/GDL: ACUR=2, FL=1, HSCM=1
  - CDJ: CDJ=2
  - ECG: N=1
  - SIC: AIC=1, N=1, SIC=5
  - URG: AIC=1, BRAN=1, CHOC=1, HOR12=1, MON=2, N=1, S=3, TRI=2, URG=1

### ⚠️ Execution Warnings
Valeur Cible OCR improbable [Le vendredi 4 sept. 2026 | Soir | 4e | Aux] : 22 remplacée par 0.; Écart détecté [Le vendredi 4 sept. 2026 | Soir | CDJ | Aux] : Présences indiquées = 4, Lignes comptées = 1. La valeur 1 a été retenue pour le fichier Excel.

### ✅ Validation Checklist
- ✓ Records parsed successfully
- ✓ Departments identified: 9
- ⚠ 3 discrepancies detected

### 📌 Notes
Anonymisation: Désactivée

### 🔍 Calculation & Alignment Audit
3 ligne(s) avec écart détecté(es). Vérification manuelle recommandée.

---

## Audit de précision - 4 Septembre Soir

- **Source :** `tests/Rapport-Template-Soir.pdf`
- **Étalon :** `tests/Rapport-Target-Soir.xlsx`
- **Procédure :** génération par `test_execution.py`, puis comparaison par paire `(Département, Catégorie)` des colonnes `Cible`, `Présences` et `Écart (Décompte vs Cible)` via `verify_output.py`.
- **Corrections apportées :**
  - la valeur de ratio est désormais lue dans une fenêtre bornée après `Ratio/Présences`, ce qui empêche les identifiants employés et les heures de travail d'être interprétés comme des cibles;
  - les séparateurs OCR entre cible et présences sont acceptés, y compris les ponctuations et signes parasites;
  - un nombre OCR tronqué (par exemple le début de `202`) n'est pas accepté comme une cible valide;
  - lorsqu'une cible clinique est absente, le décompte de lignes structurées est retenu comme repli général, sans valeur codée depuis l'étalon.
- **Validation :** `pytest -q tests/test_workforce_pipeline.py` réussit avec 14 tests passants.
- **Résultat :** 13 écarts métier sur 108 valeurs comparées, soit 87,96 % de concordance. Les écarts restants concernent des ancres ou ratios ambigus dans le texte natif (`6e/Aux`, `7e/Aux`, `ACUR/GDL/AA`, `SIC/PAB`, `URG/Inf`, `URG/PAB`). Les corriger à partir de l'étalon exigerait de coder en dur ses chiffres, ce qui a été écarté.

---
## 📝 Execution Journal Entry — 2026-09-02 09:38:54 EDT

- **Dernier Commit Git:** fix(parser): align output with Sept 4th Gold Standard XLSX
- **Description de la Mise à Jour:** Rapport de conversion PDF vers Excel avec décompte OCR et validation des codes
- **Source File:** Rapport-Template-Soir.pdf
- **Report Context:** Le vendredi 4 sept. 2026 | Shift: Soir

### 📊 Parsing Metrics
- **Total Shift Rows Extracted:** 27
- **Total Departments Identified:** 9
- **Code Count:**
  - 4e: AIC=1, FL4=5, N=1, TSS=1
  - 6e: AIC=1, FL6=7, N=1
  - 7e: AIC=1, FL=1, FL7=5
  - 8e: FL8=5
  - ACUR/GDL: ACUR=2, FL=1, HSCM=1
  - CDJ: CDJ=2
  - ECG: N=1
  - SIC: AIC=1, N=1, SIC=5
  - URG: AIC=1, BRAN=1, CHOC=1, HOR12=1, MON=2, N=1, S=3, TRI=2, URG=1

### ⚠️ Execution Warnings
Valeur Cible OCR improbable [Le vendredi 4 sept. 2026 | Soir | 4e | Aux] : 22 remplacée par 0.; Écart détecté [Le vendredi 4 sept. 2026 | Soir | CDJ | Aux] : Présences indiquées = 4, Lignes comptées = 1. La valeur 1 a été retenue pour le fichier Excel.

### ✅ Validation Checklist
- ✓ Records parsed successfully
- ✓ Departments identified: 9
- ⚠ 3 discrepancies detected

### 📌 Notes
Anonymisation: Désactivée

### 🔍 Calculation & Alignment Audit
3 ligne(s) avec écart détecté(es). Vérification manuelle recommandée.

---
## 📝 Execution Journal Entry — 2026-09-02 15:56:34 EDT

- **Dernier Commit Git:** fix(rules): enforce AA-only for ACUR/GDL and add threshold audit logic
- **Description de la Mise à Jour:** Rapport de conversion PDF vers Excel avec décompte OCR et validation des codes
- **Source File:** Rapport-Template-Soir.pdf
- **Report Context:** Le vendredi 4 sept. 2026 | Shift: Soir

### 📊 Parsing Metrics
- **Total Shift Rows Extracted:** 27
- **Total Departments Identified:** 9
- **Code Count:**
  - 4e: AIC=1, FL4=5, N=1, TSS=1
  - 6e: AIC=1, FL6=7, N=1
  - 7e: AIC=1, FL=1, FL7=5
  - 8e: FL8=5
  - ACUR/GDL: ACUR=2, FL=1, HSCM=1
  - CDJ: CDJ=2
  - ECG: N=1
  - SIC: AIC=1, N=1, SIC=5
  - URG: AIC=1, BRAN=1, CHOC=1, HOR12=1, MON=2, N=1, S=3, TRI=2, URG=1

### ⚠️ Execution Warnings
Aucun avertissement

### ✅ Validation Checklist
- ✓ Records parsed successfully
- ✓ Departments identified: 9
- ⚠ 9 discrepancies detected

### 📌 Notes
Anonymisation: Désactivée

### 🔍 Calculation & Alignment Audit
9 ligne(s) avec écart détecté(es). Vérification manuelle recommandée.

---
## 📝 Execution Journal Entry — 2026-09-02 15:57:17 EDT

- **Dernier Commit Git:** fix(rules): enforce AA-only for ACUR/GDL and add threshold audit logic
- **Description de la Mise à Jour:** Rapport de conversion PDF vers Excel avec décompte OCR et validation des codes
- **Source File:** Rapport-Template-Soir.pdf
- **Report Context:** Le vendredi 4 sept. 2026 | Shift: Soir

### 📊 Parsing Metrics
- **Total Shift Rows Extracted:** 27
- **Total Departments Identified:** 9
- **Code Count:**
  - 4e: AIC=1, FL4=5, N=1, TSS=1
  - 6e: AIC=1, FL6=7, N=1
  - 7e: AIC=1, FL=1, FL7=5
  - 8e: FL8=5
  - ACUR/GDL: ACUR=2, FL=1, HSCM=1
  - CDJ: CDJ=2
  - ECG: N=1
  - SIC: AIC=1, N=1, SIC=5
  - URG: AIC=1, BRAN=1, CHOC=1, HOR12=1, MON=2, N=1, S=3, TRI=2, URG=1

### ⚠️ Execution Warnings
Aucun avertissement

### ✅ Validation Checklist
- ✓ Records parsed successfully
- ✓ Departments identified: 9
- ⚠ 9 discrepancies detected

### 📌 Notes
Anonymisation: Désactivée

### 🔍 Calculation & Alignment Audit
9 ligne(s) avec écart détecté(es). Vérification manuelle recommandée.

---
## 📝 Execution Journal Entry — 2026-09-02 16:00:34 EDT

- **Dernier Commit Git:** fix(rules): enforce AA-only for ACUR/GDL and add threshold audit logic
- **Description de la Mise à Jour:** Rapport de conversion PDF vers Excel avec décompte OCR et validation des codes
- **Source File:** Rapport-Template-Soir.pdf
- **Report Context:** Le vendredi 4 sept. 2026 | Shift: Soir

### 📊 Parsing Metrics
- **Total Shift Rows Extracted:** 27
- **Total Departments Identified:** 9
- **Code Count:**
  - 4e: AIC=1, FL4=5, N=1, TSS=1
  - 6e: AIC=1, FL6=7, N=1
  - 7e: AIC=1, FL=1, FL7=5
  - 8e: FL8=5
  - ACUR/GDL: ACUR=2, FL=1, HSCM=1
  - CDJ: CDJ=2
  - ECG: N=1
  - SIC: AIC=1, N=1, SIC=5
  - URG: AIC=1, BRAN=1, CHOC=1, HOR12=1, MON=2, N=1, S=3, TRI=2, URG=1

### ⚠️ Execution Warnings
t; e; s; t; s; /; o; u; t; p; u; t; _; R; a; p; p; o; r; t; -; T; e; m; p; l; a; t; e; -; S; o; i; r; .; x; l; s; x

### ✅ Validation Checklist
- ✓ Records parsed successfully
- ✓ Departments identified: 9
- ⚠ 9 discrepancies detected

### 📌 Notes
Anonymisation: Désactivée

### 🔍 Calculation & Alignment Audit
9 ligne(s) avec écart détecté(es). Vérification manuelle recommandée.

---
## 📝 Execution Journal Entry — 2026-09-02 16:01:09 EDT

- **Dernier Commit Git:** fix(rules): enforce AA-only for ACUR/GDL and add threshold audit logic
- **Description de la Mise à Jour:** Rapport de conversion PDF vers Excel avec décompte OCR et validation des codes
- **Source File:** Rapport-Template-Soir.pdf
- **Report Context:** Le vendredi 4 sept. 2026 | Shift: Soir

### 📊 Parsing Metrics
- **Total Shift Rows Extracted:** 27
- **Total Departments Identified:** 9
- **Code Count:**
  - 4e: AIC=1, FL4=5, N=1, TSS=1
  - 6e: AIC=1, FL6=7, N=1
  - 7e: AIC=1, FL=1, FL7=5
  - 8e: FL8=5
  - ACUR/GDL: ACUR=2, FL=1, HSCM=1
  - CDJ: CDJ=2
  - ECG: N=1
  - SIC: AIC=1, N=1, SIC=5
  - URG: AIC=1, BRAN=1, CHOC=1, HOR12=1, MON=2, N=1, S=3, TRI=2, URG=1

### ⚠️ Execution Warnings
t; e; s; t; s; /; o; u; t; p; u; t; _; R; a; p; p; o; r; t; -; T; e; m; p; l; a; t; e; -; S; o; i; r; .; x; l; s; x

### ✅ Validation Checklist
- ✓ Records parsed successfully
- ✓ Departments identified: 9
- ⚠ 9 discrepancies detected

### 📌 Notes
Anonymisation: Désactivée

### 🔍 Calculation & Alignment Audit
9 ligne(s) avec écart détecté(es). Vérification manuelle recommandée.

---
## 📝 Execution Journal Entry — 2026-09-02 21:03:52 EDT

- **Dernier Commit Git:** Updated app components to allow ACUR/GDL AA update
- **Description de la Mise à Jour:** Rapport de conversion PDF vers Excel avec décompte OCR et validation des codes
- **Source File:** Rapport-Template-Soir.pdf
- **Report Context:** Le vendredi 4 sept. 2026 | Shift: Soir

### 📊 Parsing Metrics
- **Total Shift Rows Extracted:** 27
- **Total Departments Identified:** 9
- **Code Count:**
  - 4e: AIC=1, FL4=5, N=1, TSS=1
  - 6e: AIC=1, FL6=7, N=1
  - 7e: AIC=1, FL=1, FL7=5
  - 8e: FL8=5
  - ACUR/GDL: ACUR=2, FL=1, HSCM=1
  - CDJ: CDJ=2
  - ECG: N=1
  - SIC: AIC=1, N=1, SIC=5
  - URG: AIC=1, BRAN=1, CHOC=1, HOR12=1, MON=2, N=1, S=3, TRI=2, URG=1

### ⚠️ Execution Warnings
Aucun avertissement

### ✅ Validation Checklist
- ✓ Records parsed successfully
- ✓ Departments identified: 9
- ⚠ 8 discrepancies detected

### 📌 Notes
Anonymisation: Désactivée

### 🔍 Calculation & Alignment Audit
8 ligne(s) avec écart détecté(es). Vérification manuelle recommandée.

---
## 📝 Execution Journal Entry — 2026-09-02 21:06:04 EDT

- **Dernier Commit Git:** Updated app components to allow ACUR/GDL AA update
- **Description de la Mise à Jour:** Rapport de conversion PDF vers Excel avec décompte OCR et validation des codes
- **Source File:** Rapport-Template-Soir.pdf
- **Report Context:** Le vendredi 4 sept. 2026 | 4 sept. 2026 | Shift: Soir

### 📊 Parsing Metrics
- **Total Shift Rows Extracted:** 27
- **Total Departments Identified:** 9
- **Code Count:**
  - 4e: AIC=1, FL4=5, N=1, TSS=1
  - 6e: AIC=1, FL6=7, N=1
  - 7e: AIC=1, FL=1, FL7=5
  - 8e: FL8=5
  - ACUR/GDL: ACUR=2, FL=1, HSCM=1
  - CDJ: CDJ=2
  - ECG: N=1
  - SIC: AIC=1, N=1, SIC=5
  - URG: AIC=1, BRAN=1, CHOC=1, HOR12=1, MON=2, N=1, S=3, TRI=2, URG=1

### ⚠️ Execution Warnings
Aucun avertissement

### ✅ Validation Checklist
- ✓ Records parsed successfully
- ✓ Departments identified: 9
- ⚠ 8 discrepancies detected

### 📌 Notes
Anonymisation: Désactivée

### 🔍 Calculation & Alignment Audit
8 ligne(s) avec écart détecté(es). Vérification manuelle recommandée.

---
## 📝 Execution Journal Entry — 2026-09-02 21:07:03 EDT

- **Dernier Commit Git:** Updated app components to allow ACUR/GDL AA update
- **Description de la Mise à Jour:** Rapport de conversion PDF vers Excel avec décompte OCR et validation des codes
- **Source File:** Rapport-Template-Soir.pdf
- **Report Context:** Le vendredi 4 sept. 2026 | 4 sept. 2026 | Shift: Soir

### 📊 Parsing Metrics
- **Total Shift Rows Extracted:** 27
- **Total Departments Identified:** 9
- **Code Count:**
  - 4e: AIC=1, FL4=5, N=1, TSS=1
  - 6e: AIC=1, FL6=7, N=1
  - 7e: AIC=1, FL=1, FL7=5
  - 8e: FL8=5
  - ACUR/GDL: ACUR=2, FL=1, HSCM=1
  - CDJ: CDJ=2
  - ECG: N=1
  - SIC: AIC=1, N=1, SIC=5
  - URG: AIC=1, BRAN=1, CHOC=1, HOR12=1, MON=2, N=1, S=3, TRI=2, URG=1

### ⚠️ Execution Warnings
Aucun avertissement

### ✅ Validation Checklist
- ✓ Records parsed successfully
- ✓ Departments identified: 9
- ⚠ 8 discrepancies detected

### 📌 Notes
Anonymisation: Désactivée

### 🔍 Calculation & Alignment Audit
8 ligne(s) avec écart détecté(es). Vérification manuelle recommandée.

---
## 📝 Execution Journal Entry — 2026-09-02 21:08:01 EDT

- **Dernier Commit Git:** Updated app components to allow ACUR/GDL AA update
- **Description de la Mise à Jour:** Rapport de conversion PDF vers Excel avec décompte OCR et validation des codes
- **Source File:** Rapport-Template-Soir.pdf
- **Report Context:** Le vendredi 4 sept. 2026 | Shift: Soir

### 📊 Parsing Metrics
- **Total Shift Rows Extracted:** 26
- **Total Departments Identified:** 9
- **Code Count:**
  - 4e: AIC=1, FL4=5, N=1, TSS=1
  - 6e: AIC=1, FL6=7, N=1
  - 7e: AIC=1, FL=1, FL7=5
  - 8e: FL8=5
  - ACUR/GDL: ACUR=2, FL=1, HSCM=1
  - CDJ: CDJ=2
  - ECG: N=1
  - SIC: AIC=1, N=1, SIC=5
  - URG: AIC=1, BRAN=1, CHOC=1, HOR12=1, MON=2, N=1, S=3, TRI=2, URG=1

### ⚠️ Execution Warnings
Aucun avertissement

### ✅ Validation Checklist
- ✓ Records parsed successfully
- ✓ Departments identified: 9
- ⚠ 8 discrepancies detected

### 📌 Notes
Anonymisation: Désactivée

### 🔍 Calculation & Alignment Audit
8 ligne(s) avec écart détecté(es). Vérification manuelle recommandée.

---

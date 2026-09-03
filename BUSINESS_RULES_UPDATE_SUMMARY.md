# Sparce AI - Regles d'affaires MODE B

## Objet

Cette specification decrit les regles utilisees par le pipeline Sparce AI pour
convertir un rapport PDF d'effectifs en classeur Excel. Elle remplace les
regles historiques fondees sur les ratios OCR.

## Cibles fixes

La colonne `Cible` est la copie de reference de `Cible.xlsx`, integree sous
forme de matrice immuable dans `src/config/target_matrix.py`. C'est
l'unique source de verite : aucun ratio ni aucune cible lus dans le PDF ne
peuvent modifier le resultat Excel.

L'ordre des categories est toujours : `Inf`, `Aux`, `PAB`, `AA`.

| Departement | Jour | Soir | Nuit |
| --- | --- | --- | --- |
| 4e | 3, 2, 3, 1 | 3, 2, 2, 1 | 2, 1, 1, 0 |
| 7e | 3, 2, 3, 1 | 3, 1, 2, 1 | 2, 0, 2, 0 |
| 6e | 4, 2, 3, 1 | 3, 2, 2, 1 | 2, 2, 2, 0 |
| 8e | 3, 2, 3, 1 | 3, 2, 2, 1 | 2, 2, 2, 0 |
| SIC | 5, 0, 1, 0 | 4, 0, 1, 0 | 4, 0, 0, 0 |
| CDJ | 2, 1, 1, 1 | 1, 1, 0, 0 | 0, 0, 0, 0 |
| URG | 10, 1, 2, 2 | 9, 1, 3, 2 | 7, 1, 2, 1 |
| ECG | 0, 0, 1, 0 | 0, 0, 1, 0 | 0, 0, 1, 0 |
| ACUR/GDL | 0, 0, 0, 1 | 0, 0, 0, 1 | 0, 0, 0, 1 |

Chaque suite de quatre valeurs respecte l'ordre des categories indique ci-dessus.
Les lignes absentes de l'OCR sont ajoutees au classeur avec leur cible fixe et
zero presence.

## Reconnaissance des departements

L'ancre OCR `HF Unité de médecine 6e` est reconnue sans sensibilite a la casse,
avec ou sans tiret et avec des espaces variables. Elle est associee
exclusivement au departement Excel `6e`; elle ne doit jamais etre associee a
`8e`.

Le bloc du 6e se termine a la prochaine ancre de departement ou de categorie.
Ses lignes physiques sont donc attribuees seulement a `Inf`, `Aux`, `PAB` ou
`AA` du 6e. Le departement `8e` demeure reserve a l'ancre de chirurgie court
sejour.

## Presences et ecarts

Une ligne physique valide de la table OCR compte pour une presence. Les entetes,
les dates et les lignes structurelles qui ne representent pas un employe sont
exclus. Les ratios trouves dans le PDF ne sont ni lus ni utilises pour le
comptage.

L'ecart numerique est calcule ainsi :

`Écart = Présences - Cible`

La colonne `Écart (Décompte vs Cible)` affiche cet ecart. Une valeur non nulle
est une anomalie de dotation.

## Exceptions

- Chaque code `HOR12` est exclu du nombre numerique de presences, quelle que
  soit la categorie ou le departement. La cellule `Écart (Décompte vs Cible)`
  reste strictement numerique et ne recoit aucun suffixe `+HOR12`.
- Chaque code `TRANS` est egalement soustrait des presences dans toutes les
  categories et tous les departements.
- Les ancres `HF Accueil et réception` et `CIUSSS Gestion des lits` sont
  fusionnees dans la ligne finale `ACUR/GDL` / `AA`.
- Pour `ACUR/GDL`, seules les lignes `AA` comptent comme presences. Les
  categories `Inf`, `Aux` et `PAB` sont forcees a `Présences = 0`; leurs cibles
  fixes sont egalement nulles.

## Controle de regression

Les tests de `tests/test_workforce_pipeline.py` verifient la matrice complete
pour le quart Soir, l'isolement de l'ancre 6e, le comptage physique des lignes
et les soustractions `HOR12`/`TRANS`.
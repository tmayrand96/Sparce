#!/usr/bin/env python
"""
Validation script to verify business rule updates in the generated Excel file.
"""

import sys
from pathlib import Path
from openpyxl import load_workbook

def main():
    output_path = Path("tests/output_Rapport-Template-Soir.xlsx")
    
    if not output_path.exists():
        print(f"ERROR: Output file not found at {output_path}")
        sys.exit(1)
    
    workbook = load_workbook(output_path)
    
    print("\n" + "=" * 80)
    print("WORKBOOK STRUCTURE & VERIFICATION")
    print("=" * 80)
    print(f"\nSheet names: {workbook.sheetnames}")
    
    # Check Audit sheet
    if "Rapport_Audit" in workbook.sheetnames:
        audit_sheet = workbook["Rapport_Audit"]
        print("\n✓ Audit sheet present")
        print(f"  - Title: {audit_sheet['A1'].value}")
        print(f"  - Execution info: {audit_sheet['A2'].value}")
    
    # Check data sheets (all except Audit)
    data_sheets = [name for name in workbook.sheetnames if name != "Rapport_Audit"]
    
    for sheet_name in data_sheets:
        sheet = workbook[sheet_name]
        print(f"\n{'─' * 80}")
        print(f"Sheet: {sheet_name}")
        print(f"{'─' * 80}")
        
        shift = sheet['A1'].value
        date = sheet['A2'].value
        print(f"  Shift: {shift}")
        print(f"  Date: {date}")
        
        # Extract data rows
        rows = []
        for row in sheet.iter_rows(min_row=5, max_row=sheet.max_row, values_only=False):
            if any(cell.value for cell in row):
                dept = row[0].value
                category = row[1].value
                cible = row[2].value
                presences = row[3].value
                ecart_presences = row[4].value
                ecart_decompte = row[5].value
                
                if dept and category:
                    rows.append({
                        'Département': dept,
                        'Catégorie': category,
                        'Cible': cible,
                        'Présences': presences,
                        'Écart (Prés. vs Cible)': ecart_presences,
                        'Écart (Déc. vs Cible)': ecart_decompte,
                    })
        
        # Print rows organized by department
        departments_found = {}
        for row in rows:
            dept = row['Département']
            if dept not in departments_found:
                departments_found[dept] = []
            departments_found[dept].append(row)
        
        print("\n  Data by Department:")
        for dept in sorted(departments_found.keys()):
            dept_rows = departments_found[dept]
            print(f"\n    {dept}:")
            for row in dept_rows:
                print(f"      {row['Catégorie']:15s} | Cible: {str(row['Cible']):>2} | "
                      f"Prés: {str(row['Présences']):>2} | Écart: {row['Écart (Prés. vs Cible)']}")
        
        # Verify business rules
        print(f"\n  Verification:")
        has_8e = "8e" in departments_found
        has_7e = "7e" in departments_found
        has_aa = any(row['Catégorie'] == 'AA' for row in rows)
        has_acur_gdl = "ACUR/GDL" in departments_found
        
        print(f"    ✓ Floor 6e mapped to '8e': {has_8e}")
        print(f"    ✓ Floor 7e present: {has_7e}")
        print(f"    ✓ Category 'AA' present: {has_aa}")
        if has_aa:
            aa_rows = [r for r in rows if r['Catégorie'] == 'AA']
            print(f"      - Found {len(aa_rows)} AA entries")
            for dept_name, dept_list in departments_found.items():
                aa_in_dept = [r for r in dept_list if r['Catégorie'] == 'AA']
                if aa_in_dept:
                    print(f"        - {len(aa_in_dept)} in {dept_name}")
        print(f"    ✓ ACUR/GDL department present: {has_acur_gdl}")
    
    print("\n" + "=" * 80)
    return 0

if __name__ == "__main__":
    sys.exit(main())

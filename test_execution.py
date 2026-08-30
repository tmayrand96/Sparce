#!/usr/bin/env python
"""
Test script to validate business rule updates on the workforce PDF pipeline.
"""

import sys
from datetime import datetime
from pathlib import Path
from backend.core.workforce_pipeline import convert_workforce_pdf

def main():
    pdf_path = Path("tests/Rapport-Template-Soir.pdf")
    
    if not pdf_path.exists():
        print(f"ERROR: Test PDF not found at {pdf_path}")
        sys.exit(1)
    
    print("=" * 80)
    print(f"Execution Started: {datetime.now().isoformat()}")
    print("=" * 80)
    print(f"\nProcessing: {pdf_path.name}")
    print(f"Shift: Soir")
    print()
    
    try:
        warnings = []
        output = convert_workforce_pdf(
            pdf_path,
            shift="Soir",
            warnings=warnings,
            source_file_name=pdf_path.name
        )
        
        # Save output for inspection
        output_path = Path("tests/output_Rapport-Template-Soir.xlsx")
        with open(output_path, "wb") as f:
            f.write(output.getvalue())
        
        print(f"✓ Conversion successful!")
        print(f"✓ Output saved to: {output_path}")
        print()
        print(f"Execution completed: {datetime.now().isoformat()}")
        
        if warnings:
            print("\n" + "=" * 80)
            print("WARNINGS DETECTED:")
            print("=" * 80)
            for i, warning in enumerate(warnings, 1):
                print(f"{i}. {warning}")
        
        return 0
        
    except Exception as e:
        print(f"✗ Conversion failed with error:")
        print(f"  {type(e).__name__}: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())

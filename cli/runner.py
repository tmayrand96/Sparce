import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Hardcoded absolute path execution to bypass all environment lookup errors
ABSOLUTE_ENV_PATH = "/workspaces/Sparce/.env"

if os.path.exists(ABSOLUTE_ENV_PATH):
    load_dotenv(dotenv_path=ABSOLUTE_ENV_PATH)
    print(f"DEBUG: API Key injected from {ABSOLUTE_ENV_PATH}? {'Yes' if os.getenv('GOOGLE_API_KEY') else 'No'}")
else:
    print(f"DEBUG: Critical Error - System could not find file at: {ABSOLUTE_ENV_PATH}")

# Core architectural imports (guaranteed to receive the environment variables now)
from backend.core.ocr_engine import OCREngine
from backend.core.text_parser import clean_and_structure
from backend.core.summarizer import generate_summary

def main():
    parser = argparse.ArgumentParser(description="Sparce: Mobile Document Summarizer CLI")
    parser.add_argument("--image", type=str, required=True, help="Path to the mobile camera image capture")
    args = parser.parse_args()

    image_path = Path(args.image)
    
    # Execution Pipeline
    # Instantiate OCREngine and extract text
    ocr_engine = OCREngine()
    ocr_result = ocr_engine.extract_text(image_path)
    
    # Check if OCR extraction was successful
    if ocr_result["status"] != "success":
        print(f"Error: {ocr_result.get('message', 'Unknown OCR error')}", file=sys.stderr)
        sys.exit(1)
    
    raw_text = ocr_result["raw_text"]
    cleaned_text = clean_and_structure(raw_text)
    summary = generate_summary(cleaned_text)
    
    print("\n--- Document Summary ---")
    print(summary)

if __name__ == "__main__":
    main()
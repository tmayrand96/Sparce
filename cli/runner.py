import argparse
import sys
from pathlib import Path
from backend.ocr_engine import OCREngine
from backend.text_parser import clean_and_structure
from backend.summarizer import generate_summary

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
import argparse
from pathlib import Path
from backend.ocr_engine import extract_raw_text
from backend.text_parser import clean_and_structure
from backend.summarizer import generate_summary

def main():
    parser = argparse.ArgumentParser(description="Sparce: Mobile Document Summarizer CLI")
    parser.add_argument("--image", type=str, required=True, help="Path to the mobile camera image capture")
    args = parser.parse_args()

    image_path = Path(args.image)
    
    # Execution Pipeline
    raw_text = extract_raw_text(image_path)
    cleaned_text = clean_and_structure(raw_text)
    summary = generate_summary(cleaned_text)
    
    print("\n--- Document Summary ---")
    print(summary)

if __name__ == "__main__":
    main()
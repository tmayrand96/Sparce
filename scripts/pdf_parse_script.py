import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.core.pdf_parser import PDFDocumentParser


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/pdf_parse_script.py <path-to-pdf>")

    document_path = Path(sys.argv[1])
    parser = PDFDocumentParser()
    result = parser.parse(document_path)

    if result.get("status") != "success":
        raise SystemExit(result.get("message", "PDF parsing failed"))

    print(result["raw_text"])


if __name__ == "__main__":
    main()

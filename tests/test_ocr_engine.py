from unittest.mock import patch

import pytest
from pathlib import Path
from backend.core.ocr_engine import OCREngine, OCREngineError

def test_validate_image_missing_file():
    """Verify that a non-existent file path safely triggers an OCREngineError."""
    engine = OCREngine()
    fake_path = Path("data/this_file_does_not_exist.png")
    
    with pytest.raises(OCREngineError) as exc_info:
        engine.validate_image(fake_path)
        
    assert "Target image path does not exist" in str(exc_info.value)

def test_validate_image_is_directory():
    """Verify that targeting a directory instead of a file triggers an OCREngineError."""
    engine = OCREngine()
    # We use our existing data directory as the test target
    dir_path = Path("data")
    
    with pytest.raises(OCREngineError) as exc_info:
        engine.validate_image(dir_path)
        
    assert "Target path is a directory, expected a file" in str(exc_info.value)

def test_validate_image_corrupt_file(tmp_path):
    """Verify that an invalid image text stream triggers a validation failure."""
    engine = OCREngine()
    
    # Create a temporary fake text file masquerading as a PNG image
    bad_image = tmp_path / "fake_image.png"
    bad_image.write_text("This is plain text, not valid PNG binary data.")
    
    # Pass the corrupt image into our extractor wrapper
    result = engine.extract_text(bad_image)
    
    assert result["status"] == "error"
    assert result["error_type"] == "ValidationFailure"
    assert "Unsupported or invalid image format" in result["message"]


def test_extract_text_from_pdf_uses_pdf_parser(tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    expected_result = {
        "status": "success",
        "source_type": "pdf",
        "raw_text": "Hello from PDF",
        "page_count": 1,
        "results": [{"page_index": 0, "raw_text": "Hello from PDF"}],
        "file_name": pdf_path.name,
    }

    with patch("backend.core.ocr_engine.PDFDocumentParser.parse", return_value=expected_result) as mock_parse:
        engine = OCREngine()
        result = engine.extract_text(pdf_path)

    assert result == expected_result
    mock_parse.assert_called_once_with(pdf_path)
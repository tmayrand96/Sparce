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


def test_extract_text_from_pdf_converts_each_page(tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    fake_page_images = [
        object(),
        object(),
    ]

    with patch("backend.core.ocr_engine.convert_to_images", return_value=fake_page_images) as mock_convert, patch(
        "backend.core.ocr_engine.pytesseract.image_to_string",
        side_effect=["page one", "page two"],
    ) as mock_tesseract:
        engine = OCREngine()
        result = engine.extract_text(pdf_path)

    assert result["status"] == "success"
    assert result["source_type"] == "pdf"
    assert result["page_count"] == 2
    assert result["results"] == [
        {"page_index": 0, "raw_text": "page one"},
        {"page_index": 1, "raw_text": "page two"},
    ]
    mock_convert.assert_called_once_with(str(pdf_path))
    assert mock_tesseract.call_count == 2
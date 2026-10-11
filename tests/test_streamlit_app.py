from types import SimpleNamespace

from frontend.app import detect_document_format


def test_detect_document_format_for_pdf():
    uploaded_file = SimpleNamespace(name="notes.pdf")

    file_type, label = detect_document_format(uploaded_file)

    assert file_type == "pdf"
    assert label == "Detected Format: PDF Document"


def test_detect_document_format_for_image():
    uploaded_file = SimpleNamespace(name="scan.jpg")

    file_type, label = detect_document_format(uploaded_file)

    assert file_type == "image"
    assert label == "Detected Format: JPEG Image"


def test_detect_document_format_for_workforce_workbook():
    uploaded_file = SimpleNamespace(name="workforce.xlsx")

    file_type, label = detect_document_format(uploaded_file)

    assert file_type == "xlsx"
    assert label == "Detected Format: Excel Workforce Workbook"

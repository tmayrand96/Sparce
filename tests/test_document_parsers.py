import inspect
import typing
from pathlib import Path

from backend.core.base_document_parser import BaseDocumentParser
from backend.core.pdf_parser import PDFDocumentParser
from cli.runner import build_parser_for_path


def test_base_document_parser_contract():
    hints = typing.get_type_hints(BaseDocumentParser.parse)
    assert hints["document_path"] == typing.Union[str, Path]
    assert hints["return"] == typing.Dict[str, typing.Any]


def test_factory_selects_pdf_parser_for_pdf_extension():
    parser = build_parser_for_path("report.pdf")
    assert isinstance(parser, PDFDocumentParser)


def test_factory_uses_default_parser_for_non_pdf_extensions():
    parser = build_parser_for_path("scan.png")
    assert isinstance(parser, BaseDocumentParser)


def test_requirements_include_pdf_parsing_libraries():
    requirements = Path("requirements.txt").read_text(encoding="utf-8")
    assert "pdfplumber" in requirements
    assert "pypdf" in requirements

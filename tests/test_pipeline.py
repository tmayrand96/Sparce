import pytest
from unittest.mock import MagicMock, patch
from backend.core.pipeline import ProcessingPipeline, ProcessingPipelineError


class TestProcessingPipeline:
    @patch("backend.core.pipeline.OCREngine")
    @patch("backend.core.pipeline.clean_and_structure")
    @patch("backend.core.pipeline.generate_summary")
    def test_process_document_success(
        self,
        mock_generate_summary,
        mock_clean_and_structure,
        mock_ocr_engine_class,
    ):
        mock_ocr_engine = MagicMock()
        mock_ocr_engine.extract_text.return_value = {
            "status": "success",
            "raw_text": "Extracted OCR text.",
        }
        mock_ocr_engine_class.return_value = mock_ocr_engine

        mock_clean_and_structure.return_value = "Cleaned OCR text."
        mock_generate_summary.return_value = "Generated summary."

        pipeline = ProcessingPipeline(linkedin_client=MagicMock())
        summary = pipeline.process_document("/tmp/doc.png")

        assert summary == "Generated summary."
        mock_clean_and_structure.assert_called_once_with("Extracted OCR text.")
        mock_generate_summary.assert_called_once_with("Cleaned OCR text.")

    @patch("backend.core.pipeline.OCREngine")
    def test_process_document_ocr_failure(self, mock_ocr_engine_class):
        mock_ocr_engine = MagicMock()
        mock_ocr_engine.extract_text.return_value = {
            "status": "error",
            "message": "File not found.",
        }
        mock_ocr_engine_class.return_value = mock_ocr_engine

        pipeline = ProcessingPipeline(linkedin_client=MagicMock())

        with pytest.raises(ProcessingPipelineError) as exc_info:
            pipeline.process_document("/tmp/missing.png")

        assert "OCR failed" in str(exc_info.value)
        assert "File not found" in str(exc_info.value)

    @patch("backend.core.pipeline.OCREngine")
    @patch("backend.core.pipeline.clean_and_structure")
    def test_process_document_parsing_failure(self, mock_clean_and_structure, mock_ocr_engine_class):
        mock_ocr_engine = MagicMock()
        mock_ocr_engine.extract_text.return_value = {
            "status": "success",
            "raw_text": "Bad OCR output.",
        }
        mock_ocr_engine_class.return_value = mock_ocr_engine

        mock_clean_and_structure.side_effect = Exception("Cleaning failed")

        pipeline = ProcessingPipeline(linkedin_client=MagicMock())

        with pytest.raises(ProcessingPipelineError) as exc_info:
            pipeline.process_document("/tmp/doc.png")

        assert "Unexpected document processing failure" in str(exc_info.value)

    def test_post_to_linkedin_success(self):
        mock_client = MagicMock()
        mock_client.post_to_profile.return_value = {"status": "created"}

        pipeline = ProcessingPipeline(linkedin_client=mock_client)
        response = pipeline.post_to_linkedin(
            "This is a summary.",
            {"repo_url": "https://github.com/test/repo"},
        )

        assert response["status"] == "created"
        mock_client.post_to_profile.assert_called_once_with(
            "This is a summary.",
            "https://github.com/test/repo",
        )

    def test_post_to_linkedin_missing_github_url(self):
        mock_client = MagicMock()
        pipeline = ProcessingPipeline(linkedin_client=mock_client)

        with pytest.raises(ProcessingPipelineError) as exc_info:
            pipeline.post_to_linkedin("Summary text", {"name": "repo"})

        assert "GitHub context must include a valid repository URL" in str(exc_info.value)

    def test_post_to_linkedin_invalid_summary(self):
        mock_client = MagicMock()
        pipeline = ProcessingPipeline(linkedin_client=mock_client)

        with pytest.raises(ProcessingPipelineError) as exc_info:
            pipeline.post_to_linkedin("", "https://github.com/test/repo")

        assert "Summary must be a non-empty string" in str(exc_info.value)

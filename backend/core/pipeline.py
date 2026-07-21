import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union

from .ocr_engine import OCREngine, OCREngineError
from .summarizer import SummarizerError, generate_summary
from .text_parser import TextParsingError, clean_and_structure
from backend.connectors.linkedin_client import LinkedInClient, LinkedInClientError
from backend.token_provider import BaseTokenProvider, EnvTokenProvider


class Pipeline:
    """Simple orchestration interface for OCR, parsing, summarization, and posting."""

    def __init__(self, ocr_engine, parser, summarizer, connector):
        self.ocr = ocr_engine
        self.parser = parser
        self.summarizer = summarizer
        self.connector = connector

    def execute(self, image_path):
        """Run the full pipeline for a single document image."""
        ocr_result = self.ocr.extract_text(image_path)
        parsed_text = self.parser(ocr_result)
        summary = self.summarizer(parsed_text)
        return self.connector(summary)


class ProcessingPipelineError(Exception):
    """Generic exception raised when the processing pipeline fails."""
    pass


class ProcessingPipeline:
    """End-to-end document processing pipeline for OCR, cleaning, summarization, and LinkedIn posting."""

    def __init__(
        self,
        linkedin_client: Optional[LinkedInClient] = None,
        provider: Optional[BaseTokenProvider] = None,
    ) -> None:
        self.logger = logging.getLogger(__name__)
        self.provider = provider or EnvTokenProvider()
        self.ocr_engine = OCREngine(provider=self.provider)
        self.linkedin_client = linkedin_client or LinkedInClient()

    def process_document(self, image_path: Union[str, Path]) -> str:
        """Process a document image and return the generated summary."""
        self.logger.info("Starting document processing for image: %s", image_path)

        try:
            ocr_result = self.ocr_engine.extract_text(image_path)
            if ocr_result.get("status") != "success":
                message = ocr_result.get("message", "Unknown OCR error")
                self.logger.error("OCR failed for %s: %s", image_path, message)
                raise ProcessingPipelineError(f"OCR failed: {message}")

            raw_text = ocr_result.get("raw_text", "")
            if not raw_text:
                self.logger.error("OCR returned no text for %s", image_path)
                raise ProcessingPipelineError("OCR did not return any text to summarize.")

            self.logger.debug("Cleaning OCR text for image: %s", image_path)
            cleaned_text = clean_and_structure(raw_text)

            self.logger.debug("Generating summary for cleaned text from image: %s", image_path)
            summary = generate_summary(cleaned_text)

            self.logger.info("Document processing completed successfully for image: %s", image_path)
            return summary

        except (OCREngineError, TextParsingError, SummarizerError) as error:
            self.logger.exception("Document processing pipeline failed")
            raise ProcessingPipelineError(f"Document processing failed: {str(error)}") from error
        except ProcessingPipelineError:
            raise
        except Exception as error:
            self.logger.exception("Unexpected error in document processing pipeline")
            raise ProcessingPipelineError(
                "Unexpected document processing failure. See logs for details."
            ) from error

    def post_to_linkedin(
        self,
        summary: str,
        github_context: Union[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Post the generated summary to LinkedIn with GitHub context."""
        self.logger.info("Posting summary to LinkedIn")

        if not summary or not isinstance(summary, str):
            self.logger.error("Invalid summary provided for LinkedIn post")
            raise ProcessingPipelineError("Summary must be a non-empty string.")

        repository_url = self._extract_github_url(github_context)
        if not repository_url:
            self.logger.error("GitHub context missing or invalid for LinkedIn post")
            raise ProcessingPipelineError(
                "GitHub context must include a valid repository URL."
            )

        try:
            self.logger.debug("Sending LinkedIn post request for repo: %s", repository_url)
            result = self.linkedin_client.post_to_profile(summary.strip(), repository_url)
            self.logger.info("LinkedIn post published successfully for repo: %s", repository_url)
            return result

        except LinkedInClientError as error:
            self.logger.exception("LinkedIn posting failed")
            raise ProcessingPipelineError(
                f"LinkedIn posting failed: {str(error)}"
            ) from error
        except Exception as error:
            self.logger.exception("Unexpected error during LinkedIn posting")
            raise ProcessingPipelineError(
                "Unexpected LinkedIn posting failure. See logs for details."
            ) from error

    def _extract_github_url(self, github_context: Union[str, Dict[str, Any]]) -> str:
        if isinstance(github_context, str):
            return github_context.strip()

        if isinstance(github_context, dict):
            candidates = [
                "repo_url",
                "repository_url",
                "url",
                "html_url",
                "source_url",
                "github_repo_url",
            ]
            for key in candidates:
                value = github_context.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()

        return ""

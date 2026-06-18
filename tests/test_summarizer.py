import pytest
from unittest.mock import Mock, patch, MagicMock
from backend.summarizer import (
    GoogleGeminiSummarizer,
    generate_summary,
    SummarizerError,
)


class TestGoogleGeminiSummarizer:
    """Tests for the GoogleGeminiSummarizer class."""
    
    @patch.dict("os.environ", {"GOOGLE_API_KEY": "test_api_key"})
    @patch("google.genai.Client")
    def test_init_with_env_key(self, mock_client_class):
        """Test initialization with environment variable API key."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        summarizer = GoogleGeminiSummarizer()
        assert summarizer.api_key == "test_api_key"
        mock_client_class.assert_called_once_with(api_key="test_api_key")
    
    @patch("google.genai.Client")
    def test_init_with_provided_key(self, mock_client_class):
        """Test initialization with provided API key."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        summarizer = GoogleGeminiSummarizer(api_key="provided_key")
        assert summarizer.api_key == "provided_key"
        mock_client_class.assert_called_once_with(api_key="provided_key")
    
    @patch.dict("os.environ", {}, clear=True)
    def test_init_without_api_key(self):
        """Test that missing API key raises error."""
        with pytest.raises(SummarizerError) as exc_info:
            GoogleGeminiSummarizer()
        assert "GOOGLE_API_KEY" in str(exc_info.value)
    
    @patch.dict("os.environ", {"GOOGLE_API_KEY": "test_key"})
    @patch("google.genai.Client")
    def test_build_prompt(self, mock_client_class):
        """Test prompt building."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        summarizer = GoogleGeminiSummarizer()
        prompt = summarizer._build_prompt("This is test text.")
        
        assert "summarize" in prompt.lower()
        assert "This is test text." in prompt
        assert "Document:" in prompt
    
    @patch.dict("os.environ", {"GOOGLE_API_KEY": "test_key"})
    @patch("google.genai.Client")
    def test_summarize_valid_text(self, mock_client_class):
        """Test summarization with valid text."""
        # Mock the client and response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "This is the summary."
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        summarizer = GoogleGeminiSummarizer()
        result = summarizer.summarize("This is a long document with important information.")
        
        assert result == "This is the summary."
        mock_client.models.generate_content.assert_called_once()
    
    @patch.dict("os.environ", {"GOOGLE_API_KEY": "test_key"})
    @patch("google.genai.Client")
    def test_summarize_empty_text(self, mock_client_class):
        """Test that empty text raises error."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        summarizer = GoogleGeminiSummarizer()
        with pytest.raises(SummarizerError) as exc_info:
            summarizer.summarize("")
        assert "non-empty string" in str(exc_info.value)
    
    @patch.dict("os.environ", {"GOOGLE_API_KEY": "test_key"})
    @patch("google.genai.Client")
    def test_summarize_short_text(self, mock_client_class):
        """Test that very short text raises error."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        summarizer = GoogleGeminiSummarizer()
        with pytest.raises(SummarizerError) as exc_info:
            summarizer.summarize("Short")
        assert "too short" in str(exc_info.value)
    
    @patch.dict("os.environ", {"GOOGLE_API_KEY": "test_key"})
    @patch("google.genai.Client")
    def test_summarize_invalid_input_type(self, mock_client_class):
        """Test that non-string input raises error."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        summarizer = GoogleGeminiSummarizer()
        with pytest.raises(SummarizerError) as exc_info:
            summarizer.summarize(None)
        assert "non-empty string" in str(exc_info.value)
    
    @patch.dict("os.environ", {"GOOGLE_API_KEY": "test_key"})
    @patch("google.genai.Client")
    def test_summarize_empty_response(self, mock_client_class):
        """Test handling of empty API response."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = ""
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        summarizer = GoogleGeminiSummarizer()
        with pytest.raises(SummarizerError) as exc_info:
            summarizer.summarize("This is valid text for summarization.")
        assert "Empty response" in str(exc_info.value)
    
    @patch.dict("os.environ", {"GOOGLE_API_KEY": "test_key"})
    @patch("google.genai.Client")
    def test_summarize_api_error(self, mock_client_class):
        """Test handling of API errors."""
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception("API Error")
        mock_client_class.return_value = mock_client
        
        summarizer = GoogleGeminiSummarizer()
        with pytest.raises(SummarizerError) as exc_info:
            summarizer.summarize("This is valid text for summarization.")
        assert "Failed to call Gemini API" in str(exc_info.value)
    
    @patch.dict("os.environ", {"GOOGLE_API_KEY": "test_key"})
    @patch("google.genai.types.GenerateContentConfig")
    @patch("google.genai.Client")
    def test_summarize_with_custom_tokens(self, mock_client_class, mock_config_class):
        """Test summarization with custom token limit."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Custom summary"
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client
        mock_config_class.return_value = MagicMock()
        
        summarizer = GoogleGeminiSummarizer()
        result = summarizer.summarize(
            "This is a long document with important information.",
            max_output_tokens=512
        )
        
        assert result == "Custom summary"
        # Verify that generate_content was called
        mock_client.models.generate_content.assert_called_once()


class TestGenerateSummary:
    """Tests for the generate_summary function."""
    
    @patch.dict("os.environ", {"GOOGLE_API_KEY": "test_key"})
    @patch("google.genai.Client")
    def test_generate_summary_valid_text(self, mock_client_class):
        """Test generate_summary wrapper function."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Generated summary"
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        result = generate_summary("This is a long document with important information.")
        assert result == "Generated summary"
    
    @patch.dict("os.environ", {"GOOGLE_API_KEY": "test_key"})
    @patch("google.genai.Client")
    def test_generate_summary_empty_text(self, mock_client_class):
        """Test that generate_summary handles empty text."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        with pytest.raises(SummarizerError):
            generate_summary("")
    
    @patch.dict("os.environ", {"GOOGLE_API_KEY": "test_key"})
    @patch("google.genai.Client")
    def test_generate_summary_invalid_text(self, mock_client_class):
        """Test that generate_summary handles invalid text."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        with pytest.raises(SummarizerError):
            generate_summary(None)


class TestSummarizerIntegration:
    """Integration tests for the summarizer."""
    
    @patch.dict("os.environ", {"GOOGLE_API_KEY": "test_key"})
    @patch("backend.summarizer._summarizer", None)
    @patch("google.genai.Client")
    def test_full_summarization_pipeline(self, mock_client_class):
        """Test full summarization pipeline with realistic text."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = """Summary:
        
- Key point 1: Main idea
- Key point 2: Supporting detail
- Key point 3: Conclusion"""
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        long_text = """This document discusses the importance of artificial intelligence in modern society.
        AI has revolutionized many industries including healthcare, finance, and transportation.
        Machine learning algorithms can process vast amounts of data quickly and accurately.
        Natural language processing enables computers to understand human language.
        Computer vision allows machines to interpret images and videos.
        These technologies are constantly evolving and improving.
        The future holds many possibilities for AI applications and development."""
        
        result = generate_summary(long_text)
        # The response should match what we mocked
        assert "Key point" in result
        assert len(result) > 0

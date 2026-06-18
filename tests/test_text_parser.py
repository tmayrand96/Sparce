import pytest
from backend.text_parser import (
    clean_text,
    tokenize_sentences,
    chunk_text,
    clean_and_structure,
    TextParsingError,
)


class TestCleanText:
    """Tests for the clean_text function."""
    
    def test_clean_text_basic(self):
        """Test basic text cleaning."""
        raw = "Hello  world  !!  This   is   a   test."
        result = clean_text(raw)
        assert "Hello" in result
        assert "world" in result
        assert result.count(" ") < raw.count(" ")
    
    def test_clean_text_removes_ocr_artifacts(self):
        """Test that OCR artifacts are removed."""
        raw = "This is text @#$% with weird chars"
        result = clean_text(raw)
        assert "@" not in result
        assert "#" not in result
        assert "$" not in result
        assert "%" not in result
    
    def test_clean_text_normalizes_line_endings(self):
        """Test that line endings are normalized."""
        raw = "Line 1\r\nLine 2\nLine 3"
        result = clean_text(raw)
        assert "\r\n" not in result
        assert "Line 1" in result
        assert "Line 2" in result
    
    def test_clean_text_removes_page_numbers(self):
        """Test that page numbers are removed."""
        raw = "This is page 01 with 02 numbers 03"
        result = clean_text(raw)
        assert "01" not in result
        assert "02" not in result
        assert "03" not in result
    
    def test_clean_text_empty_input(self):
        """Test that empty input raises error."""
        with pytest.raises(TextParsingError):
            clean_text("")
    
    def test_clean_text_invalid_input(self):
        """Test that non-string input raises error."""
        with pytest.raises(TextParsingError):
            clean_text(None)
        
        with pytest.raises(TextParsingError):
            clean_text(123)


class TestTokenizeSentences:
    """Tests for the tokenize_sentences function."""
    
    def test_tokenize_sentences_basic(self):
        """Test basic sentence tokenization."""
        text = "This is the first sentence. This is the second sentence."
        result = tokenize_sentences(text)
        assert len(result) == 2
        assert "first" in result[0]
        assert "second" in result[1]
    
    def test_tokenize_sentences_with_abbreviations(self):
        """Test tokenization with abbreviations."""
        text = "Dr. Smith went to the store. He bought milk."
        result = tokenize_sentences(text)
        assert len(result) >= 2
        assert any("Dr" in s for s in result)
        assert any("bought" in s for s in result)
    
    def test_tokenize_sentences_single_sentence(self):
        """Test tokenization of single sentence."""
        text = "This is only one sentence."
        result = tokenize_sentences(text)
        assert len(result) == 1
        assert "one sentence" in result[0]
    
    def test_tokenize_sentences_empty_input(self):
        """Test that empty input raises error."""
        with pytest.raises(TextParsingError):
            tokenize_sentences("")
    
    def test_tokenize_sentences_invalid_input(self):
        """Test that non-string input raises error."""
        with pytest.raises(TextParsingError):
            tokenize_sentences(None)


class TestChunkText:
    """Tests for the chunk_text function."""
    
    def test_chunk_text_basic(self):
        """Test basic text chunking."""
        sentences = ["Sentence 1.", "Sentence 2.", "Sentence 3.", 
                     "Sentence 4.", "Sentence 5."]
        result = chunk_text(sentences, chunk_size=2, overlap=0)
        assert len(result) >= 2
        assert "Sentence 1" in result[0]
    
    def test_chunk_text_with_overlap(self):
        """Test chunking with overlap."""
        sentences = ["Sentence 1.", "Sentence 2.", "Sentence 3.", 
                     "Sentence 4.", "Sentence 5."]
        result = chunk_text(sentences, chunk_size=2, overlap=1)
        # With overlap, first chunk should be different from second
        assert result[0] != result[1]
        assert "Sentence 1" in result[0]
        assert "Sentence 2" in result[1]
    
    def test_chunk_text_single_sentence(self):
        """Test chunking with single sentence."""
        sentences = ["This is a single sentence."]
        result = chunk_text(sentences, chunk_size=10)
        assert len(result) == 1
        assert "single" in result[0]
    
    def test_chunk_text_invalid_chunk_size(self):
        """Test that invalid chunk size raises error."""
        sentences = ["S1.", "S2.", "S3."]
        
        with pytest.raises(TextParsingError):
            chunk_text(sentences, chunk_size=0)
        
        with pytest.raises(TextParsingError):
            chunk_text(sentences, chunk_size=-1)
    
    def test_chunk_text_invalid_overlap(self):
        """Test that invalid overlap raises error."""
        sentences = ["S1.", "S2.", "S3."]
        
        with pytest.raises(TextParsingError):
            chunk_text(sentences, chunk_size=2, overlap=-1)
        
        with pytest.raises(TextParsingError):
            chunk_text(sentences, chunk_size=2, overlap=2)
    
    def test_chunk_text_empty_input(self):
        """Test that empty input raises error."""
        with pytest.raises(TextParsingError):
            chunk_text([])


class TestCleanAndStructure:
    """Tests for the clean_and_structure function."""
    
    def test_clean_and_structure_basic(self):
        """Test full pipeline with basic text."""
        raw = "This  is   the  first  sentence.  This is the second sentence."
        result = clean_and_structure(raw)
        assert isinstance(result, str)
        assert len(result) > 0
        assert "first" in result
        assert "second" in result
    
    def test_clean_and_structure_multiline(self):
        """Test full pipeline with multiline text."""
        raw = """This is the first paragraph.
        
This is the second paragraph with multiple sentences. 
It contains important information."""
        result = clean_and_structure(raw)
        assert isinstance(result, str)
        assert "first" in result
        assert "second" in result
    
    def test_clean_and_structure_with_ocr_artifacts(self):
        """Test full pipeline with OCR artifacts."""
        raw = "Th1s is t3xt w1th n01s3 @#$% and extra    spaces."
        result = clean_and_structure(raw)
        assert isinstance(result, str)
        # Text should be cleaned
        assert "@#$%" not in result
    
    def test_clean_and_structure_empty_input(self):
        """Test that empty input raises error."""
        with pytest.raises(TextParsingError):
            clean_and_structure("")
    
    def test_clean_and_structure_preserves_content(self):
        """Test that important content is preserved."""
        raw = "Date: 2025-01-01. Amount: $1000. Contact: john.doe@example.com"
        result = clean_and_structure(raw)
        # Check that key info is preserved (some special chars may be removed)
        assert "Date" in result or "date" in result.lower()

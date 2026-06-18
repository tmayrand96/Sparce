import re
from typing import List
import nltk
from nltk.tokenize import sent_tokenize

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('punkt_tab', quiet=True)


class TextParsingError(Exception):
    """Custom exception for text parsing failures."""
    pass


def clean_text(raw_text: str) -> str:
    """
    Cleans OCR artifacts and normalizes whitespace.
    
    Args:
        raw_text: Raw text extracted from OCR.
        
    Returns:
        Cleaned text with normalized whitespace and removed artifacts.
    """
    if not raw_text or not isinstance(raw_text, str):
        raise TextParsingError("Input text must be a non-empty string")
    
    # Remove common OCR artifacts and special characters
    text = raw_text
    
    # Remove extra whitespace characters and normalize line breaks
    text = re.sub(r'\r\n', '\n', text)  # Normalize line endings
    text = re.sub(r'\n\n+', '\n', text)  # Remove multiple consecutive newlines
    text = re.sub(r'[ \t]+', ' ', text)  # Normalize spaces and tabs
    
    # Remove common OCR noise patterns
    text = re.sub(r'[^\w\s\.\,\!\?\;\:\-\n]', '', text)  # Keep only alphanumeric and common punctuation
    
    # Remove page numbers like "01", "02"
    text = re.sub(r'\b0[0-9]\b', '', text)
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    return text


def tokenize_sentences(cleaned_text: str) -> List[str]:
    """
    Tokenizes text into sentences using NLTK.
    
    Args:
        cleaned_text: Cleaned text ready for tokenization.
        
    Returns:
        List of sentences.
    """
    if not cleaned_text or not isinstance(cleaned_text, str):
        raise TextParsingError("Input text must be a non-empty string")
    
    try:
        sentences = sent_tokenize(cleaned_text)
        # Filter out empty sentences
        sentences = [s.strip() for s in sentences if s.strip()]
        return sentences
    except Exception as e:
        raise TextParsingError(f"Sentence tokenization failed: {str(e)}")


def chunk_text(sentences: List[str], chunk_size: int = 10, overlap: int = 2) -> List[str]:
    """
    Chunks sentences into groups for LLM context windows.
    Uses sliding window approach with overlap to preserve context.
    
    Args:
        sentences: List of tokenized sentences.
        chunk_size: Number of sentences per chunk.
        overlap: Number of overlapping sentences between chunks.
        
    Returns:
        List of text chunks.
    """
    if not sentences:
        raise TextParsingError("Sentence list cannot be empty")
    
    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
        raise TextParsingError("chunk_size must be > 0, and 0 <= overlap < chunk_size")
    
    chunks = []
    stride = chunk_size - overlap
    
    for i in range(0, len(sentences), stride):
        chunk = sentences[i:i + chunk_size]
        if chunk:  # Only add non-empty chunks
            chunks.append(' '.join(chunk))
    
    return chunks


def clean_and_structure(raw_text: str) -> str:
    """
    Orchestrates the full text cleaning and structuring pipeline.
    
    Args:
        raw_text: Raw text extracted from OCR.
        
    Returns:
        Cleaned and structured text ready for summarization.
    """
    try:
        # Step 1: Clean the raw text
        cleaned = clean_text(raw_text)
        
        # Step 2: Tokenize into sentences
        sentences = tokenize_sentences(cleaned)
        
        # Step 3: Chunk with overlap for context preservation
        chunks = chunk_text(sentences, chunk_size=10, overlap=2)
        
        # Step 4: Combine chunks into structured text
        # For now, we join them back with clear separation for the summarizer
        structured_text = '\n\n'.join(chunks)
        
        return structured_text
    except TextParsingError as e:
        raise TextParsingError(f"Text parsing pipeline failed: {str(e)}")
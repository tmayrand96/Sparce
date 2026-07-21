import time
from typing import Optional

import google.genai as genai
from google.genai import errors

from backend.token_provider import BaseTokenProvider, EnvTokenProvider


class SummarizerError(Exception):
    """Custom exception for summarization failures."""
    pass


class GoogleGeminiSummarizer:
    """Handles text summarization using Google Gemini API."""

    def __init__(
        self,
        provider: Optional[BaseTokenProvider] = None,
        api_key: Optional[str] = None,
        model: str = "gemini-3.1-flash-lite",
    ):
        """
        Initialize the Gemini summarizer.

        Args:
            provider: Token provider used to resolve the API key.
            api_key: Google API key. If provided, it overrides the provider.
            model: Gemini model to use.
        """
        self.provider = provider or EnvTokenProvider()

        try:
            resolved_api_key = api_key or self.provider.get_token()
        except ValueError as exc:
            raise SummarizerError(
                "GOOGLE_API_KEY environment variable not set. "
                "Please set your Google API key to use the summarizer."
            ) from exc

        self.api_key = resolved_api_key
        self.model_name = model
        self.client = genai.Client(api_key=self.api_key)
    
    def _build_prompt(self, text: str) -> str:
        """
        Build an optimized prompt for document summarization.
        
        Args:
            text: The text to summarize.
            
        Returns:
            Formatted prompt string.
        """
        prompt = f"""You are a professional document summarizer. 
Analyze the following document and provide a concise, well-structured summary.

Guidelines:
- Capture the main points and key information
- Maintain clarity and accuracy
- Keep the summary to 2-4 paragraphs
- Use bullet points for lists of items
- Preserve important numbers, dates, and names
- Write in a professional tone
- CRITICAL: Provide the final summary in the same language the document is written in (e.g., if the text is in French, respond in French).

Document:
{text}

Summary:"""
        return prompt
    
    def summarize(self, text: str, max_output_tokens: Optional[int] = None) -> str:
        """
        Summarize the given text using Gemini API with automatic rate-limit throttling.
        
        Args:
            text: The text to summarize.
            max_output_tokens: Maximum tokens for the response (default: 1024).
            
        Returns:
            Summary text.
            
        Raises:
            SummarizerError: If API call fails or text is invalid.
        """
        if not text or not isinstance(text, str):
            raise SummarizerError("Input text must be a non-empty string")
        
        if len(text.strip()) < 20:
            raise SummarizerError("Text is too short to summarize (minimum 20 characters)")
        
        max_retries = 3
        base_delay = 21  # Default fallback wait time
        
        for attempt in range(max_retries):
            try:
                prompt = self._build_prompt(text)
                
                # Configure generation settings
                generation_config = {
                    "max_output_tokens": max_output_tokens or 1024,
                    "temperature": 0.7,
                    "top_p": 0.95,
                }
                
                # Call the API
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=genai.types.GenerateContentConfig(**generation_config)
                )
                
                if not response or not response.text:
                    raise SummarizerError("Empty response from Gemini API")
                
                return response.text.strip()
                
            except errors.ClientError as e:
                # Catch the 429 Rate Limit error dynamically
                if e.code == 429:
                    print(f"\n[Sparce Auto-Throttle] Hit Gemini rate limit (Attempt {attempt + 1}/{max_retries}).")
                    
                    # Parse out the dynamic wait window from the Google server message
                    try:
                        retry_delay = int(float(e.message.split("Please retry in ")[1].split("s")[0]))
                    except Exception:
                        retry_delay = base_delay
                    
                    # Add a 2-second safety buffer to ensure the gate is open
                    wait_time = retry_delay + 2
                    print(f"Pacing pipeline... Sleeping for {wait_time} seconds before automatic retry.")
                    time.sleep(wait_time)
                    continue  # Loop back up and try the generation again
                
                # Re-raise any other client-side error immediately
                raise SummarizerError(f"Gemini API Client Error: {str(e)}")
                
            except SummarizerError:
                raise
            except Exception as e:
                raise SummarizerError(
                    f"Failed to call Gemini API: {str(e)}"
                )
                
        raise SummarizerError("Failed to clear Gemini rate limits after multiple automated retries.")


# Global summarizer instance
_summarizer = None


def _get_summarizer(provider: Optional[BaseTokenProvider] = None) -> GoogleGeminiSummarizer:
    """Get or initialize the global summarizer instance."""
    global _summarizer
    if _summarizer is None:
        _summarizer = GoogleGeminiSummarizer(provider=provider)
    return _summarizer


def generate_summary(cleaned_text: str, provider: Optional[BaseTokenProvider] = None) -> str:
    """
    Orchestrates LLM API call to return the finalized document summary.
    
    Args:
        cleaned_text: Cleaned and structured text ready for summarization.
        
    Returns:
        Generated summary.
        
    Raises:
        SummarizerError: If summarization fails.
    """
    try:
        summarizer = _get_summarizer(provider=provider)
        
        # --- PRE-FLIGHT TOKEN COUNT ---
        if hasattr(summarizer, 'client'):
            token_check = summarizer.client.models.count_tokens(
                model=summarizer.model_name,
                contents=cleaned_text
            )
            total_tokens = getattr(token_check, "total_tokens", None)
            if not isinstance(total_tokens, int):
                total_tokens = 0
            print(f"DEBUG [Pre-flight]: Input payload size is {total_tokens} tokens.")

            if total_tokens > 1000000:
                print("WARNING: This payload risks hitting your Per-Minute Token Quota!")
        # ----------------------------------------

        return summarizer.summarize(cleaned_text)
        
    except SummarizerError as e:
        raise SummarizerError(f"Summarization failed: {str(e)}")
    except Exception as e:
        raise SummarizerError(f"Unexpected error during summarization: {str(e)}")
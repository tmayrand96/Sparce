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
    
    def _build_prompt(
        self,
        text: str,
        user_prompt: Optional[str] = None,
        challenge_mode: bool = False,
        system_instruction: Optional[str] = None,
    ) -> str:
        """
        Build an optimized prompt for document summarization.
        
        Args:
            text: The text to summarize.
            user_prompt: Optional user-specified question or instruction.
            challenge_mode: If enabled, injects a critical thinking modifier.
            system_instruction: Optional override for the final prompt instruction.
            
        Returns:
            Formatted prompt string.
        """
        if system_instruction and system_instruction.strip():
            instruction = system_instruction.strip()
        elif user_prompt and user_prompt.strip():
            instruction = (
                f"Analyze the following document and answer the user's request: {user_prompt.strip()}"
            )
        else:
            instruction = "Analyze the following document and provide a concise, well-structured summary."

        if challenge_mode:
            instruction += (
                " In addition to synthesizing this document, act as a rigorous thought partner. "
                "Explicitly challenge the core assumptions, logical leaps, potential blind spots, and underlying premises presented in the text. "
                "Provide constructive counter-arguments and pose 2-3 deep, probing questions to test the thesis."
            )

        prompt = f"""You are a professional document summarizer.
{instruction}

Guidelines:
- Capture the main points and key information
- Maintain clarity and accuracy
- Keep the response concise, ideally under 1000 characters
- Use bullet points for lists of items when helpful
- Preserve important numbers, dates, and names
- Write in a professional tone
- CRITICAL: Provide the final response in the same language the document is written in (e.g., if the text is in French, respond in French).

Document:
{text}

Summary:"""
        return prompt
    
    def summarize(
        self,
        text: str,
        max_output_tokens: Optional[int] = None,
        user_prompt: Optional[str] = None,
        challenge_mode: bool = False,
        system_instruction: Optional[str] = None,
    ) -> str:
        """
        Summarize the given text using Gemini API with automatic rate-limit throttling.
        
        Args:
            text: The text to summarize.
            max_output_tokens: Maximum tokens for the response (default: 1024).
            user_prompt: Optional user-specified question or instruction.
            challenge_mode: If enabled, apply critical analysis prompt injection.
            system_instruction: Optional override for the top-level prompt.
            
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
                prompt = self._build_prompt(
                    text,
                    user_prompt=user_prompt,
                    challenge_mode=challenge_mode,
                    system_instruction=system_instruction,
                )
                
                # Configure generation settings
                max_output = max_output_tokens or 300
                generation_config = {
                    "max_output_tokens": max_output,
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


def generate_summary(
    cleaned_text: str,
    provider: Optional[BaseTokenProvider] = None,
    user_prompt: Optional[str] = None,
    max_output_tokens: Optional[int] = None,
    challenge_mode: bool = False,
    system_instruction: Optional[str] = None,
) -> str:
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

        return summarizer.summarize(
            cleaned_text,
            max_output_tokens=max_output_tokens,
            user_prompt=user_prompt,
            challenge_mode=challenge_mode,
            system_instruction=system_instruction,
        )
        
    except SummarizerError as e:
        raise SummarizerError(f"Summarization failed: {str(e)}")
    except Exception as e:
        raise SummarizerError(f"Unexpected error during summarization: {str(e)}")
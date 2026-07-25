"""
Google Gemini LLM Provider — uses the Google Generative AI SDK.
Free tier: gemini-2.0-flash
"""

import time
from typing import Optional
import google.generativeai as genai

from .base import BaseLLMProvider, LLMResponse
from ..config import get_settings


class GeminiProvider(BaseLLMProvider):
    """Google Gemini API provider."""

    def __init__(self, model_name: str = "gemini-2.0-flash"):
        super().__init__(provider_name="gemini", model_name=model_name)
        settings = get_settings()
        self.api_key = settings.GEMINI_API_KEY

        if self.api_key:
            genai.configure(api_key=self.api_key)
            self._model = genai.GenerativeModel(model_name)
            self._is_available = True
        else:
            self._model = None
            self._is_available = False

    async def generate(self, prompt: str, max_tokens: int = 2048) -> LLMResponse:
        """Generate response from Gemini."""
        if not self._is_available:
            return self._create_error_response("Gemini API key not configured")

        try:
            start = time.time()
            response = self._model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    max_output_tokens=max_tokens,
                    temperature=0.1,  # Low temperature for SQL precision
                ),
            )
            latency = (time.time() - start) * 1000

            content = response.text if response.text else ""
            content = self._extract_sql(content)

            return LLMResponse(
                provider=self.provider_name,
                model=self.model_name,
                content=content,
                is_success=True,
                latency_ms=latency,
            )
        except Exception as e:
            return self._create_error_response(f"Gemini error: {str(e)}")

    async def health_check(self) -> bool:
        """Check if Gemini API is available."""
        if not self._is_available:
            return False
        try:
            response = self._model.generate_content("SELECT 1")
            return bool(response.text)
        except Exception:
            return False

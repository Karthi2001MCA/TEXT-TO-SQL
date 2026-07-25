"""
Groq LLM Provider — fast inference for open-source models.
Supports: Llama 3.3, Mixtral, Gemma 2, Qwen.
"""

import time
from groq import Groq

from .base import BaseLLMProvider, LLMResponse
from ..config import get_settings


class GroqProvider(BaseLLMProvider):
    """Groq API provider for open-source models."""

    def __init__(self, model_name: str = "llama-3.3-70b-versatile"):
        super().__init__(provider_name="groq", model_name=model_name)
        settings = get_settings()
        self.api_key = settings.GROQ_API_KEY

        if self.api_key:
            self._client = Groq(api_key=self.api_key)
            self._is_available = True
        else:
            self._client = None
            self._is_available = False

    async def generate(self, prompt: str, max_tokens: int = 2048) -> LLMResponse:
        """Generate response from Groq."""
        if not self._is_available:
            return self._create_error_response("Groq API key not configured")

        try:
            start = time.time()
            response = self._client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are an expert SQL analyst. Return only SQL queries, no explanations."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=max_tokens,
                temperature=0.1,
            )
            latency = (time.time() - start) * 1000

            content = response.choices[0].message.content or ""
            content = self._extract_sql(content)
            tokens = response.usage.total_tokens if response.usage else 0

            return LLMResponse(
                provider=self.provider_name,
                model=self.model_name,
                content=content,
                is_success=True,
                latency_ms=latency,
                tokens_used=tokens,
            )
        except Exception as e:
            return self._create_error_response(f"Groq error: {str(e)}")

    async def health_check(self) -> bool:
        """Check if Groq API is available."""
        if not self._is_available:
            return False
        try:
            response = self._client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": "SELECT 1"}],
                max_tokens=10,
            )
            return bool(response.choices)
        except Exception:
            return False

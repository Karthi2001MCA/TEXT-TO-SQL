"""
Generic provider for any service exposing an OpenAI-compatible chat API.

Groq, DeepSeek, OpenRouter, Cerebras, Mistral and GitHub Models all speak the
same protocol, so they differ only by base URL, key and model id.
"""

import time
from typing import Optional

from openai import OpenAI

from .base import BaseLLMProvider, LLMResponse

SQL_SYSTEM_PROMPT = "You are an expert SQL analyst. Return only SQL queries, no explanations."


class OpenAICompatibleProvider(BaseLLMProvider):
    """Provider for any OpenAI-compatible /chat/completions endpoint."""

    def __init__(
        self,
        provider_name: str,
        model_name: str,
        api_key: Optional[str],
        base_url: str,
        extra_headers: Optional[dict] = None,
    ):
        super().__init__(provider_name=provider_name, model_name=model_name)
        self.base_url = base_url
        self.extra_headers = extra_headers or {}

        if api_key:
            self._client = OpenAI(api_key=api_key, base_url=base_url)
            self._is_available = True
        else:
            self._client = None
            self._is_available = False

    async def generate(self, prompt: str, max_tokens: int = 2048) -> LLMResponse:
        """Generate a response from the configured model."""
        if not self._is_available:
            return self._create_error_response(
                f"{self.provider_name} API key not configured"
            )

        try:
            start = time.time()
            response = self._client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": SQL_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=max_tokens,
                temperature=0.1,
                extra_headers=self.extra_headers or None,
            )
            latency = (time.time() - start) * 1000

            content = self._extract_sql(response.choices[0].message.content or "")
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
            return self._create_error_response(f"{self.provider_name} error: {str(e)}")

    async def health_check(self) -> bool:
        """Check whether the endpoint responds."""
        if not self._is_available:
            return False
        try:
            response = self._client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": "SELECT 1"}],
                max_tokens=10,
                extra_headers=self.extra_headers or None,
            )
            return bool(response.choices)
        except Exception:
            return False

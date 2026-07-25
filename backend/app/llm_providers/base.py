"""
Abstract base class for all LLM providers.
Each provider must implement the generate() method.
"""

import re
from abc import ABC, abstractmethod
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class LLMResponse:
    """Standardized response from any LLM provider."""
    provider: str
    model: str
    content: str
    is_success: bool = True
    error: Optional[str] = None
    latency_ms: float = 0.0
    tokens_used: int = 0
    metadata: dict = field(default_factory=dict)


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, provider_name: str, model_name: str):
        self.provider_name = provider_name
        self.model_name = model_name
        self._is_available = False

    @abstractmethod
    async def generate(self, prompt: str, max_tokens: int = 2048) -> LLMResponse:
        """Generate a response from the LLM given a prompt."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider is available and responding."""
        pass

    @property
    def is_available(self) -> bool:
        return self._is_available

    def _create_error_response(self, error: str) -> LLMResponse:
        """Create a standardized error response."""
        return LLMResponse(
            provider=self.provider_name,
            model=self.model_name,
            content="",
            is_success=False,
            error=error,
        )

    def _extract_sql(self, raw_response: str) -> str:
        """
        Extract clean SQL from an LLM response.
        Handles markdown fences, surrounding prose, and the <think> scratchpad
        blocks that reasoning models (e.g. Qwen) emit before their answer.
        """
        text = (raw_response or "").strip()

        # Drop reasoning scratchpads, including an unterminated one (model hit max_tokens)
        text = re.sub(r"<think>.*?</think>", " ", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<think>.*$", " ", text, flags=re.DOTALL | re.IGNORECASE).strip()

        # Prefer a fenced code block wherever it appears in the response
        fence = re.search(r"```(?:sql)?\s*(.+?)```", text, flags=re.DOTALL | re.IGNORECASE)
        if fence:
            text = fence.group(1)
        else:
            # Otherwise start at the first statement keyword, discarding any preamble
            start = re.search(r"\b(WITH|SELECT)\b", text, flags=re.IGNORECASE)
            if start:
                text = text[start.start():]

        # Remove trailing semicolons (we add them ourselves)
        return text.strip().rstrip(";").strip()

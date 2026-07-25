"""
Multi-LLM Consensus Engine — orchestrates multiple LLMs, validates,
ranks, and selects the best SQL query.
"""

import asyncio
import time
from typing import List, Optional

from ..llm_providers.base import BaseLLMProvider, LLMResponse
from ..llm_providers.gemini_provider import GeminiProvider
from ..llm_providers.groq_provider import GroqProvider
from ..llm_providers.deepseek_provider import DeepSeekProvider
from ..llm_providers.ollama_provider import OllamaProvider
from ..llm_providers.openai_compatible_provider import OpenAICompatibleProvider
from ..config import get_settings

settings = get_settings()

# Groq models used for the consensus panel — deliberately from different families
# (Meta / OpenAI / Alibaba) so their failure modes are not correlated.
GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "openai/gpt-oss-120b",
    "qwen/qwen3.6-27b",
    "llama-3.1-8b-instant",
]

# Additional OpenAI-compatible providers, all of which have a no-card free tier.
# Each activates only when its key is present in .env, so leaving a key blank
# simply leaves that provider out of the panel.
#
# Model ids drift — if a provider starts returning "model not found", check its
# docs and update the list here.
OPENAI_COMPATIBLE_PROVIDERS = [
    {
        # openrouter.ai/keys — ':free' models cost nothing
        "name": "openrouter",
        "base_url": "https://openrouter.ai/api/v1",
        "models": [
            "google/gemma-4-31b-it:free",
            "cohere/north-mini-code:free",
            "nvidia/nemotron-3-super-120b-a12b:free",
        ],
        "extra_headers": {"X-Title": "Enterprise AI Data Assistant"},
    },
    {
        # github.com/settings/tokens — free with any GitHub account
        "name": "github",
        "base_url": "https://models.github.ai/inference",
        "models": [
            "meta/llama-3.3-70b-instruct",
            "mistral-ai/codestral-2501",
            "microsoft/phi-4",
        ],
    },
    {
        # cloud.cerebras.ai — free tier, very fast inference
        "name": "cerebras",
        "base_url": "https://api.cerebras.ai/v1",
        "models": ["llama-3.3-70b"],
    },
    {
        # console.mistral.ai — free experimental tier
        "name": "mistral",
        "base_url": "https://api.mistral.ai/v1",
        "models": ["mistral-small-latest"],
    },
]


class MultiLLMEngine:
    """
    Orchestrates SQL generation across multiple LLMs.
    Sends the prompt to all available providers in parallel,
    collects responses, and returns them for validation/ranking.
    """

    def __init__(self):
        self.providers: List[BaseLLMProvider] = []
        self._initialize_providers()

    def _initialize_providers(self):
        """Initialize providers that have a usable (non-placeholder) API key."""
        # Gemini
        if settings.gemini_key:
            self.providers.append(GeminiProvider())

        # Groq — register multiple models for diverse responses.
        # Verify IDs against https://console.groq.com/docs/models before changing;
        # Groq decommissions models (gemma2-9b-it and mixtral-8x7b-32768 are gone).
        if settings.groq_key:
            for model in GROQ_MODELS:
                self.providers.append(GroqProvider(model_name=model))

        # DeepSeek
        if settings.deepseek_key:
            self.providers.append(DeepSeekProvider())

        # Free-tier OpenAI-compatible providers (OpenRouter, GitHub Models, ...)
        for spec in OPENAI_COMPATIBLE_PROVIDERS:
            api_key = settings.usable_key(spec["name"])
            if not api_key:
                continue
            for model in spec["models"]:
                self.providers.append(
                    OpenAICompatibleProvider(
                        provider_name=spec["name"],
                        model_name=model,
                        api_key=api_key,
                        base_url=spec["base_url"],
                        extra_headers=spec.get("extra_headers"),
                    )
                )

        # Ollama (local — always added, availability checked at runtime)
        self.providers.append(OllamaProvider())

    def get_available_providers(self) -> List[dict]:
        """Get info about all registered providers."""
        return [
            {
                "provider": p.provider_name,
                "model": p.model_name,
                "is_available": p.is_available,
            }
            for p in self.providers
        ]

    async def generate_sql_from_all(
        self,
        prompt: str,
        timeout_seconds: float = 30.0,
    ) -> List[LLMResponse]:
        """
        Send the SQL generation prompt to ALL available providers in parallel.
        Returns list of LLMResponse objects (including failures).
        """
        if not self.providers:
            return []

        tasks = []
        for provider in self.providers:
            if provider.is_available:
                task = asyncio.create_task(
                    self._generate_with_timeout(provider, prompt, timeout_seconds)
                )
                tasks.append(task)

        if not tasks:
            return []

        # Execute all in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        responses = []
        for result in results:
            if isinstance(result, LLMResponse):
                responses.append(result)
            elif isinstance(result, Exception):
                responses.append(LLMResponse(
                    provider="unknown",
                    model="unknown",
                    content="",
                    is_success=False,
                    error=str(result),
                ))

        return responses

    async def _generate_with_timeout(
        self,
        provider: BaseLLMProvider,
        prompt: str,
        timeout: float,
    ) -> LLMResponse:
        """Generate SQL with a timeout wrapper."""
        try:
            return await asyncio.wait_for(
                provider.generate(prompt), timeout=timeout
            )
        except asyncio.TimeoutError:
            return LLMResponse(
                provider=provider.provider_name,
                model=provider.model_name,
                content="",
                is_success=False,
                error=f"Timeout after {timeout}s",
            )

    async def generate_insight(self, prompt: str) -> str:
        """Generate insight text using the first available provider."""
        for provider in self.providers:
            if provider.is_available:
                response = await provider.generate(prompt)
                if response.is_success and response.content:
                    return response.content
        return "Unable to generate insights — no LLM providers available."

    async def generate_chart_recommendation(self, prompt: str) -> str:
        """Generate chart recommendation using the first available provider."""
        for provider in self.providers:
            if provider.is_available:
                response = await provider.generate(prompt)
                if response.is_success and response.content:
                    return response.content
        return '{"chart_type": "table", "title": "Query Results"}'


# Singleton instance
_engine: Optional[MultiLLMEngine] = None


def get_llm_engine() -> MultiLLMEngine:
    """Get the singleton Multi-LLM Engine instance."""
    global _engine
    if _engine is None:
        _engine = MultiLLMEngine()
    return _engine

"""
DeepSeek LLM Provider — uses OpenAI-compatible API.
Note: DeepSeek has no free tier; the account needs a positive balance.
"""

from .openai_compatible_provider import OpenAICompatibleProvider
from ..config import get_settings


class DeepSeekProvider(OpenAICompatibleProvider):
    """DeepSeek API provider (OpenAI-compatible)."""

    def __init__(self, model_name: str = "deepseek-chat"):
        settings = get_settings()
        super().__init__(
            provider_name="deepseek",
            model_name=model_name,
            api_key=settings.deepseek_key,
            base_url="https://api.deepseek.com/v1",
        )

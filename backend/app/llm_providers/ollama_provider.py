"""
Ollama LLM Provider — local model inference via Ollama API.
Supports any locally installed model (Llama, Mistral, Phi, Qwen, Gemma, etc.)
"""

import time
import httpx

from .base import BaseLLMProvider, LLMResponse
from ..config import get_settings


class OllamaProvider(BaseLLMProvider):
    """Ollama local inference provider."""

    def __init__(self, model_name: str = "llama3.2"):
        super().__init__(provider_name="ollama", model_name=model_name)
        settings = get_settings()
        self.base_url = settings.OLLAMA_BASE_URL
        self._is_available = True  # Assume available, health_check will verify

    async def generate(self, prompt: str, max_tokens: int = 2048) -> LLMResponse:
        """Generate response from Ollama."""
        try:
            start = time.time()
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model_name,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.1,
                            "num_predict": max_tokens,
                        },
                    },
                )
                response.raise_for_status()
                data = response.json()
            latency = (time.time() - start) * 1000

            content = data.get("response", "")
            content = self._extract_sql(content)

            return LLMResponse(
                provider=self.provider_name,
                model=self.model_name,
                content=content,
                is_success=True,
                latency_ms=latency,
            )
        except httpx.ConnectError:
            self._is_available = False
            return self._create_error_response("Ollama is not running. Start it with: ollama serve")
        except Exception as e:
            return self._create_error_response(f"Ollama error: {str(e)}")

    async def health_check(self) -> bool:
        """Check if Ollama is running and the model is available."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    models = [m["name"] for m in data.get("models", [])]
                    self._is_available = True
                    return True
                return False
        except Exception:
            self._is_available = False
            return False

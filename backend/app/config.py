"""
Configuration module using Pydantic Settings.
Loads environment variables from .env file.
"""

from pydantic_settings import BaseSettings
from typing import Optional, List
from functools import lru_cache
import os

# A key straight out of .env.example is not a usable key. Treating these as
# configured makes the app claim providers it cannot actually reach.
PLACEHOLDER_KEY_MARKERS = ("your-", "your_", "yourkey", "changeme", "replace-me", "xxx", "<")

# Provider name -> the settings field holding its API key.
# Ollama is absent because it is local and needs no key.
LLM_KEY_FIELDS = {
    "gemini": "GEMINI_API_KEY",
    "groq": "GROQ_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "openai": "OPENAI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "cerebras": "CEREBRAS_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "github": "GITHUB_MODELS_TOKEN",
}


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # --- Application ---
    APP_NAME: str = "Enterprise AI Data Assistant"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # --- Database ---
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/app.db"
    DATA_DATABASE_URL: str = "sqlite+aiosqlite:///./data/user_data.db"

    # --- LLM API Keys ---
    GEMINI_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    DEEPSEEK_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None

    # --- Free-tier providers (no card required) ---
    OPENROUTER_API_KEY: Optional[str] = None
    CEREBRAS_API_KEY: Optional[str] = None
    MISTRAL_API_KEY: Optional[str] = None
    GITHUB_MODELS_TOKEN: Optional[str] = None

    # --- Ollama (Local) ---
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # --- RAG Settings ---
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    VECTOR_DB_PATH: str = "./data/vector_store"
    CHUNK_SIZE: int = 500
    TOP_K_RESULTS: int = 5

    # --- Rate Limiting ---
    RATE_LIMIT: str = "100/minute"

    # --- CORS ---
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    # --- File Upload ---
    MAX_UPLOAD_SIZE_MB: int = 50
    UPLOAD_DIR: str = "./data/uploads"

    # --- Paths ---
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

    # --- API key helpers ---

    @staticmethod
    def is_real_key(value: Optional[str]) -> bool:
        """True if the value looks like an actual API key rather than a placeholder."""
        if not value:
            return False
        candidate = value.strip().lower()
        if len(candidate) < 10:
            return False
        return not any(marker in candidate for marker in PLACEHOLDER_KEY_MARKERS)

    def usable_key(self, provider: str) -> Optional[str]:
        """Return the configured key for a provider, or None if missing/placeholder."""
        field = LLM_KEY_FIELDS.get(provider)
        value = getattr(self, field, None) if field else None
        return value if self.is_real_key(value) else None

    @property
    def gemini_key(self) -> Optional[str]:
        return self.usable_key("gemini")

    @property
    def groq_key(self) -> Optional[str]:
        return self.usable_key("groq")

    @property
    def deepseek_key(self) -> Optional[str]:
        return self.usable_key("deepseek")

    @property
    def openai_key(self) -> Optional[str]:
        return self.usable_key("openai")

    def get_available_llm_providers(self) -> List[str]:
        """Return list of providers with a usable (non-placeholder) API key."""
        providers = [name for name in LLM_KEY_FIELDS if self.usable_key(name)]
        # Ollama needs no key — availability is checked at runtime
        providers.append("ollama")
        return providers


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

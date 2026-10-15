"""Apollo Application Configuration."""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APOLLO_ENV: str = "development"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # SEC EDGAR Requirements
    SEC_USER_AGENT: str = "ApolloResearch/1.0 (research@example.com)"
    SEC_RATE_LIMIT_PER_SEC: float = 5.0
    SEC_TIMEOUT_SECONDS: float = 15.0

    # Bounded Autonomy Limits
    MAX_FOLLOWUP_ROUNDS: int = 3
    MAX_RETRIEVAL_REQUESTS_PER_RUN: int = 20

    # Persistence
    DATABASE_URL: str = "sqlite:///./apollo_research.db"

    # Authentication & Multi-Tenancy
    AUTH_SECRET_KEY: str = "apollo-sec-research-super-secret-key-prod-01"
    AUTH_ALGORITHM: str = "HS256"
    AUTH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    REQUIRE_AUTH: bool = False

    # LLM Provider
    DEFAULT_LLM_PROVIDER: str = "ollama"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "gemma4:latest"

    # Artifact Storage
    REPORT_OUTPUT_DIR: Path = Path("./reports")


settings = Settings()

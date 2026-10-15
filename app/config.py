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

    # Plugin Execution Deadlines & Security
    PLUGIN_EXECUTION_TIMEOUT_SECONDS: float = 30.0
    FAIL_CLOSED_CAPABILITY_POLICY: bool = False

    @property
    def is_production(self) -> bool:
        return self.APOLLO_ENV.strip().lower() in ("production", "prod")

    def model_post_init(self, __context: object) -> None:
        if self.is_production:
            # Enforce fail-closed security invariants in production
            if not self.REQUIRE_AUTH:
                raise ValueError("Production configuration violation: REQUIRE_AUTH cannot be disabled in production.")

            unsafe_keys = {
                "apollo-sec-research-super-secret-key-prod-01",
                "secret",
                "changeme",
                "admin",
            }
            key_lower = self.AUTH_SECRET_KEY.lower()
            if (
                self.AUTH_SECRET_KEY in unsafe_keys
                or "change-in-prod" in key_lower
                or "default-secret" in key_lower
                or len(self.AUTH_SECRET_KEY.strip()) < 32
            ):
                raise ValueError(
                    "Production configuration violation: Default or insecure AUTH_SECRET_KEY is prohibited in production. "
                    "AUTH_SECRET_KEY must be at least 32 characters and cryptographically secure."
                )

            if "example.com" in self.SEC_USER_AGENT or not self.SEC_USER_AGENT.strip():
                raise ValueError(
                    "Production configuration violation: Default SEC_USER_AGENT is prohibited in production. "
                    "Must specify valid institutional contact information per SEC EDGAR regulations."
                )


settings = Settings()


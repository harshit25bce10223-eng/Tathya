import warnings
from typing import Literal, Self

from pydantic import (
    EmailStr,
    HttpUrl,
    PostgresDsn,
    computed_field,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Support .env from project root or inside backend
        env_file=[".env", "../.env"],
        env_ignore_empty=True,
        extra="ignore",
    )
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "changethis_secret_key_at_least_32_chars_long"
    # 60 minutes * 24 hours * 8 days = 8 days
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    FRONTEND_HOST: str = "http://localhost:5173"
    FASTAPI_ENV: Literal["development"] | None = None

    PROJECT_NAME: str = "Tathya Fact Verification Engine"
    SENTRY_DSN: HttpUrl | None = None
    DATABASE_URL: PostgresDsn = PostgresDsn(
        "postgresql+psycopg://postgres:changethis@localhost:5432/app"
    )

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def _use_psycopg_driver(cls, value: str | PostgresDsn) -> str:
        database_url = str(value)
        for scheme in ("postgres://", "postgresql://"):
            if database_url.startswith(scheme):
                return database_url.replace(scheme, "postgresql+psycopg://", 1)
        return database_url

    SMTP_TLS: bool = True
    SMTP_SSL: bool = False
    SMTP_PORT: int = 587
    SMTP_HOST: str | None = None
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    EMAILS_FROM_EMAIL: EmailStr | None = "info@example.com"
    EMAILS_FROM_NAME: str | None = None

    @model_validator(mode="after")
    def _set_default_emails_from(self) -> Self:
        if not self.EMAILS_FROM_NAME:
            self.EMAILS_FROM_NAME = self.PROJECT_NAME
        if not self.EMAILS_FROM_EMAIL:
            self.EMAILS_FROM_EMAIL = "info@example.com"
        return self

    EMAIL_RESET_TOKEN_EXPIRE_HOURS: int = 48

    @computed_field  # type: ignore[prop-decorator]
    @property
    def emails_enabled(self) -> bool:
        return bool(self.SMTP_HOST and self.EMAILS_FROM_EMAIL)

    EMAIL_TEST_USER: EmailStr = "test@example.com"
    FIRST_SUPERUSER: EmailStr = "admin@tathya.ai"
    FIRST_SUPERUSER_PASSWORD: str = "changethis"

    # ------------------------------------------------------------------
    # Tathya Phase 1 settings
    # ------------------------------------------------------------------
    # Public base URL used for passport QR / verify links
    PUBLIC_BASE_URL: str = "http://localhost:8000"

    # LLM providers (provider-neutral adapter in app.core.llm)
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = "gpt-5-mini"
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-2.5-flash"
    LLM_TIMEOUT_SECONDS: float = 60.0
    LLM_MAX_RETRIES: int = 1
    LLM_CACHE_DIR: str = "./data/cache"

    # Embedding / reranker runtime (Phase 0 cache)
    EMBEDDING_MODEL: str = "BAAI/bge-m3"
    RERANKER_MODEL: str = "BAAI/bge-reranker-v2-m3"
    HHEM_MODEL: str = "vectara/hallucination_evaluation_model"
    USE_HHEM: bool = False
    TORCH_DEVICE: str = "auto"
    MODEL_CACHE_DIR: str = "./data/models"

    # Storage (uploaded documents, keys)
    STORAGE_DIR: str = "./storage"
    ECDSA_PRIVATE_KEY_PATH: str = "./secrets/passport_private.pem"
    ECDSA_PUBLIC_KEY_PATH: str = "./secrets/passport_public.pem"

    def _check_default_secret(self, var_name: str, value: str | None) -> None:
        if value == "changethis":
            message = (
                f'The value of {var_name} is "changethis", '
                "for security, please change it, at least for deployments."
            )
            if self.FASTAPI_ENV == "development":
                warnings.warn(message, stacklevel=1)
            else:
                raise ValueError(message)

    @model_validator(mode="after")
    def _enforce_non_default_secrets(self) -> Self:
        self._check_default_secret("SECRET_KEY", self.SECRET_KEY)
        for host in self.DATABASE_URL.hosts():
            self._check_default_secret("DATABASE_URL password", host["password"])
        self._check_default_secret(
            "FIRST_SUPERUSER_PASSWORD", self.FIRST_SUPERUSER_PASSWORD
        )

        return self


settings = Settings()  # type: ignore

"""Gemini must accept the same nullable JSON Schema used by the judge."""

from types import SimpleNamespace
from google import genai
from app.core import llm
from app.core.judge import JUDGE_SCHEMA
import pytest
from app.core.config import Settings


def test_gemini_passes_raw_json_schema_and_bounded_timeout(monkeypatch):
    observed = {}

    def create(**kwargs):
        observed.update(kwargs)

        def generate(**request):
            config = request["config"]
            assert config.response_json_schema == JUDGE_SCHEMA
            assert config.response_schema is None
            return SimpleNamespace(text='{"status":"uncertain"}')

        return SimpleNamespace(models=SimpleNamespace(generate_content=generate))

    monkeypatch.setattr(genai, "Client", create)
    result = llm._call_gemini(
        llm.LLMRequest(
            prompt="Synthetic schema check",
            schema=JUDGE_SCHEMA,
            prompt_version="schema-test",
        )
    )
    assert result == {"status": "uncertain"}
    assert observed["http_options"].timeout == int(
        llm.settings.LLM_TIMEOUT_SECONDS * 1000
    )


@pytest.mark.parametrize(
    "secret", ["short", "changethis_secret_key_at_least_32_chars_long"]
)
def test_production_rejects_weak_or_template_signing_secret(secret):
    with pytest.raises(ValueError, match="SECRET_KEY"):
        Settings(
            FASTAPI_ENV=None,
            SECRET_KEY=secret,
            FIRST_SUPERUSER_PASSWORD="synthetic-strong-password",
            DATABASE_URL="postgresql://test:strong-password@localhost/test",
        )

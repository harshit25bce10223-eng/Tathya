"""Provider-neutral LLM adapter (Phase 1 foundation).

Locked requirements:
    - one adapter, no provider-specific calls elsewhere
    - primary: gpt-5-mini (OpenAI), fallback: Gemini 2.5 Flash
    - temperature=0, structured output via JSON schema
    - one retry, timeout, deterministic disk cache
    - cache key = SHA256(provider + model + prompt_version + input_hash + temperature)
"""

from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.core.config import settings

LLM_PROMPT_VERSION = "v1"


class LLMError(RuntimeError):
    """All providers failed for a request."""


class LLMUnavailableError(LLMError):
    """No provider is configured (missing API keys)."""


@dataclass
class LLMRequest:
    prompt: str
    schema: dict[str, Any]
    prompt_version: str = LLM_PROMPT_VERSION
    temperature: float = 0.0
    max_output_tokens: int = 4096
    metadata: dict[str, Any] = field(default_factory=dict)


def _input_hash(request: LLMRequest) -> str:
    payload = json.dumps(
        {"prompt": request.prompt, "schema": request.schema},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def cache_key(provider: str, model: str, request: LLMRequest) -> str:
    payload = (
        f"{provider}{model}{request.prompt_version}"
        f"{_input_hash(request)}{request.temperature}"
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class LLMCache:
    """Deterministic JSON file cache. Thread-safe, no eviction (Phase 1)."""

    def __init__(self, directory: str) -> None:
        self.dir = Path(directory).expanduser().resolve()
        self._lock = threading.Lock()

    def get(self, key: str) -> dict[str, Any] | None:
        path = self.dir / f"{key}.json"
        try:
            with self._lock:
                if path.exists():
                    return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return None

    def put(self, key: str, value: dict[str, Any]) -> None:
        path = self.dir / f"{key}.json"
        try:
            with self._lock:
                self.dir.mkdir(parents=True, exist_ok=True)
                tmp = path.with_suffix(".tmp")
                tmp.write_text(
                    json.dumps(value, ensure_ascii=False), encoding="utf-8"
                )
                tmp.replace(path)
        except OSError:
            pass  # cache is best-effort


def _schema_instruction(schema: dict[str, Any]) -> str:
    return (
        "Respond with a single JSON object that validates against this JSON "
        "Schema and nothing else (no prose, no markdown fences):\n"
        + json.dumps(schema, ensure_ascii=False)
    )


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------


def _call_openai(request: LLMRequest) -> dict[str, Any]:
    from openai import OpenAI

    client = OpenAI(api_key=settings.OPENAI_API_KEY, timeout=settings.LLM_TIMEOUT_SECONDS)
    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        temperature=request.temperature,
        max_tokens=request.max_output_tokens,
        messages=[
            {"role": "system", "content": _schema_instruction(request.schema)},
            {"role": "user", "content": request.prompt},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "response",
                "strict": True,
                "schema": request.schema,
            },
        },
    )
    content = response.choices[0].message.content or ""
    return json.loads(content)


def _call_gemini(request: LLMRequest) -> dict[str, Any]:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=request.prompt,
        config=types.GenerateContentConfig(
            temperature=request.temperature,
            max_output_tokens=request.max_output_tokens,
            response_mime_type="application/json",
            response_schema=request.schema,
            system_instruction=_schema_instruction(request.schema),
        ),
    )
    text = response.text
    if not text:
        raise LLMError("gemini returned empty response")
    return json.loads(text)


@dataclass
class Provider:
    name: str
    model: str
    configured: bool
    call: Any


def providers() -> list[Provider]:
    return [
        Provider(
            name="openai",
            model=settings.OPENAI_MODEL,
            configured=bool(settings.OPENAI_API_KEY),
            call=_call_openai,
        ),
        Provider(
            name="gemini",
            model=settings.GEMINI_MODEL,
            configured=bool(settings.GEMINI_API_KEY),
            call=_call_gemini,
        ),
    ]


class LLMAdapter:
    """Single entry point for all LLM usage in the codebase."""

    def __init__(self) -> None:
        self.cache = LLMCache(settings.LLM_CACHE_DIR)

    def is_configured(self) -> bool:
        return any(p.configured for p in providers())

    def complete_json(self, request: LLMRequest) -> dict[str, Any]:
        configured = [p for p in providers() if p.configured]
        if not configured:
            raise LLMUnavailableError("no LLM provider configured")

        for provider in configured:
            key = cache_key(provider.name, provider.model, request)
            cached = self.cache.get(key)
            if cached is not None:
                return cached

        errors: list[str] = []
        for provider in configured:
            key = cache_key(provider.name, provider.model, request)
            attempts = 1 + max(0, settings.LLM_MAX_RETRIES)
            for attempt in range(attempts):
                try:
                    result = provider.call(request)
                    if not isinstance(result, dict):
                        raise LLMError("provider returned non-object JSON")
                    self.cache.put(key, result)
                    return result
                except Exception as exc:  # noqa: BLE001 - fallback boundary
                    errors.append(f"{provider.name} attempt {attempt + 1}: {exc}")
        raise LLMError("; ".join(errors) or "all LLM providers failed")


llm_adapter = LLMAdapter()

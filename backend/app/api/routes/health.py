"""Health and demo-readiness endpoints (root paths, never expose secrets)."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core import models_runtime
from app.core.config import settings
from app.core.jobs import queue_state
from app.core.llm import llm_adapter

router = APIRouter(tags=["health"])

APP_VERSION = "0.1.0"


def _db_status() -> str:
    from app.core.db import engine

    started = time.monotonic()
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        _ = started
        return "up"
    except (SQLAlchemyError, OSError):
        return "down"


def _llm_status() -> str:
    try:
        return "ready" if llm_adapter.is_configured() else "not_configured"
    except Exception:  # noqa: BLE001
        return "unavailable"


@router.get("/health")
def health() -> dict[str, Any]:
    """Component health. Values are status strings only — no config, no secrets."""
    runtime = models_runtime.runtime_status()
    components = {
        "api": "up",
        "db": _db_status(),
        "llm": _llm_status(),
        "embeddings": runtime["embeddings"],
        "reranker": runtime["reranker"],
        "hhem": runtime["hhem"],
        "queue": queue_state.to_dict(),
    }
    critical_ok = components["api"] == "up" and components["db"] == "up"
    return {
        "status": "ok" if critical_ok else "degraded",
        "app": "Tathya",
        "version": APP_VERSION,
        "components": components,
    }


def _exists(relative: str) -> bool:
    return Path(relative).expanduser().exists()


@router.get("/demo/readiness")
def demo_readiness() -> dict[str, Any]:
    """Demo readiness checklist (local paths and booleans only)."""
    hero_pack_loaded = _exists("storage/hero_pack/hero_manifest.json")
    cache_ready = _exists("data/cache/hero_cached_result.json")
    passport_key_ready = (
        _exists(settings.ECDSA_PRIVATE_KEY_PATH)
        and _exists(settings.ECDSA_PUBLIC_KEY_PATH)
    )
    db_ready = _db_status() == "up"
    llm_ready = llm_adapter.is_configured()
    offline_ready = hero_pack_loaded and cache_ready and passport_key_ready

    checks = {
        "hero_pack_loaded": hero_pack_loaded,
        "cache_ready": cache_ready,
        "passport_key_ready": passport_key_ready,
        "db_ready": db_ready,
        "llm_ready": llm_ready,
        "offline_ready": offline_ready,
    }
    return {
        "ready": all(v for k, v in checks.items() if k != "llm_ready"),
        "checks": checks,
    }

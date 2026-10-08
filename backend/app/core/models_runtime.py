"""Model runtime interfaces (Phase 1 foundation).

Locked models:
    embeddings: BAAI/bge-m3
    reranker:   BAAI/bge-reranker-v2-m3
    HHEM:       optional (USE_HHEM)
    TORCH_DEVICE=auto -> resolved device is confirmed, not assumed

Models are lazy-loaded. Health reporting never loads weights; it reports
configuration + cache presence + torch availability only.
Models are never re-downloaded when the Phase 0 cache already has them.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.core.config import settings

logger = logging.getLogger("tathya.models")

_embedder: Any = None
_reranker: Any = None
_hhem: Any = None
_device: str | None = None


def _cache_dir() -> Path:
    return Path(settings.MODEL_CACHE_DIR).expanduser().resolve()


def resolve_device() -> str:
    """Confirm the actual runtime device for TORCH_DEVICE=auto."""
    global _device
    if _device is not None:
        return _device
    pref = (settings.TORCH_DEVICE or "auto").lower()
    try:
        import torch

        if pref == "auto":
            if torch.cuda.is_available():
                _device = "cuda"
            elif getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
                _device = "mps"
            else:
                _device = "cpu"
        else:
            _device = pref
    except ImportError:
        _device = "cpu" if pref in ("auto", "cpu") else pref
    logger.info("torch device resolved to %s", _device)
    return _device


def _model_cached(model_id: str) -> bool:
    """True if the Phase 0 cache contains a directory for this model."""
    cache = _cache_dir()
    if not cache.exists():
        return False
    encoded = model_id.replace("/", "--")
    if (cache / model_id).exists() or (cache / encoded).exists():
        return True
    # HuggingFace-style cache layouts
    for marker in ("model.safetensors", "config.json", "pytorch_model.bin"):
        if list(cache.rglob(f"*{encoded}*{marker}")):
            return True
        if list(cache.rglob(f"*{model_id.split('/')[-1]}*\\{marker}")):
            return True
    return False


def get_embedder() -> Any:
    """Lazy-load BAAI/bge-m3 from the local cache when available."""
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer

        _embedder = SentenceTransformer(
            settings.EMBEDDING_MODEL,
            cache_folder=str(_cache_dir()),
            device=resolve_device(),
        )
    return _embedder


def get_reranker() -> Any:
    """Lazy-load BAAI/bge-reranker-v2-m3 cross-encoder."""
    global _reranker
    if _reranker is None:
        from sentence_transformers import CrossEncoder

        _reranker = CrossEncoder(
            settings.RERANKER_MODEL,
            max_length=512,
            device=resolve_device(),
            cache_folder=str(_cache_dir()),
        )
    return _reranker


def get_hhem() -> Any:
    """Optional HHEM hallucination judge (USE_HHEM flag)."""
    global _hhem
    if not settings.USE_HHEM:
        return None
    if _hhem is None:
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(
            settings.HHEM_MODEL, cache_dir=str(_cache_dir())
        )
        model = AutoModelForSequenceClassification.from_pretrained(
            settings.HHEM_MODEL, cache_dir=str(_cache_dir())
        )
        _hhem = {"tokenizer": tokenizer, "model": model}
    return _hhem


def embed(texts: list[str]) -> list[list[float]]:
    model = get_embedder()
    vectors = model.encode(texts, normalize_embeddings=True)
    return [list(map(float, v)) for v in vectors]


def rerank(query: str, documents: list[str]) -> list[float]:
    if not documents:
        return []
    model = get_reranker()
    pairs = [(query, doc) for doc in documents]
    scores = model.predict(pairs)
    return [float(s) for s in scores]


def hhem_score(premise: str, hypothesis: str) -> float | None:
    bundle = get_hhem()
    if bundle is None:
        return None
    tokenizer = bundle["tokenizer"]
    model = bundle["model"]
    import torch

    inputs = tokenizer(
        premise, hypothesis, return_tensors="pt", truncation=True, max_length=512
    )
    with torch.no_grad():
        logits = model(**inputs).logits
    prob = torch.softmax(logits, dim=-1)[0]
    return float(prob[1])  # label 1 = faithful


# ---------------------------------------------------------------------------
# Status (used by /health and /demo/readiness — never loads weights)
# ---------------------------------------------------------------------------


def runtime_status() -> dict[str, Any]:
    status: dict[str, Any] = {
        "device": None,
        "torch_available": False,
        "embedding_model": settings.EMBEDDING_MODEL,
        "embedding_cached": False,
        "reranker_model": settings.RERANKER_MODEL,
        "reranker_cached": False,
        "hhem_enabled": bool(settings.USE_HHEM),
        "hhem_cached": False,
    }
    try:
        import torch  # noqa: F401

        status["torch_available"] = True
        status["device"] = resolve_device()
    except ImportError:
        status["device"] = "unavailable"
    status["embedding_cached"] = _model_cached(settings.EMBEDDING_MODEL)
    status["reranker_cached"] = _model_cached(settings.RERANKER_MODEL)
    if settings.USE_HHEM:
        status["hhem_cached"] = _model_cached(settings.HHEM_MODEL)

    status["embeddings"] = (
        "ready" if status["embedding_cached"] else "not_cached"
    )
    status["reranker"] = "ready" if status["reranker_cached"] else "not_cached"
    if settings.USE_HHEM:
        status["hhem"] = "ready" if status["hhem_cached"] else "not_cached"
    else:
        status["hhem"] = "disabled"
    return status

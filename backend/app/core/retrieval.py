"""Hybrid evidence retrieval: BM25 + dense vectors + RRF (+ optional rerank).

Designed for small source packs (hundreds of sentences). FAISS is used when
installed; otherwise cosine search over in-memory numpy arrays. Dense models
are optional — BM25 always runs so exact tokens (₹, PO numbers, GSTIN) hit.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from sqlmodel import Session, select

from app.core.canonical import build_blocks, build_sentences
from app.core.config import settings
from app.models import Claim, Document, Evidence

logger = logging.getLogger("tathya.retrieval")

_TOKEN = re.compile(r"[A-Za-z0-9₹%./-]+")
_FALLBACK_EMBEDDING = "BAAI/bge-small-en-v1.5"


@dataclass
class RetrievedChunk:
    document_id: uuid.UUID
    sentence_id: str
    text: str
    start_offset: int
    end_offset: int
    score: float
    support_type: str
    bm25_rank: int | None = None
    dense_rank: int | None = None


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN.findall(text) if t.strip()]


def reciprocal_rank_fusion(
    ranked_lists: list[list[str]],
    k: int = 60,
) -> list[tuple[str, float]]:
    scores: dict[str, float] = {}
    for ranked in ranked_lists:
        for rank, key in enumerate(ranked, start=1):
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda item: item[1], reverse=True)


def _bm25_ranks(query: str, corpus: list[str]) -> list[int]:
    from rank_bm25 import BM25Okapi

    tokenized = [_tokenize(doc) if doc else ["_empty"] for doc in corpus]
    bm25 = BM25Okapi(tokenized)
    scores = bm25.get_scores(_tokenize(query) or ["_empty"])
    order = sorted(range(len(corpus)), key=lambda i: float(scores[i]), reverse=True)
    return order


def _try_faiss_search(query_vec: np.ndarray, matrix: np.ndarray, top_k: int) -> list[int]:
    try:
        import faiss  # type: ignore
    except Exception:
        return []
    if matrix.size == 0:
        return []
    index = faiss.IndexFlatIP(matrix.shape[1])
    vectors = matrix.astype("float32")
    faiss.normalize_L2(vectors)
    q = query_vec.reshape(1, -1).astype("float32").copy()
    faiss.normalize_L2(q)
    index.add(vectors)
    _scores, ids = index.search(q, min(top_k, len(matrix)))
    return [int(i) for i in ids[0] if i >= 0]


def _cosine_ranks(query_vec: np.ndarray, matrix: np.ndarray, top_k: int) -> list[int]:
    if matrix.size == 0:
        return []
    q = query_vec / (np.linalg.norm(query_vec) + 1e-9)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-9
    scores = (matrix / norms) @ q
    return list(np.argsort(-scores)[:top_k])


@lru_cache(maxsize=1)
def _embedder():
    models = [settings.EMBEDDING_MODEL, _FALLBACK_EMBEDDING]
    last_error: Exception | None = None
    for name in models:
        if not name:
            continue
        try:
            from sentence_transformers import SentenceTransformer

            model = SentenceTransformer(name, cache_folder=settings.MODEL_CACHE_DIR)
            logger.info("loaded embedding model %s", name)
            return model
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            logger.warning("embedding model %s unavailable: %s", name, exc)
    if last_error:
        logger.warning("dense retrieval disabled: %s", last_error)
    return None


@lru_cache(maxsize=1)
def _reranker():
    try:
        from sentence_transformers import CrossEncoder

        model = CrossEncoder(settings.RERANKER_MODEL)
        logger.info("loaded reranker %s", settings.RERANKER_MODEL)
        return model
    except Exception as exc:  # noqa: BLE001
        logger.info("reranker unavailable, using RRF ranks only: %s", exc)
        return None


def _encode(texts: list[str]) -> np.ndarray | None:
    model = _embedder()
    if model is None or not texts:
        return None
    vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return np.asarray(vectors, dtype=np.float32)


def _chunks_for_audit(session: Session, audit_id: uuid.UUID) -> list[RetrievedChunk]:
    documents = session.exec(
        select(Document).where(
            Document.audit_id == audit_id,
            Document.is_current.is_(True),
            Document.kind == "source",
        )
    ).all()
    chunks: list[RetrievedChunk] = []
    for document in documents:
        text = document.normalized_text or ""
        sentences = build_sentences(document.id, build_blocks(text), text)
        for sentence in sentences:
            if len(sentence.text.strip()) < 12:
                continue
            chunks.append(
                RetrievedChunk(
                    document_id=document.id,
                    sentence_id=sentence.sentence_id,
                    text=sentence.text.strip(),
                    start_offset=sentence.start_offset,
                    end_offset=sentence.end_offset,
                    score=0.0,
                    support_type="unclassified",
                )
            )
    return chunks


def retrieve_for_claim(
    session: Session,
    claim: Claim,
    *,
    top_k: int = 5,
    candidate_pool: int = 20,
) -> list[RetrievedChunk]:
    chunks = _chunks_for_audit(session, claim.audit_id)
    usable = [
        chunk
        for chunk in chunks
        if not (
            chunk.document_id == claim.document_id
            and chunk.sentence_id == claim.sentence_id
        )
    ]
    if not usable:
        return []

    # Exact business-field comparisons settle numeric/date checks before any
    # semantic model initialization. Preserve all conflicting current quotes.
    from app.core.source_verification import compare_quote
    exact = [chunk for chunk in usable if compare_quote(claim.text, chunk.text) is not None]
    if exact:
        return exact

    corpus = [chunk.text for chunk in usable]
    keys = [f"{chunk.document_id}:{chunk.sentence_id}" for chunk in usable]
    key_to_index = {key: i for i, key in enumerate(keys)}

    bm25_order = _bm25_ranks(claim.text, corpus)
    ranked_lists = [[keys[i] for i in bm25_order]]

    embeddings = _encode(corpus + [claim.text])
    dense_order: list[int] = []
    if embeddings is not None:
        matrix, query_vec = embeddings[:-1], embeddings[-1]
        dense_order = _try_faiss_search(query_vec, matrix, candidate_pool)
        if not dense_order:
            dense_order = _cosine_ranks(query_vec, matrix, candidate_pool)
        ranked_lists.append([keys[i] for i in dense_order])

    fused = reciprocal_rank_fusion(ranked_lists)
    pool_keys = [key for key, _score in fused[:candidate_pool]]

    reranker = _reranker()
    if reranker is not None and pool_keys:
        pairs = [(claim.text, usable[key_to_index[key]].text) for key in pool_keys]
        try:
            scores = reranker.predict(pairs)
            order = sorted(
                range(len(pool_keys)),
                key=lambda i: float(scores[i]),
                reverse=True,
            )
            pool_keys = [pool_keys[i] for i in order]
        except Exception as exc:  # noqa: BLE001
            logger.warning("rerank failed: %s", exc)

    results: list[RetrievedChunk] = []
    for rank, key in enumerate(pool_keys[:top_k], start=1):
        chunk = usable[key_to_index[key]]
        fused_score = next((score for item, score in fused if item == key), 0.0)
        chunk.score = round(float(fused_score), 6)
        chunk.bm25_rank = next(
            (i + 1 for i, idx in enumerate(bm25_order) if keys[idx] == key),
            None,
        )
        chunk.dense_rank = next(
            (i + 1 for i, idx in enumerate(dense_order) if keys[idx] == key),
            None,
        )
        if _looks_like_conflict(claim.text, chunk.text):
            chunk.support_type = "refutes"
        results.append(chunk)
        logger.debug("retrieved rank %s score %s", rank, chunk.score)
    return results


def _looks_like_conflict(claim_text: str, evidence_text: str) -> bool:
    claim_nums = re.findall(r"\d[\d,]*(?:\.\d+)?", claim_text)
    evid_nums = re.findall(r"\d[\d,]*(?:\.\d+)?", evidence_text)
    if not claim_nums or not evid_nums:
        return False
    claim_set = {n.replace(",", "") for n in claim_nums}
    evid_set = {n.replace(",", "") for n in evid_nums}
    return bool(claim_set and evid_set and claim_set.isdisjoint(evid_set))


def persist_evidence_for_claim(
    session: Session,
    claim: Claim,
    chunks: list[RetrievedChunk],
) -> list[Evidence]:
    existing = session.exec(select(Evidence).join(Document, Evidence.source_document_id == Document.id).where(Evidence.claim_id == claim.id, Document.is_current.is_(True), Document.kind == "source")).all()
    if existing:
        return list(existing)
    rows: list[Evidence] = []
    for chunk in chunks:
        row = Evidence(
            claim_id=claim.id,
            source_document_id=chunk.document_id,
            quote=chunk.text,
            location_json=json.dumps(
                {
                    "kind": "text",
                    "start": chunk.start_offset,
                    "end": chunk.end_offset,
                    "sentence_id": chunk.sentence_id,
                    "bm25_rank": chunk.bm25_rank,
                    "dense_rank": chunk.dense_rank,
                },
                ensure_ascii=False,
            ),
            support_type=chunk.support_type,
            score=chunk.score,
        )
        session.add(row)
        rows.append(row)
    if rows:
        session.commit()
        for row in rows:
            session.refresh(row)
    return rows


def retrieve_evidence_for_audit(session: Session, audit_id: uuid.UUID) -> int:
    claims = session.exec(select(Claim).where(Claim.audit_id == audit_id)).all()
    written = 0
    for claim in claims:
        chunks = retrieve_for_claim(session, claim)
        rows = persist_evidence_for_claim(session, claim, chunks)
        written += len(rows)
    return written


def rrf_debug_score(rank: int, k: int = 60) -> float:
    return 1.0 / (k + rank)


__all__ = [
    "RetrievedChunk",
    "reciprocal_rank_fusion",
    "retrieve_for_claim",
    "retrieve_evidence_for_audit",
    "persist_evidence_for_claim",
    "rrf_debug_score",
]

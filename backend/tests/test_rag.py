"""RAG regression tests use isolated SQLite and stubbed model/provider calls."""

import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine

from app.api.deps import get_current_user, get_db
from app.api.routes.rag import router
from app.core import rag, retrieval
from app.core.llm import LLMUnavailableError
from app.models import Audit, Document, User


@pytest.fixture(scope="session", autouse=True)
def db():
    # Override repository's shared DB fixture; these tests never touch PostgreSQL.
    yield None


@pytest.fixture
def pack(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    for table in (User.__table__, Audit.__table__, Document.__table__):
        table.create(engine)
    monkeypatch.setattr(retrieval, "_encode", lambda _: None)
    monkeypatch.setattr(retrieval, "_reranker", lambda: None)
    with Session(engine) as session:
        owner = User(
            email="rag-owner@example.com", hashed_password="not-a-real-password"
        )
        stranger = User(
            email="rag-other@example.com", hashed_password="not-a-real-password"
        )
        session.add_all([owner, stranger])
        session.commit()
        audit = Audit(title="Source questions", owner_id=owner.id)
        other = Audit(title="Other tenant", owner_id=stranger.id)
        session.add_all([audit, other])
        session.commit()

        def source(text, *, current=True, kind="source", audit_id=None, version=1):
            d = Document(
                audit_id=audit_id or audit.id,
                kind=kind,
                filename=f"source-{uuid.uuid4().hex}.txt",
                storage_path="unused",
                normalized_text=text,
                text_hash=uuid.uuid4().hex,
                is_current=current,
                version_no=version,
            )
            session.add(d)
            session.commit()
            return d

        yield session, owner, stranger, audit, other, source
    engine.dispose()


def test_only_current_same_audit_sources_are_retrieved(pack):
    session, _, _, audit, other, source = pack
    current = source("The warranty period is twelve months.")
    source("The warranty period is ninety months.", current=False, version=2)
    source("The warranty period is eighty months.", kind="primary", version=3)
    source("The warranty period is seventy months.", audit_id=other.id)
    citations, mode = rag.retrieve_sources(
        session, audit.id, "What is the warranty period?", 5
    )
    assert mode == "lexical" and len(citations) == 1
    c = citations[0]
    assert c.document_id == current.id
    assert c.quote == current.normalized_text[c.start_offset : c.end_offset]
    assert c.text_hash == current.text_hash


def test_unrelated_question_abstains_without_calling_generator(pack, monkeypatch):
    session, _, _, audit, _, source = pack
    source("The warranty period is twelve months.")
    monkeypatch.setattr(
        rag.llm_adapter,
        "complete_json",
        lambda _: pytest.fail("irrelevant evidence sent to LLM"),
    )
    result = rag.answer_question(
        session, audit.id, rag.RagQuestion(question="What are zebras eating?")
    )
    assert result.status == "insufficient_evidence" and result.citations == []


def test_generated_answer_has_versioned_citations(pack, monkeypatch):
    session, _, _, audit, _, source = pack
    source("The warranty period is twelve months.")
    captured = []

    def complete(request):
        captured.append(request)
        return {
            "insufficient_evidence": False,
            "statements": [
                {"text": "The warranty is twelve months.", "citation_ids": ["S1"]}
            ],
        }

    monkeypatch.setattr(rag.llm_adapter, "complete_json", complete)
    result = rag.answer_question(
        session, audit.id, rag.RagQuestion(question="What is the warranty?")
    )
    assert result.status == "answered" and result.answer.endswith("[S1]")
    assert len(result.citations) == 1 and "untrusted data" in captured[0].prompt
    assert captured[0].prompt_version == "tathya-rag-v1"


@pytest.mark.parametrize(
    "payload",
    [
        {
            "insufficient_evidence": False,
            "statements": [{"text": "Warranty is 99 months", "citation_ids": ["S99"]}],
        },
        {
            "insufficient_evidence": False,
            "statements": [{"text": "Warranty is 99 months", "citation_ids": []}],
        },
    ],
)
def test_invalid_or_missing_citations_are_rejected(pack, monkeypatch, payload):
    session, _, _, audit, _, source = pack
    source("The warranty period is twelve months.")
    monkeypatch.setattr(rag.llm_adapter, "complete_json", lambda _: payload)
    result = rag.answer_question(
        session, audit.id, rag.RagQuestion(question="What is the warranty?")
    )
    assert (
        result.status == "generation_unavailable" and "99 months" not in result.answer
    )


def test_missing_provider_returns_excerpts_not_fake_generation(pack, monkeypatch):
    session, _, _, audit, _, source = pack
    source("The warranty period is twelve months.")

    def unavailable(_):
        raise LLMUnavailableError("not configured")

    monkeypatch.setattr(rag.llm_adapter, "complete_json", unavailable)
    result = rag.answer_question(
        session, audit.id, rag.RagQuestion(question="What is the warranty?")
    )
    assert result.status == "generation_unavailable" and result.citations


def test_changed_source_invalidates_answer(pack, monkeypatch):
    session, _, _, audit, _, source = pack
    d = source("The warranty period is twelve months.")

    def changed(_):
        d.is_current = False
        session.add(d)
        session.commit()
        return {
            "insufficient_evidence": False,
            "statements": [{"text": "Twelve months.", "citation_ids": ["S1"]}],
        }

    monkeypatch.setattr(rag.llm_adapter, "complete_json", changed)
    result = rag.answer_question(
        session, audit.id, rag.RagQuestion(question="What is the warranty?")
    )
    assert result.status == "generation_unavailable" and not result.citations


def test_api_owner_access_and_cross_audit_denial(pack, monkeypatch):
    session, owner, stranger, audit, _, source = pack
    source("The warranty period is twelve months.")
    calls = []
    monkeypatch.setattr(
        rag.llm_adapter,
        "complete_json",
        lambda _: calls.append(1) or {"insufficient_evidence": True, "statements": []},
    )
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    def get_session():
        yield session

    app.dependency_overrides[get_db] = get_session
    app.dependency_overrides[get_current_user] = lambda: stranger
    with TestClient(app) as client:
        url = f"/api/v1/audits/{audit.id}/ask"
        assert (
            client.post(url, json={"question": "What is the warranty?"}).status_code
            == 404
        )
        assert calls == []
        app.dependency_overrides[get_current_user] = lambda: owner
        assert (
            client.post(url, json={"question": "What is the warranty?"}).status_code
            == 200
        )
        assert client.post(url, json={"question": "   "}).status_code == 422
        assert (
            client.post(url, json={"question": "Warranty?", "top_k": 99}).status_code
            == 422
        )
        del app.dependency_overrides[get_current_user]
        assert client.post(url, json={"question": "Warranty?"}).status_code == 401


@pytest.mark.parametrize("vectors", [[], [[float("nan")]], [[0.0]], [[1.0]]])
def test_invalid_embeddings_preserve_lexical_retrieval(pack, monkeypatch, vectors):
    session, _, _, audit, _, source = pack
    document = source("The warranty period is twelve months.")
    monkeypatch.setattr(retrieval, "_encode", lambda _: vectors)
    citations, mode = rag.retrieve_sources(session, audit.id, "Warranty period?", 5)
    assert mode == "lexical"
    assert citations[0].document_id == document.id


def test_hindi_retrieval_uses_complete_words(pack):
    session, _, _, audit, _, source = pack
    relevant = source("वारंटी अवधि बारह महीने है।")
    source("कार्यालय दिल्ली में है।", version=2)
    assert "वारंटी" in retrieval._tokenize("वारंटी अवधि?")
    citations, mode = rag.retrieve_sources(session, audit.id, "वारंटी अवधि?", 5)
    assert mode == "lexical"
    assert [c.document_id for c in citations] == [relevant.id]


def test_invalid_location_is_not_returned(pack, monkeypatch):
    session, _, _, audit, _, source = pack
    document = source("Warranty period is twelve months.")
    chunk = retrieval.RetrievedChunk(
        document_id=document.id,
        sentence_id="invalid",
        text=document.normalized_text,
        start_offset=-1,
        end_offset=1000,
        score=1.0,
        support_type="unknown",
    )
    monkeypatch.setattr(retrieval, "_chunks_for_audit", lambda *_: [chunk])
    citations, _ = rag.retrieve_sources(session, audit.id, "Warranty?", 5)
    assert citations == []


@pytest.mark.parametrize("change", ["kind", "version_no", "audit_id"])
def test_source_identity_change_invalidates_answer(pack, monkeypatch, change):
    session, _, _, audit, other, source = pack
    document = source("Warranty period is twelve months.")

    def complete(_):
        value = {"kind": "primary", "version_no": 2, "audit_id": other.id}[change]
        setattr(document, change, value)
        session.add(document)
        session.commit()
        return {
            "insufficient_evidence": False,
            "statements": [{"text": "Twelve months.", "citation_ids": ["S1"]}],
        }

    monkeypatch.setattr(rag.llm_adapter, "complete_json", complete)
    result = rag.answer_question(
        session, audit.id, rag.RagQuestion(question="Warranty period?")
    )
    assert result.status == "generation_unavailable"
    assert result.citations == []

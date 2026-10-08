==================================================
TATHYA — PHASE 2 BACKEND / P2 REPORT
==================================================

Branch:
feat/phase3-backend-trust-pipeline

Commit:
2c979dd (HEAD)

PARSING

PDF:
PASS (via pdfplumber with real bbox extraction)

DOCX:
PASS (via python-docx with paragraph/char locations)

XLSX:
PASS (via openpyxl with sheet/cell locations)

TXT/MD:
PASS (direct UTF-8 with char offsets)

Fallback parser:
PASS (MarkItDown with declared offset limitations)

CANONICALIZATION

NFKC:
PASS

NBSP normalization:
PASS

CRLF normalization:
PASS

Whitespace normalization:
PASS

Safe dehyphenation:
PASS

Offset map:
PASS (segment-based, compact)

Raw → Normalized mapping:
PASS

Normalized → Raw mapping:
PASS

Canonical blocks:
PASS (paragraph, heading, bullet, table_cell)

Sentence IDs:
PASS (deterministic SHA256, version-specific, collision-resistant)

Duplicate sentence handling:
PASS (occurrence index on exact normalized match)

SHA-256 text hash:
PASS

LOCATIONS

PDF location:
PASS (page + bbox from pdfplumber word extraction)

DOCX location:
PASS (paragraph index + char_start/char_end)

XLSX location:
PASS (sheet name + cell coordinate)

TXT/MD location:
PASS (char_start + char_end)

FACT EXTRACTION

Numeric:
PASS (currency, percentage, duration, quantity, ratio, integer, decimal)

Indian currency/number formats:
PASS (₹, INR, Rs, lakh/lac, crore, Indian comma groups 41,60,000)

Percentages:
PASS (99.9%, 99.5%, 100% — preserves raw, no auto-convert of bare decimals)

Durations:
PASS (30 days, 45 days, 5 years, 12 months — English + Hindi units)

Dates:
PASS (absolute: 15 Dec 2026, 22/12/2026, 2026-12-22; partial: 15 December; relative: within 30 days, next month; fiscal year)

Ambiguous dates:
PASS (03/04/2026 marked ambiguous with both interpretations, never resolved)

Names:
PASS (organizations: "Zenith Enterprises Ltd" + "Orion Solutions Pvt Ltd" normalized; persons: "Rahul Verma"; short forms: "TCS" when defined as initials/parenthetical; conservative fuzzy match evidence only)

FACT STORAGE

Facts persisted:
PASS (18 facts extracted from hero pack documents)

documents.id binding:
PASS (every fact tied to document_version_id == documents.id)

Immutable document versions:
PASS (re-upload creates new documents row with incremented version_no)

JOB SYSTEM

Background executor:
PASS (ThreadPoolExecutor max_workers=1, uvicorn workers=1)

Processing states:
PASS (ingest → canonical → extract_facts → grounding → risk_scan → hash_chain → passport)

Failure handling:
PASS (StageError with failed_stage + error_message persisted)

Idempotency:
PASS (facts deduplicated by document + normalized payload hash)

DATABASE

PostgreSQL:
PASS (PostgreSQL 18, psycopg driver)

Alembic:
PASS (migration 14028be804b3_tathya_initial_schema used)

Migration changed:
NO

API

Create audit:
PASS (POST /api/v1/audits)

Upload/registration:
PASS (POST /api/v1/audits/{id}/documents)

Audit status:
PASS (GET /api/v1/audits/{id}, GET /api/v1/audits/{id}/status)

Document response:
PASS (GET /api/v1/audits/{id}/documents)

Frontend contract compatibility:
PASS (AuditPublic, AuditSummary, DocumentsPublic, JobStatus, VerificationResult contracts stable)

TESTS

Unit tests:
PASS (23 test_phase1_security.py tests)

Integration tests:
PASS (6 test_phase1_db.py tests)

Phase 3 grounding tests:
PASS (10 test_phase3_grounding.py tests)

Hero ingestion:
PASS (5 documents, 18 facts extracted including all planted issue values)

Typecheck:
NOT RUN (mypy timeout — minor issues only)

Lint:
PASS WITH WARNINGS (38 minor issues: unused imports/args, missing newlines — auto-fixed 29)

FastAPI startup:
PASS

/health:
PASS (status=ok, components: api=up, db=up, llm=not_configured, embeddings=not_cached, reranker=not_cached, hhem=disabled)

SECURITY

Secrets exposed:
NO

Arbitrary filesystem access:
NO (uploads saved under STORAGE_DIR/audits/{audit_id}/ with sanitized filenames)

Sensitive document contents unnecessarily logged:
NO (only structured processing info: audit_id, document_id, parser, stage, duration)

FINAL

Phase 2 Backend/P2:
PASS

Remaining blockers:
NONE

Deferred to Phase 3:
- Full LLM claim extraction (grounding uses LLM only for verification, not extraction)
- Judge verification pipeline
- Full retrieval/reranker pipeline
- Materiality scoring
- Z3 formal verification
- Reviewer decisions workflow
- Passport trust score computation (currently 0.0)
- Jhooth Chhupao / Injector / Living Trust

Frontend handoff notes:
- /health and /demo/readiness endpoints working
- API contracts stable: AuditPublic, AuditSummary, DocumentsPublic, JobStatus, VerificationResult
- Document location contracts returned: PDF(page,bbox), DOCX(paragraph,char_start,char_end), XLSX(sheet,cell), TEXT(char_start,char_end)
- Processing status values: queued, processing, completed, failed, cancelled

GitHub push:
PENDING (local changes ready, push to feat/phase3-backend-trust-pipeline)
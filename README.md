<p align="center">
  <img src="frontend/public/assets/images/tathya-logo-v2.png" alt="Tathya" width="220" />
</p>

<h1 align="center">Tathya</h1>

<p align="center"><strong>Every fact, checked.</strong></p>

<p align="center">
  A reviewer-first workspace for tracing document claims to evidence, surfacing conflicts, and publishing verifiable trust records.
</p>

## What Tathya does

Tathya helps teams review high-stakes documents without treating an AI response as the final answer. It preserves the path from a claim to its source evidence so a human reviewer can inspect the underlying text and make the decision.

```text
Upload documents → extract claims → compare against sources → review findings → verify a trust passport
```

### Built for evidence-led review

- **Document audits** — upload primary and source documents, then follow an audit through review.
- **Claim and evidence traceability** — findings retain document locations, quotes, source versions and hashes.
- **Investigation workspace** — inspect the document, findings and evidence together instead of reading a generic AI report.
- **Source questions** — ask questions over the current source pack with constrained, cited answers and honest abstention.
- **Trust passports** — publish a signed record that can be checked through the public verifier.
- **Reviewer controls** — separate reviewer decisions from automated findings and preserve uncertainty when evidence is inconclusive.

## The audit workflow

### 1. Bring the document and its sources together

Start an audit by adding the document under review and the source material that should support, contradict or clarify it. Tathya treats source documents as versioned evidence, so review always has a concrete basis.

### 2. Turn text into reviewable claims

The pipeline extracts and normalizes document text, identifies claims and keeps location data with every finding. A reviewer can move from a finding back to the relevant page, paragraph, cell or text range instead of relying on a summary alone.

### 3. Compare claims with evidence

Tathya presents supported, contradicted, unsupported and uncertain states separately. Missing evidence is not shown as a false claim, and inconclusive evidence is not turned into artificial certainty.

### 4. Investigate before deciding

The control workspace links the document, finding list and evidence panel. Selecting a finding focuses its document location, opens the related evidence and makes the next reviewer check clear.

### 5. Publish a verifiable record

Once a review is complete, a trust passport can be verified through a public token. Verification is separate from the private review workspace and does not expose source documents.

## Review principles

| Principle | What it means in Tathya |
| --- | --- |
| Evidence before assertion | Every answer and finding should lead back to a source excerpt or an explicit absence of evidence. |
| Honest uncertainty | `UNSUPPORTED`, `UNCERTAIN` and `CONTRADICTED` stay distinct throughout the review flow. |
| Human accountability | Automated output assists the reviewer; reviewer decisions remain a first-class record. |
| Version awareness | Source versions, text hashes and locations keep evidence references tied to the content that was reviewed. |
| Safe generation | Source questions use constrained context, citation checks and abstention when the available material is insufficient. |

## Product surfaces

| Surface | Purpose |
| --- | --- |
| `/login` | Secure user access |
| `/submit` | Start an audit with primary and source files |
| `/control/queue` | Review work that needs attention |
| `/control/workspace/:auditId` | Investigate findings, locations and evidence |
| `/verify/:token` | Verify a published trust passport |
| `/health` | Check API and runtime component status |

## Quick start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- [Bun](https://bun.sh/)
- Docker Desktop for PostgreSQL and Mailcatcher

### Run locally

```bash
# 1. Configure local values
# macOS / Linux
cp .env.example .env

# Windows PowerShell
Copy-Item .env.example .env

# 2. Start supporting services
docker compose up -d db mailcatcher

# 3. Start the API (terminal 1)
cd backend
uv sync
uv run bash scripts/prestart.sh
uv run fastapi dev

# 4. Start the web app (terminal 2, from repository root)
bun install
bun run dev
```

Open the web app at `http://localhost:5173`, API documentation at `http://localhost:8000/docs`, and health at `http://localhost:8000/health`.

For development SQLite can be configured in `.env`; use PostgreSQL for shared or production environments.

### Supported document inputs

Tathya accepts PDF, DOCX, XLSX/XLSM, TXT, Markdown and CSV inputs. Each format enters a common canonical-text representation while preserving the strongest available location reference:

| Format | Parser path | Review location |
| --- | --- | --- |
| PDF | `pdfplumber` | Page and bounding box where available |
| DOCX | `python-docx` | Paragraph and character range |
| XLSX / XLSM | `openpyxl` | Sheet and cell |
| TXT / Markdown / CSV | Direct UTF-8 reader | Character range |
| Other readable formats | MarkItDown fallback | Explicit fallback provenance |

Normalisation makes text safe to compare without silently changing its meaning: Unicode is standardised, line endings and whitespace are made consistent, and meaningful hyphens are preserved. The pipeline keeps offset mappings so reviewers can return from a normalized claim to the original document location.

## Architecture

```text
React + Vite web app
        │
        ▼
FastAPI API ── PostgreSQL
        │
        ├── document parsing and canonical text
        ├── claim, evidence and finding pipeline
        ├── hybrid source retrieval (BM25 + optional dense reranking)
        └── signed trust-passport verification
```

The repository also includes an Expo companion app in `mobile/` and transactional email components in `packages/react-email/`.

## Repository guide

| Directory | Contains |
| --- | --- |
| `backend/` | API, audit pipeline, authentication, evidence models, database migrations and verification services |
| `frontend/` | Tathya web application, typed API client, reviewer workspace and browser tests |
| `mobile/` | Expo companion application for mobile access and capture workflows |
| `docs/` | Product contracts and implementation notes, including the source-question design |
| `evaluation/` | Trust-core evaluation fixtures and methodology notes |
| `deploy/` | Production Docker Compose reference and deployment checklist |
| `packages/react-email/` | Transactional email components |

## Source questions and RAG

`POST /api/v1/audits/{audit_id}/ask` answers only from the audit's current source documents. Answers are cited with exact excerpts, locations, source versions and hashes. If relevant evidence or a configured generation provider is unavailable, the API abstains or returns retrieved excerpts instead of inventing an answer.

### How retrieval works

Tathya uses hybrid retrieval for small, audit-scoped source packs. It combines lexical and semantic retrieval, then only sends selected excerpts to the configured provider.

```text
Question
   │
   ├── BM25 lexical search ───────────► exact terms, IDs, currencies and dates
   ├── Dense embedding search ─────────► semantic similarity when the model is available
   ├── Reciprocal-rank fusion ─────────► combines both result lists
   ├── Optional cross-encoder rerank ──► refines the candidate order
   └── Citation validation ────────────► exact source excerpt, version and offsets
```

Dense embeddings and reranking are optional. If a model is unavailable, returns invalid vectors, or is not configured, lexical retrieval remains available. Queries without relevant candidates return an evidence-insufficient response rather than a made-up answer.

### RAG response states

| State | Meaning |
| --- | --- |
| `answered` | The generated response passed structured-output and citation validation. |
| `insufficient_evidence` | Current source documents do not contain enough relevant evidence. |
| `generation_unavailable` | Excerpts were retrieved but a provider was unavailable or output could not be validated. |

### RAG safeguards

- Retrieval is restricted to current `source` documents in the requested audit; it never uses another audit's sources or the audited primary document as source evidence.
- Prompts treat uploaded text and questions as untrusted data. The generator has no tools or write capability.
- Every factual statement must reference one or more server-issued citation IDs.
- Citation quotes are sliced from the stored source text, not generated by the model.
- Before returning an answer, Tathya checks source audit membership, source kind, current status, version, text hash and quoted character range again.
- Sources changed while generation is in progress invalidate the response so the reviewer can ask again against the latest material.

See [RAG design and validation notes](docs/rag.md) for the retrieval contract and safeguards.

## Evidence, scoring and verification

### Findings and review decisions

The audit model keeps facts, claims, evidence, flags and reviewer decisions as separate records. This keeps automated analysis and human judgement distinguishable. A finding can lead a reviewer to a source excerpt, while a reviewer decision provides the accountable outcome for the audit.

When evidence is returned by the backend, the interface distinguishes these states instead of flattening them into a single “wrong” label:

| Evidence state | Review meaning |
| --- | --- |
| `SUPPORTED` | Source material supports the claim. |
| `CONTRADICTED` | Source material conflicts with the claim. |
| `UNSUPPORTED` | No supporting source evidence was found in the current source set. |
| `UNCERTAIN` | Available evidence is inconclusive and needs reviewer verification. |

### Trust passports

Tathya issues a public verification record after the audit pipeline has the required document and source context. A passport includes a verification token, document hash, source-set hash, audit-chain reference and a signature. The verifier checks the associated audit record and signature state before returning the public result.

The signing path uses ECDSA P-256 and a SHA-256-backed audit chain. Keys stay in runtime storage and must be backed up with the document and database volumes. A public passport verifies the record; it is not a substitute for exposing private source documents.

### Evaluation and adversarial review

The evaluation workspace records deterministic checks, provider-judge behaviour, abstentions, latency and errors on synthetic fixtures. It does not present component results as a production-accuracy claim. The challenge workflow evaluates a candidate audit against canonical source copies while preserving the parent audit's original evidence and reviewer decisions.

See [evaluation notes](evaluation/README.md) for scope, methodology and current limitations.

## Quality checks

```bash
# Frontend lint and browser tests
bun run lint
bun run test

# Backend tests
cd backend
uv run bash scripts/tests-start.sh

# Focused RAG regression tests (from repository root)
.venv/Scripts/python.exe -m pytest --noconftest backend/tests/test_rag.py -q
```

The focused RAG suite runs against isolated in-memory SQLite tables and stubbed provider/model calls. It covers audit isolation, source-version filtering, exact quote offsets, invalid citations, abstention, unavailable generation, source changes and input limits.

## Deployment

The production Compose reference is documented in [deploy/README.md](deploy/README.md). It uses persistent volumes for document storage and signing keys, plus HTTPS termination. Review deployment settings, migrations and backups before admitting real documents.

## Project references

- [Contribution guide](CONTRIBUTING.md)
- [RAG design notes](docs/rag.md)
- [Trust-core evaluation notes](evaluation/README.md)
- [Production deployment reference](deploy/README.md)

## Submission notes

Tathya is an active product build. Local model availability, provider configuration and document processing outcomes depend on the runtime environment and supplied evidence. Review findings and source excerpts before making decisions.

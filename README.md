<p align="center">
  <img src="frontend/public/assets/images/tathya-logo-v2.png" alt="Tathya" width="220" />
</p>

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
cp .env.example .env

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

## Source questions and RAG

`POST /api/v1/audits/{audit_id}/ask` answers only from the audit's current source documents. Answers are cited with exact excerpts, locations, source versions and hashes. If relevant evidence or a configured generation provider is unavailable, the API abstains or returns retrieved excerpts instead of inventing an answer.

See [RAG design and validation notes](docs/rag.md) for the retrieval contract and safeguards.

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

## Deployment

The production Compose reference is documented in [deploy/README.md](deploy/README.md). It uses persistent volumes for document storage and signing keys, plus HTTPS termination. Review deployment settings, migrations and backups before admitting real documents.

## Project references

- [Contribution guide](CONTRIBUTING.md)
- [RAG design notes](docs/rag.md)
- [Trust-core evaluation notes](evaluation/README.md)
- [Production deployment reference](deploy/README.md)

## Submission notes

Tathya is an active product build. Local model availability, provider configuration and document processing outcomes depend on the runtime environment and supplied evidence. Review findings and source excerpts before making decisions.

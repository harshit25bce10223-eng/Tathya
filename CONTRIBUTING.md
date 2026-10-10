# Contributing to Tathya

Thanks for helping improve Tathya. The product handles evidence-led review, so changes should be easy to trace, test and review.

## Before you start

Keep each pull request focused on one outcome. For changes that alter shared API contracts, document processing, evidence semantics, authentication or signing behavior, open an issue first so the implementation approach can be agreed before code is written.

Never commit secrets, user documents, signing keys, generated frontend bundles, model caches or local test output.

## Development

Use the local setup in [README.md](README.md). Run checks relevant to the files you changed:

```bash
# web application
bun run lint
bun run test

# backend application
cd backend
uv run bash scripts/tests-start.sh
```

For changes to source retrieval, run the focused regression suite from the repository root:

```bash
.venv/Scripts/python.exe -m pytest --noconftest backend/tests/test_rag.py -q
```

## Pull requests

Explain the user-facing problem, the resulting behavior and the validation performed. Update tests when behavior changes. If something is intentionally deferred, state it clearly in the pull request description.

Preserve citation integrity: frontend code presents backend evidence and status; it must not calculate truth, source authority or trust scores on its own.

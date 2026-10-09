# Tathya (तथ्य)

Every fact, checked. Tathya is a document fact verification product built around claims, source evidence, reviewer decisions and trust passports.

## Repository

- `backend/`: FastAPI service, authentication, PostgreSQL models and migration history.
- `frontend/`: React application and generated OpenAPI client, built with Vite and served by the backend.
- `src/`: Tathya product interface work, including submission, control center and trust analytics. This separate tree currently has missing imported files and is not the active frontend entry.
- `mobile/`: Expo integration app for service health, camera permissions and secure storage.
- `scripts/`: document, OCR, retrieval, model, passport and evaluation checks.
- `packages/react-email/`: transactional email source and shared email components.

The intended product routes are `/login`, `/submit`, `/control`, `/control/queue`, `/control/workspace/:auditId` and `/verify/:token`. The current active frontend still contains inherited administration and Items routes; product integration is incomplete. Do not interpret the intended routes as a claim that all workflows are deployed.

## Development

Use the [development guide](development.md) for setup, backend/frontend commands, testing and contribution instructions. See the [deployment guide](deployment.md) for deployment options.

The Vite build targets `backend/app/frontend/`. Keep generated deployment output separate from authored product source. Configure local environment values from `.env.example`; never commit passwords, credentials, private keys or runtime uploads.

## Open-source foundation

Tathya reuses the [Full Stack FastAPI Template](https://github.com/fastapi/full-stack-fastapi-template), FastAPI, SQLModel, Alembic, React, Vite, Tailwind, shadcn/ui, TanStack and Expo. Tathya product work also uses Recharts and React Flow. Document/OCR/ML integrations include MarkItDown, pdfplumber, python-docx, openpyxl, Presidio, sentence-transformers, Transformers, PyTorch and Tesseract tooling. These libraries are useful infrastructure; their presence does not imply an inherited demo.

Dependencies retain their own licenses in their installed distributions.

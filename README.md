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

Use [development.md](development.md), [backend instructions](backend/README.md), [frontend instructions](frontend/README.md) and [deployment instructions](deployment-docker-compose.md) for the existing service setup. Review the [residue audit](docs/template-residue-audit.md) before deployment: the frontend manifest and lockfile differ and the local Python environment requires repair.

The Vite build targets `backend/app/frontend/`. Keep generated deployment output separate from authored product source. Configure local environment values from `.env.example`; never commit passwords, credentials, private keys or runtime uploads.

## Open-source foundation

Tathya reuses the [Full Stack FastAPI Template](https://github.com/fastapi/full-stack-fastapi-template), FastAPI, SQLModel, Alembic, React, Vite, Tailwind, shadcn/ui, TanStack and Expo. Tathya product work also uses Recharts and React Flow. Document/OCR/ML integrations include MarkItDown, pdfplumber, python-docx, openpyxl, Presidio, sentence-transformers, Transformers, PyTorch and Tesseract tooling. These libraries are useful infrastructure; their presence does not imply an inherited demo.

Upstream copyright and license notices remain in [LICENSE](LICENSE), [mobile/LICENSE](mobile/LICENSE) and installed dependency distributions. This repository's MIT notice retains Sebastián Ramírez's upstream copyright. See [LICENSES.md](LICENSES.md) for the attribution record; it is not a substitute for reviewing dependency licenses when distributing the application or models.

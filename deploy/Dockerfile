FROM oven/bun:1 AS frontend
WORKDIR /app
COPY package.json bun.lock ./
COPY frontend/package.json frontend/package.json
COPY packages/react-email/package.json packages/react-email/package.json
RUN bun install --frozen-lockfile
COPY frontend frontend
WORKDIR /app/frontend
RUN bun run build

FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /bin/uv
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr poppler-utils libgomp1 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY backend/pyproject.toml backend/pyproject.toml
COPY backend/app backend/app
RUN uv sync --frozen --no-dev --package app
COPY --from=frontend /app/backend/app/frontend backend/app/frontend
RUN useradd -u 10001 -m tathya && mkdir -p backend/storage backend/secrets backend/data && chown -R tathya:tathya /app
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
WORKDIR /app/backend
USER tathya
EXPOSE 8000
# The in-process job executor and startup recovery require one API worker.
CMD ["sh", "-c", "python -m app.production_bootstrap && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1"]

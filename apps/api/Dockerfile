FROM node:24-bookworm-slim AS web-builder
WORKDIR /web
COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci
COPY apps/web ./
RUN npm run build

FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.9.24 /uv /uvx /bin/
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY apps/api/src apps/api/src
RUN uv sync --frozen --no-dev --no-editable

FROM python:3.12-slim
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:0.9.24 /uv /bin/uv
COPY --from=builder /app/.venv /app/.venv
COPY pyproject.toml uv.lock .python-version ./
COPY alembic.ini ./
COPY apps/api/start-api.sh ./start-api.sh
COPY apps/api/migrations apps/api/migrations
COPY apps/api/evaluation apps/api/evaluation
COPY --from=web-builder /web/dist /app/web
ENV WEB_DIST_DIR=/app/web
ENV PATH="/app/.venv/bin:$PATH" UV_PYTHON_DOWNLOADS=never
RUN useradd --create-home --uid 10001 api \
    && mkdir -p /home/api/.cache/embeddings \
    && chown api:api /home/api/.cache /home/api/.cache/embeddings
USER api
EXPOSE 8000
CMD ["uvicorn", "pmknowledge.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]

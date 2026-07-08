FROM python:3.13-slim AS base
RUN pip install --no-cache-dir uv && \
    apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

FROM base AS deps
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

FROM base AS runner
WORKDIR /app

RUN addgroup --system --gid 1001 fastapi && \
    adduser --system --uid 1001 --gid 1001 --no-create-home fastapi

COPY --from=deps --chown=fastapi:fastapi /app/.venv /app/.venv
COPY --chown=fastapi:fastapi . .

ENV PATH="/app/.venv/bin:$PATH"
ENV UV_CACHE_DIR="/tmp/uv-cache"

USER fastapi

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

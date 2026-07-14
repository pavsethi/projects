# Backend image: FastAPI served by uvicorn, dependencies managed by uv.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

# Install dependencies first (from the lockfile) for better layer caching.
# The project is package=false, so this installs only the dependencies.
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy the application source.
COPY . .

# Run migrations, then start the server. $PORT is provided by most hosts.
# --no-sync: the environment is already built, so don't re-resolve at runtime.
ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uv run --no-sync alembic upgrade head && uv run --no-sync uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]

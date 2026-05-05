FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Install runtime dependencies directly to avoid packaging failures when local metadata files are missing.
RUN pip install --no-cache-dir \
    "fastapi>=0.111.0" \
    "uvicorn>=0.30.0" \
    "pydantic>=2.7.0" \
    "pydantic-settings>=2.2.1" \
    "httpx>=0.27.0" \
    "langgraph>=0.2.0"

COPY src ./src
COPY scripts ./scripts
COPY .env.example ./.env.example

EXPOSE 8088

# Default command runs API. Worker uses command override in docker-compose.
CMD ["python", "-m", "hz_bank_aiops.api.main"]

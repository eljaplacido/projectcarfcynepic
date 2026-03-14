FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md /app/
COPY src /app/src
COPY config /app/config
COPY demo /app/demo
COPY scripts /app/scripts

# Create var/ directory for local SQLite fallback
RUN mkdir -p /app/var

ARG EXTRAS="kafka"
RUN pip install --upgrade pip \
    && pip install -e ".[${EXTRAS}]"

# Cloud Run sets PORT (default 8080); local dev uses 8000
ENV PORT=8000
EXPOSE ${PORT}

CMD uvicorn src.main:app --host 0.0.0.0 --port ${PORT}

# syntax=docker/dockerfile:1

FROM node:22-alpine AS frontend-builder
WORKDIR /build/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build


FROM python:3.13-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DATA_FILE=/app/runtime-data/state.json

WORKDIR /app

RUN groupadd --system flowpilot && useradd --system --gid flowpilot --create-home flowpilot

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/app ./backend/app
COPY backend/data/seed.json ./backend/data/seed.json
COPY backend/data/evaluation ./backend/data/evaluation
COPY --from=frontend-builder /build/frontend/release-dist ./frontend/release-dist

RUN mkdir -p /app/runtime-data && chown -R flowpilot:flowpilot /app

USER flowpilot
EXPOSE 8011

CMD ["uvicorn", "app.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8011"]

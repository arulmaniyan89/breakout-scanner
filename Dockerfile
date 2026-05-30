# ── Stage 1: Build the React frontend ────────────────────────────────────────
FROM node:22-alpine AS frontend
WORKDIR /app
COPY frontend/package.json .
RUN npm install
COPY frontend/ .
RUN npm run build

# ── Stage 2: Python backend + embed the built frontend ────────────────────────
FROM python:3.12-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ .

# Embed the React build as static files served by FastAPI
COPY --from=frontend /app/dist ./static

ENV PYTHONUNBUFFERED=1 \
    TZ=Asia/Kolkata

EXPOSE 8000

# Render injects $PORT; default to 8000 for local Docker testing
CMD ["sh", "-c", "uvicorn quick_serve:app --host 0.0.0.0 --port ${PORT:-8000}"]

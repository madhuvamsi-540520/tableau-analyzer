# ---- Stage 1: build the React/Vite frontend ------------------------------- #
FROM node:20-slim AS frontend

WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build


# ---- Stage 2: Python API that also serves the built SPA ------------------- #
FROM python:3.12-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app

# The SPA is served by FastAPI, so the browser sees one origin and /api needs
# no CORS. Path matches STATIC_DIR in app/main.py.
COPY --from=frontend /frontend/dist ./static

# Cloud Run injects PORT; default keeps `docker run` working locally.
ENV PORT=8080
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}

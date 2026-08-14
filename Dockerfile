# Multi-stage build: compiles the React frontend, then packages everything
# into a single Python image that serves BOTH the API/WebSocket and the static
# frontend. One service, one port — ideal for a free VM.
#
# Repo structure is preserved inside the image so ROOT_DIR resolves to /app:
#   /app/backend/app/config.py  →  ROOT_DIR = /app
#   /app/frontend/dist          →  FRONTEND_DIST
#   /app/workspace              →  mounted workspace (compose)
#   /app/data                   →  mounted data dir (SQLite)
FROM node:20-alpine AS frontend-build
WORKDIR /fe
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

FROM python:3.11-slim
WORKDIR /app

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ ./backend/
COPY --from=frontend-build /fe/dist /app/frontend/dist

WORKDIR /app/backend
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Stage 1: Build the React frontend
FROM node:22-alpine AS frontend-build
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# Stage 2: Run the Python backend (serves the built frontend too)
FROM python:3.12-slim
LABEL org.opencontainers.image.source="https://github.com/thegspiro/politician-position-tracker" \
      org.opencontainers.image.description="Politician Position Tracker"
WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

# Copy the built frontend into backend/static so FastAPI can serve it
COPY --from=frontend-build /app/dist ./static

# Persistent data directory for the SQLite database. The entrypoint is made
# executable here so the image does not depend on the checkout preserving the
# exec bit (it is not preserved on Windows hosts).
RUN mkdir -p /app/data && chmod +x /app/docker-entrypoint.sh
ENV DATABASE_URL=sqlite:////app/data/politician_tracker.db

EXPOSE 8000

# start-period covers the migration run, which is slow on array-backed disks.
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/api/health' % os.environ.get('PORT', '8000'))" || exit 1

# The entrypoint applies pending Alembic migrations before starting uvicorn.
ENTRYPOINT ["/app/docker-entrypoint.sh"]

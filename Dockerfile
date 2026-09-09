# Stage 1: Build the React frontend
FROM node:20-alpine AS frontend-build
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# Stage 2: Run the Python backend (serves the built frontend too)
FROM python:3.12-slim
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

HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

# The entrypoint applies pending Alembic migrations before starting uvicorn.
ENTRYPOINT ["/app/docker-entrypoint.sh"]

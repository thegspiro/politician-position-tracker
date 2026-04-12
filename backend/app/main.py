import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .database import Base, engine
from .routers import issues, politicians, statements

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Politician Position Tracker")

# CORS is only needed during local dev (Vite on :5173 -> FastAPI on :8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(politicians.router)
app.include_router(issues.router)
app.include_router(statements.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


# --- Serve the React SPA from the built frontend ---
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

if STATIC_DIR.is_dir():
    # Serve static assets (JS, CSS, images) at /assets
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    # Serve favicon and other root-level static files
    @app.get("/favicon.svg")
    async def favicon():
        return FileResponse(STATIC_DIR / "favicon.svg")

    # SPA catch-all: any non-API route serves index.html so React Router works
    @app.get("/{path:path}")
    async def serve_spa(request: Request, path: str):
        file_path = STATIC_DIR / path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(STATIC_DIR / "index.html")

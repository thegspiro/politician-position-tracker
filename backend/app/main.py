import os
import uuid
from pathlib import Path

from fastapi import Depends, FastAPI, File, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from .auth import require_admin, router as auth_router
from .database import get_db
from .models import Issue, Politician, Source, Statement
from .routers import issues, politicians, statements
from .schemas import IssueOut, PoliticianOut, SourceOut, StatementOut

# The schema is owned by Alembic, not by create_all. The container entrypoint
# runs "alembic upgrade head" before starting the server; see the README for
# the local development equivalent.

app = FastAPI(title="Politician Position Tracker")

# CORS is only needed during local dev (Vite on :5173 -> FastAPI on :8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(politicians.router)
app.include_router(issues.router)
app.include_router(statements.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


# --- Upload endpoint ---
# Defaults to the container path; overridable so the app can run (and be tested)
# outside Docker without needing to create /app.
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", "/app/data/uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}


@app.post("/api/uploads")
def upload_file(
    file: UploadFile = File(...),
    _admin: str = Depends(require_admin),
):
    ext = Path(file.filename).suffix.lower() if file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail=f"File type '{ext}' not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )
    filename = f"{uuid.uuid4().hex}{ext}"
    dest = UPLOAD_DIR / filename
    with open(dest, "wb") as f:
        contents = file.file.read()
        f.write(contents)
    return {"url": f"/uploads/{filename}"}


# Mount uploads directory as static files
if UPLOAD_DIR.is_dir():
    app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


# --- Data export endpoint ---
@app.get("/api/export")
def export_data(
    _admin: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    all_politicians = db.query(Politician).order_by(Politician.name).all()
    all_issues = db.query(Issue).order_by(Issue.name).all()
    all_statements = (
        db.query(Statement)
        .options(
            joinedload(Statement.politician),
            joinedload(Statement.issues),
            joinedload(Statement.sources),
        )
        .order_by(Statement.created_at.desc())
        .all()
    )
    # Deduplicate due to joinedload producing cartesian products
    seen_ids: set[int] = set()
    unique_statements = []
    for s in all_statements:
        if s.id not in seen_ids:
            seen_ids.add(s.id)
            unique_statements.append(s)
    all_statements = unique_statements

    return {
        "politicians": [PoliticianOut.model_validate(p).model_dump(mode="json") for p in all_politicians],
        "issues": [IssueOut.model_validate(i).model_dump(mode="json") for i in all_issues],
        "statements": [StatementOut.model_validate(s).model_dump(mode="json") for s in all_statements],
    }


# --- Data import endpoint ---
class ImportData(BaseModel):
    politicians: list[dict] = []
    issues: list[dict] = []
    statements: list[dict] = []


@app.post("/api/import")
def import_data(
    data: ImportData,
    _admin: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Import data from a JSON backup. Merges with existing data (skips duplicates by name)."""
    from datetime import datetime as dt

    stats = {"politicians": 0, "issues": 0, "statements": 0, "sources": 0}

    # Map old IDs to new IDs
    politician_id_map: dict[int, int] = {}
    issue_id_map: dict[int, int] = {}

    # Import politicians
    for pol_data in data.politicians:
        existing = db.query(Politician).filter(Politician.name == pol_data.get("name")).first()
        if existing:
            politician_id_map[pol_data.get("id", 0)] = existing.id
            continue
        pol = Politician(
            name=pol_data.get("name", ""),
            party=pol_data.get("party", ""),
            office=pol_data.get("office", ""),
            state=pol_data.get("state"),
            photo_url=pol_data.get("photo_url"),
        )
        db.add(pol)
        db.flush()
        politician_id_map[pol_data.get("id", 0)] = pol.id
        stats["politicians"] += 1

    # Import issues
    for issue_data in data.issues:
        existing = db.query(Issue).filter(Issue.name == issue_data.get("name")).first()
        if existing:
            issue_id_map[issue_data.get("id", 0)] = existing.id
            continue
        issue = Issue(
            name=issue_data.get("name", ""),
            description=issue_data.get("description"),
        )
        db.add(issue)
        db.flush()
        issue_id_map[issue_data.get("id", 0)] = issue.id
        stats["issues"] += 1

    # Import statements
    for stmt_data in data.statements:
        # Check for duplicate by title + politician
        old_pol_id = stmt_data.get("politician_id", 0)
        new_pol_id = politician_id_map.get(old_pol_id)
        if not new_pol_id:
            continue

        existing = (
            db.query(Statement)
            .filter(Statement.title == stmt_data.get("title"), Statement.politician_id == new_pol_id)
            .first()
        )
        if existing:
            continue

        post_date = None
        if stmt_data.get("post_date"):
            try:
                post_date = dt.fromisoformat(stmt_data["post_date"].replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass

        stmt = Statement(
            politician_id=new_pol_id,
            title=stmt_data.get("title", ""),
            analysis=stmt_data.get("analysis", ""),
            post_url=stmt_data.get("post_url", ""),
            post_platform=stmt_data.get("post_platform", ""),
            post_content=stmt_data.get("post_content"),
            screenshot_url=stmt_data.get("screenshot_url"),
            post_date=post_date,
        )

        # Attach issues
        issue_entries = stmt_data.get("issues", [])
        for issue_entry in issue_entries:
            old_issue_id = issue_entry.get("id", 0)
            new_issue_id = issue_id_map.get(old_issue_id)
            if new_issue_id:
                issue_obj = db.query(Issue).get(new_issue_id)
                if issue_obj:
                    stmt.issues.append(issue_obj)

        db.add(stmt)
        db.flush()

        # Import sources
        for src_data in stmt_data.get("sources", []):
            source = Source(
                statement_id=stmt.id,
                source_type=src_data.get("source_type", "analysis"),
                title=src_data.get("title", ""),
                url=src_data.get("url", ""),
                description=src_data.get("description"),
            )
            db.add(source)
            stats["sources"] += 1

        stats["statements"] += 1

    db.commit()
    return {"message": "Import complete", "imported": stats}


# --- Serve the React SPA from the built frontend ---
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def resolve_static_file(path: str) -> Path | None:
    """Resolve a request path to a file inside STATIC_DIR, or None.

    The request path is attacker-controlled and arrives percent-decoded, so it
    can contain ".." segments that escape STATIC_DIR (e.g. "%2e%2e/data/...").
    Resolving the candidate and requiring STATIC_DIR to be one of its parents
    confines every response to the built frontend directory.
    """
    static_root = STATIC_DIR.resolve()
    candidate = (static_root / path).resolve()
    if static_root not in candidate.parents:
        return None
    if not candidate.is_file():
        return None
    return candidate


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
        file_path = resolve_static_file(path)
        if file_path is not None:
            return FileResponse(file_path)
        return FileResponse(STATIC_DIR / "index.html")

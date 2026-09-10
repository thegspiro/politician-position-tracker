import os
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.exception_handlers import http_exception_handler
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import citations, settings
from .auth import require_admin, router as auth_router
from .database import get_db
from .models import Issue, Politician, Source, Statement, new_source_uid
from .routers import issues, politicians, statements, users
from .schemas import IssueOut, PoliticianOut, SourceOut, StatementOut

# The schema is owned by Alembic, not by create_all. The container entrypoint
# runs "alembic upgrade head" before starting the server; see the README for
# the local development equivalent.

app = FastAPI(title="Politician Position Tracker")

# --- Security headers ---
#
# The application embeds third-party media, so the policy has to name the hosts
# those embeds come from. It is deliberately strict about what may execute:
# script-src lists only the embed providers, and object-src is closed entirely.
#
# frame-src is broad because a "document" source can point at any publisher's
# PDF. Framing arbitrary https documents is the feature; executing arbitrary
# script is not, and script-src is what prevents that.
CSP_DIRECTIVES = [
    "default-src 'self'",
    "script-src 'self' https://platform.twitter.com https://embed.bsky.app "
    "https://cdn.syndication.twimg.com",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: https:",
    "media-src 'self' https:",
    "font-src 'self' data:",
    "connect-src 'self' https://embed.bsky.app https://cdn.syndication.twimg.com",
    "frame-src https:",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
]

# Set CONTENT_SECURITY_POLICY to override the default, or to the empty string to
# disable the header while diagnosing a blocked embed.
CONTENT_SECURITY_POLICY = os.environ.get(
    "CONTENT_SECURITY_POLICY", "; ".join(CSP_DIRECTIVES)
)

# Uploaded files are attacker-influenced content served from our own origin.
# This policy lets nothing in them run, load or navigate.
UPLOAD_CSP = "default-src 'none'; img-src 'self'; style-src 'unsafe-inline'; sandbox"


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)

    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault(
        "Permissions-Policy", "geolocation=(), microphone=(), camera=()"
    )

    if request.url.path.startswith("/uploads/"):
        response.headers["Content-Security-Policy"] = UPLOAD_CSP
        response.headers["X-Frame-Options"] = "DENY"
    elif CONTENT_SECURITY_POLICY:
        response.headers.setdefault(
            "Content-Security-Policy", CONTENT_SECURITY_POLICY
        )

    return response


# CORS is only needed during local dev (Vite on :5173 -> FastAPI on :8000), so
# it is off unless CORS_ORIGINS names the origins to allow. Enabling it in
# production would let another site make credentialed requests to this API.
CORS_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("CORS_ORIGINS", "").split(",")
    if origin.strip()
]

if CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include routers
app.include_router(auth_router)
app.include_router(politicians.router)
app.include_router(issues.router)
app.include_router(statements.router)
app.include_router(users.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/config")
def public_config():
    """Site settings the frontend needs before rendering."""
    return {
        "site_name": settings.SITE_NAME,
        "citation_style": settings.CITATION_STYLE,
        "citation_styles": list(citations.CITATION_STYLES),
    }


# --- Upload endpoint ---
# Defaults to the container path; overridable so the app can run (and be tested)
# outside Docker without needing to create /app.
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", "/app/data/uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_MB", "5")) * 1024 * 1024
_UPLOAD_CHUNK = 64 * 1024

# SVG is deliberately absent. Uploads are served from the application's own
# origin, and an SVG is a script-bearing document: opening one would execute
# attacker-controlled JavaScript with access to same-origin storage. Raster
# formats cannot do this.
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}

# Leading bytes each accepted format must start with. Checked so that the
# extension cannot be used to disguise a different file type.
_MAGIC_PREFIXES: dict[str, tuple[bytes, ...]] = {
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".gif": (b"GIF87a", b"GIF89a"),
    ".webp": (b"RIFF",),
}


def _content_matches_extension(head: bytes, ext: str) -> bool:
    prefixes = _MAGIC_PREFIXES.get(ext, ())
    if not any(head.startswith(prefix) for prefix in prefixes):
        return False
    # RIFF is a container; confirm the WEBP form specifically.
    if ext == ".webp":
        return len(head) >= 12 and head[8:12] == b"WEBP"
    return True


@app.post("/api/uploads")
def upload_file(
    file: UploadFile = File(...),
    _admin: str = Depends(require_admin),
):
    ext = Path(file.filename).suffix.lower() if file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"File type '{ext}' not allowed. "
                f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            ),
        )

    head = file.file.read(12)
    if not _content_matches_extension(head, ext):
        raise HTTPException(
            status_code=400,
            detail=f"File content does not match the '{ext}' extension.",
        )

    filename = f"{uuid.uuid4().hex}{ext}"
    dest = UPLOAD_DIR / filename

    # Streamed with a running total so an oversized upload is refused instead of
    # being read into memory in full.
    written = len(head)
    try:
        with open(dest, "wb") as out:
            out.write(head)
            while chunk := file.file.read(_UPLOAD_CHUNK):
                written += len(chunk)
                if written > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail=(
                            "File is larger than the "
                            f"{MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit."
                        ),
                    )
                out.write(chunk)
    except Exception:
        dest.unlink(missing_ok=True)
        raise

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
def _parse_datetime(value: object) -> datetime | None:
    """Parse an ISO-8601 string from a backup, tolerating a trailing "Z"."""
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


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
    stats = {"politicians": 0, "issues": 0, "statements": 0, "sources": 0}

    # uids must stay unique. A backup taken from another instance can collide
    # with a uid already present here, so taken uids are tracked and a fresh
    # one is generated on conflict.
    taken_uids = {uid for (uid,) in db.query(Source.uid).all()}

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

        post_date = _parse_datetime(stmt_data.get("post_date"))

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
                issue_obj = db.get(Issue, new_issue_id)
                if issue_obj:
                    stmt.issues.append(issue_obj)

        db.add(stmt)
        db.flush()

        # Import sources
        for position, src_data in enumerate(stmt_data.get("sources", [])):
            uid = src_data.get("uid")
            if not uid or uid in taken_uids:
                uid = new_source_uid()
                while uid in taken_uids:
                    uid = new_source_uid()
            taken_uids.add(uid)

            source = Source(
                statement_id=stmt.id,
                uid=uid,
                source_type=src_data.get("source_type", "analysis"),
                title=src_data.get("title", ""),
                url=src_data.get("url", ""),
                description=src_data.get("description"),
                media_type=src_data.get("media_type") or "webpage",
                publisher=src_data.get("publisher"),
                published_date=_parse_datetime(src_data.get("published_date")),
                excerpt=src_data.get("excerpt"),
                locator=src_data.get("locator"),
                archive_url=src_data.get("archive_url"),
                archived_at=_parse_datetime(src_data.get("archived_at")),
                retrieved_at=_parse_datetime(src_data.get("retrieved_at")),
                sort_order=src_data.get("sort_order", position),
                authors=src_data.get("authors") or None,
                container_title=src_data.get("container_title"),
                edition=src_data.get("edition"),
                document_type=src_data.get("document_type"),
                bill_number=src_data.get("bill_number"),
                congress_number=src_data.get("congress_number"),
                congress_session=src_data.get("congress_session"),
                committee=src_data.get("committee"),
                report_number=src_data.get("report_number"),
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


# Prefixes that belong to the backend. A request under one of these must never
# be answered with the SPA shell, or a missing endpoint would look like a
# successful HTML response to the client.
BACKEND_PREFIXES = ("/api", "/uploads", "/docs", "/redoc", "/openapi.json")


def _is_backend_path(path: str) -> bool:
    return any(path == prefix or path.startswith(prefix + "/") for prefix in BACKEND_PREFIXES)


if STATIC_DIR.is_dir():
    # Serve static assets (JS, CSS, images) at /assets
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    # Serve favicon and other root-level static files
    @app.get("/favicon.svg")
    async def favicon():
        return FileResponse(STATIC_DIR / "favicon.svg")

    # The SPA fallback is an exception handler rather than a "/{path:path}"
    # route. A catch-all route matches before Starlette's trailing-slash
    # redirect runs, so it shadowed every collection endpoint: a request for
    # "/api/politicians" matched the catch-all and returned index.html instead
    # of JSON. As a 404 handler it runs only after real routing has failed.
    @app.exception_handler(StarletteHTTPException)
    async def spa_fallback(request: Request, exc: StarletteHTTPException):
        if exc.status_code != 404 or _is_backend_path(request.url.path):
            return await http_exception_handler(request, exc)

        file_path = resolve_static_file(request.url.path.lstrip("/"))
        if file_path is not None:
            return FileResponse(file_path)
        return FileResponse(STATIC_DIR / "index.html")

import json
import logging
import os
from enum import Enum

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse, Response
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from .. import archiving, citations, settings
from ..auth import require_admin
from ..database import get_db
from ..models import Issue, Politician, Source, Statement, User, new_source_uid
from ..schemas import (
    PaginatedResponse,
    SourceCreate,
    StatementCreate,
    StatementListOut,
    StatementOut,
    StatementUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/statements", tags=["statements"])


class StatementSort(str, Enum):
    """Orderings the timeline offers.

    Sorting has to happen in the database: the timeline shows one page of
    results, so ordering the rows the client already holds would only reorder
    that page and would silently misrepresent the whole set.
    """

    newest = "newest"
    oldest = "oldest"
    politician_az = "politician-az"


# A statement is dated by its post, falling back to when it was recorded. This
# matches what the timeline displays, so the order agrees with the visible date.
def _statement_date():
    return func.coalesce(Statement.post_date, Statement.created_at)


def apply_sort(query, sort: StatementSort):
    """Order a statement query, always with a unique tiebreaker.

    Without the trailing id, rows sharing a date can swap places between
    requests, which makes paging past them unreliable.
    """
    if sort is StatementSort.oldest:
        return query.order_by(_statement_date().asc(), Statement.id.asc())
    if sort is StatementSort.politician_az:
        return query.join(Statement.politician).order_by(
            Politician.name.asc(), _statement_date().desc(), Statement.id.desc()
        )
    return query.order_by(_statement_date().desc(), Statement.id.desc())

# Fields copied verbatim from the request onto a Source row. uid is excluded
# because it is assigned on insert and never overwritten; sort_order is
# excluded because it is derived from the submitted order.
SOURCE_FIELDS = (
    "source_type",
    "title",
    "url",
    "description",
    "media_type",
    "publisher",
    "published_date",
    "excerpt",
    "locator",
    "archive_url",
    "archived_at",
    "retrieved_at",
    "container_title",
    "edition",
    "document_type",
    "bill_number",
    "congress_number",
    "congress_session",
    "committee",
    "report_number",
)


def _apply_source_fields(
    source: Source, data: SourceCreate, sort_order: int, actor: User | None = None
) -> None:
    for field in SOURCE_FIELDS:
        setattr(source, field, getattr(data, field))
    # Authors are validated as models but stored in a JSON column, so they are
    # written as plain dicts with empty entries dropped.
    source.authors = [
        author.model_dump(exclude_none=True) for author in data.authors
    ] or None
    source.sort_order = sort_order
    if actor is not None:
        if source.created_by_id is None:
            source.created_by_id = actor.id
        source.updated_by_id = actor.id


def sync_sources(
    db: Session,
    statement_id: int,
    incoming: list[SourceCreate],
    actor: User | None = None,
) -> None:
    """Reconcile a statement's sources with the submitted list.

    Sources are matched by uid and updated in place. Previously this deleted
    every row and reinserted, which changed both the primary key and the uid on
    every save and so broke any citation or permalink pointing at a source.
    Rows whose uid is absent from the submission are deleted; entries without a
    uid are new and are assigned one.

    Display order is taken from the submitted order rather than from the
    client-supplied sort_order, so the list renders exactly as the admin
    arranged it.
    """
    existing = {
        source.uid: source
        for source in db.query(Source).filter(Source.statement_id == statement_id).all()
    }
    submitted_uids: set[str] = set()

    for position, data in enumerate(incoming):
        # A uid is only honoured if it belongs to this statement and has not
        # already been claimed earlier in the same submission; anything else is
        # treated as a new source rather than silently overwriting a row.
        source = None
        if data.uid and data.uid not in submitted_uids:
            source = existing.get(data.uid)
        if source is None:
            source = Source(statement_id=statement_id, uid=new_source_uid())
            db.add(source)
        submitted_uids.add(source.uid)
        _apply_source_fields(source, data, position, actor)

    for uid, source in existing.items():
        if uid not in submitted_uids:
            db.delete(source)


@router.get("", response_model=PaginatedResponse[StatementListOut])
def list_statements(
    politician_id: int | None = Query(None),
    issue_id: int | None = Query(None),
    platform: str | None = Query(None),
    search: str | None = Query(None),
    sort: StatementSort = Query(StatementSort.newest),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(Statement).options(
        joinedload(Statement.politician),
        joinedload(Statement.issues),
    )
    if politician_id:
        query = query.filter(Statement.politician_id == politician_id)
    if issue_id:
        query = query.join(Statement.issues).filter(Issue.id == issue_id)
    if platform:
        query = query.filter(Statement.post_platform == platform)
    if search:
        query = query.filter(
            Statement.title.ilike(f"%{search}%")
            | Statement.analysis.ilike(f"%{search}%")
            | Statement.post_content.ilike(f"%{search}%")
        )

    # Get total count from a subquery (without joinedload) to avoid duplicates
    count_query = db.query(Statement.id)
    if politician_id:
        count_query = count_query.filter(Statement.politician_id == politician_id)
    if issue_id:
        count_query = count_query.join(Statement.issues).filter(Issue.id == issue_id)
    if platform:
        count_query = count_query.filter(Statement.post_platform == platform)
    if search:
        count_query = count_query.filter(
            Statement.title.ilike(f"%{search}%")
            | Statement.analysis.ilike(f"%{search}%")
            | Statement.post_content.ilike(f"%{search}%")
        )
    total = count_query.distinct().count()

    all_items = apply_sort(query, sort).offset(skip).limit(limit).all()
    # Deduplicate due to joinedload
    seen: set[int] = set()
    items = []
    for s in all_items:
        if s.id not in seen:
            seen.add(s.id)
            items.append(s)
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.get("/{statement_id}", response_model=StatementOut)
def get_statement(statement_id: int, db: Session = Depends(get_db)):
    statement = (
        db.query(Statement)
        .options(
            joinedload(Statement.politician),
            joinedload(Statement.issues),
            joinedload(Statement.sources),
            joinedload(Statement.created_by),
            joinedload(Statement.updated_by),
        )
        .filter(Statement.id == statement_id)
        .first()
    )
    if not statement:
        raise HTTPException(status_code=404, detail="Statement not found")
    return statement


@router.post("", response_model=StatementOut, status_code=201)
def create_statement(
    data: StatementCreate,
    background: BackgroundTasks,
    actor: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    sources_data = data.sources
    issue_ids = data.issue_ids
    statement_dict = data.model_dump(exclude={"sources", "issue_ids"})
    statement = Statement(**statement_dict)
    statement.created_by_id = actor.id
    statement.updated_by_id = actor.id

    # Attach issues
    if issue_ids:
        issues = db.query(Issue).filter(Issue.id.in_(issue_ids)).all()
        if len(issues) != len(issue_ids):
            raise HTTPException(status_code=400, detail="One or more issue IDs are invalid")
        statement.issues = issues

    db.add(statement)
    db.flush()

    sync_sources(db, statement.id, sources_data, actor)

    db.commit()
    db.refresh(statement)
    schedule_archiving(background, statement.id)

    # Reload with relationships
    return (
        db.query(Statement)
        .options(
            joinedload(Statement.politician),
            joinedload(Statement.issues),
            joinedload(Statement.sources),
            joinedload(Statement.created_by),
            joinedload(Statement.updated_by),
        )
        .filter(Statement.id == statement.id)
        .first()
    )


@router.put("/{statement_id}", response_model=StatementOut)
def update_statement(
    statement_id: int,
    data: StatementUpdate,
    background: BackgroundTasks,
    actor: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    statement = db.query(Statement).filter(Statement.id == statement_id).first()
    if not statement:
        raise HTTPException(status_code=404, detail="Statement not found")

    sources_data = data.sources
    issue_ids = data.issue_ids
    statement_dict = data.model_dump(exclude={"sources", "issue_ids"})
    for key, value in statement_dict.items():
        setattr(statement, key, value)
    statement.updated_by_id = actor.id

    # Update issues
    if issue_ids is not None:
        issues = db.query(Issue).filter(Issue.id.in_(issue_ids)).all()
        if len(issues) != len(issue_ids):
            raise HTTPException(status_code=400, detail="One or more issue IDs are invalid")
        statement.issues = issues
    else:
        statement.issues = []

    sync_sources(db, statement_id, sources_data, actor)

    db.commit()
    db.refresh(statement)
    schedule_archiving(background, statement_id)

    return (
        db.query(Statement)
        .options(
            joinedload(Statement.politician),
            joinedload(Statement.issues),
            joinedload(Statement.sources),
            joinedload(Statement.created_by),
            joinedload(Statement.updated_by),
        )
        .filter(Statement.id == statement.id)
        .first()
    )


@router.delete("/{statement_id}", status_code=204)
def delete_statement(
    statement_id: int,
    _admin: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    statement = db.query(Statement).filter(Statement.id == statement_id).first()
    if not statement:
        raise HTTPException(status_code=404, detail="Statement not found")
    db.delete(statement)
    db.commit()


# --- Archiving ----------------------------------------------------------


def archive_pending_sources(statement_id: int) -> None:
    """Capture snapshots for a statement's un-archived sources.

    Runs after the response has been sent, so a slow or unreachable archive
    service never delays a save. Each source is committed on its own: one
    failure must not discard the snapshots that did succeed.
    """
    from ..database import SessionLocal

    db = SessionLocal()
    try:
        sources = (
            db.query(Source)
            .filter(Source.statement_id == statement_id, Source.archive_url.is_(None))
            .all()
        )
        for source in sources:
            if not archiving.is_submittable(source.url):
                continue
            result = archiving.archive_url(source.url)
            if not result.ok:
                continue
            source.archive_url = result.url
            source.archived_at = result.timestamp
            db.commit()
    except Exception:
        logger.exception("Archiving sources for statement %s failed", statement_id)
        db.rollback()
    finally:
        db.close()


def schedule_archiving(background: BackgroundTasks, statement_id: int) -> None:
    if archiving.ARCHIVE_ENABLED:
        background.add_task(archive_pending_sources, statement_id)


@router.post("/{statement_id}/sources/{uid}/archive")
def archive_source_now(
    statement_id: int,
    uid: str,
    _admin: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Capture a snapshot for one source on demand.

    Available whether or not automatic archiving is enabled, so a deployment
    that keeps it off can still archive deliberately, and a source whose
    automatic capture failed can be retried without re-saving the statement.
    """
    source = (
        db.query(Source)
        .filter(Source.statement_id == statement_id, Source.uid == uid)
        .first()
    )
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    if not archiving.is_submittable(source.url):
        raise HTTPException(
            status_code=400, detail="This source's URL cannot be archived"
        )

    result = archiving.archive_url(source.url)
    if not result.ok:
        # The archive service is outside our control, so this is a gateway
        # failure rather than a fault in the request.
        raise HTTPException(
            status_code=502,
            detail=f"Could not archive this source: {result.error}",
        )

    source.archive_url = result.url
    source.archived_at = result.timestamp
    db.commit()
    db.refresh(source)
    return {"archive_url": source.archive_url, "archived_at": source.archived_at}


# --- Citations ----------------------------------------------------------


def _load_statement_for_citation(statement_id: int, db: Session) -> Statement:
    statement = (
        db.query(Statement)
        .options(joinedload(Statement.politician), joinedload(Statement.sources))
        .filter(Statement.id == statement_id)
        .first()
    )
    if not statement:
        raise HTTPException(status_code=404, detail="Statement not found")
    return statement


def _ordered_sources(statement: Statement) -> list[Source]:
    return sorted(statement.sources, key=lambda s: (s.sort_order, s.id))


def _page_url(request: Request, statement_id: int) -> str:
    """The public URL of this statement's page, for the "cite this page" form.

    Derived from the request, so it is correct behind a reverse proxy only when
    the proxy forwards the original host and uvicorn is run with
    --proxy-headers. SITE_URL overrides it when that is not the case.
    """
    configured = os.environ.get("SITE_URL", "").strip().rstrip("/")
    if configured:
        return f"{configured}/statements/{statement_id}"
    return str(request.base_url).rstrip("/") + f"/statements/{statement_id}"


def _citation_inputs(
    statement: Statement, request: Request
) -> tuple[list[tuple[Source, citations.CitationInput]], citations.CitationInput, citations.CitationInput]:
    sources = [
        (source, citations.from_source(source)) for source in _ordered_sources(statement)
    ]
    post = citations.from_statement_post(statement)
    page = citations.from_statement_page(
        statement, settings.SITE_NAME, _page_url(request, statement.id)
    )
    return sources, post, page


@router.get("/{statement_id}/citations")
def get_statement_citations(
    statement_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Every citation for a statement: its sources, its post, and its page."""
    statement = _load_statement_for_citation(statement_id, db)
    sources, post, page = _citation_inputs(statement, request)

    return {
        "default_style": settings.CITATION_STYLE,
        "site_name": settings.SITE_NAME,
        "sources": [
            {
                "uid": source.uid,
                "source_type": source.source_type,
                "sort_order": source.sort_order,
                **citations.render_all(data),
            }
            for source, data in sources
        ],
        "post": citations.render_all(post),
        "page": citations.render_all(page),
    }


def _export_entries(
    statement: Statement, request: Request
) -> list[tuple[str, citations.CitationInput]]:
    """Every citable item for a statement, keyed by a stable export id."""
    sources, post, page = _citation_inputs(statement, request)
    entries = [(f"source-{source.uid}", data) for source, data in sources]
    entries.append((f"post-{statement.id}", post))
    entries.append((f"statement-{statement.id}", page))
    return entries


@router.get("/{statement_id}/citations.json")
def export_statement_citations_csl(
    statement_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """CSL-JSON, the interchange format Zotero and pandoc read."""
    statement = _load_statement_for_citation(statement_id, db)
    payload = [
        citations.to_csl_json(data, entry_id)
        for entry_id, data in _export_entries(statement, request)
    ]
    return Response(
        content=json.dumps(payload, indent=2),
        media_type="application/json",
        headers={
            "Content-Disposition": (
                f'attachment; filename="statement-{statement_id}-citations.json"'
            )
        },
    )


@router.get("/{statement_id}/citations.bib", response_class=PlainTextResponse)
def export_statement_citations_bibtex(
    statement_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    statement = _load_statement_for_citation(statement_id, db)
    body = "\n\n".join(
        citations.to_bibtex(data, entry_key)
        for entry_key, data in _export_entries(statement, request)
    )
    return PlainTextResponse(
        content=body + "\n",
        headers={
            "Content-Disposition": (
                f'attachment; filename="statement-{statement_id}-citations.bib"'
            )
        },
    )

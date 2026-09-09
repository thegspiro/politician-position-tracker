from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from ..auth import require_admin
from ..database import get_db
from ..models import Issue, Source, Statement, new_source_uid
from ..schemas import (
    PaginatedResponse,
    SourceCreate,
    StatementCreate,
    StatementListOut,
    StatementOut,
    StatementUpdate,
)

router = APIRouter(prefix="/api/statements", tags=["statements"])

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
)


def _apply_source_fields(source: Source, data: SourceCreate, sort_order: int) -> None:
    for field in SOURCE_FIELDS:
        setattr(source, field, getattr(data, field))
    source.sort_order = sort_order


def sync_sources(
    db: Session, statement_id: int, incoming: list[SourceCreate]
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
        _apply_source_fields(source, data, position)

    for uid, source in existing.items():
        if uid not in submitted_uids:
            db.delete(source)


@router.get("", response_model=PaginatedResponse[StatementListOut])
def list_statements(
    politician_id: int | None = Query(None),
    issue_id: int | None = Query(None),
    platform: str | None = Query(None),
    search: str | None = Query(None),
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

    all_items = (
        query.order_by(Statement.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
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
    _admin: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    sources_data = data.sources
    issue_ids = data.issue_ids
    statement_dict = data.model_dump(exclude={"sources", "issue_ids"})
    statement = Statement(**statement_dict)

    # Attach issues
    if issue_ids:
        issues = db.query(Issue).filter(Issue.id.in_(issue_ids)).all()
        if len(issues) != len(issue_ids):
            raise HTTPException(status_code=400, detail="One or more issue IDs are invalid")
        statement.issues = issues

    db.add(statement)
    db.flush()

    sync_sources(db, statement.id, sources_data)

    db.commit()
    db.refresh(statement)

    # Reload with relationships
    return (
        db.query(Statement)
        .options(
            joinedload(Statement.politician),
            joinedload(Statement.issues),
            joinedload(Statement.sources),
        )
        .filter(Statement.id == statement.id)
        .first()
    )


@router.put("/{statement_id}", response_model=StatementOut)
def update_statement(
    statement_id: int,
    data: StatementUpdate,
    _admin: str = Depends(require_admin),
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

    # Update issues
    if issue_ids is not None:
        issues = db.query(Issue).filter(Issue.id.in_(issue_ids)).all()
        if len(issues) != len(issue_ids):
            raise HTTPException(status_code=400, detail="One or more issue IDs are invalid")
        statement.issues = issues
    else:
        statement.issues = []

    sync_sources(db, statement_id, sources_data)

    db.commit()
    db.refresh(statement)

    return (
        db.query(Statement)
        .options(
            joinedload(Statement.politician),
            joinedload(Statement.issues),
            joinedload(Statement.sources),
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

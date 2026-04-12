from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..models import Source, Statement
from ..schemas import StatementCreate, StatementListOut, StatementOut, StatementUpdate

router = APIRouter(prefix="/api/statements", tags=["statements"])


@router.get("/", response_model=list[StatementListOut])
def list_statements(
    politician_id: int | None = Query(None),
    issue_id: int | None = Query(None),
    platform: str | None = Query(None),
    search: str | None = Query(None),
    db: Session = Depends(get_db),
):
    query = (
        db.query(Statement)
        .options(joinedload(Statement.politician), joinedload(Statement.issue))
    )
    if politician_id:
        query = query.filter(Statement.politician_id == politician_id)
    if issue_id:
        query = query.filter(Statement.issue_id == issue_id)
    if platform:
        query = query.filter(Statement.post_platform == platform)
    if search:
        query = query.filter(
            Statement.title.ilike(f"%{search}%")
            | Statement.analysis.ilike(f"%{search}%")
            | Statement.post_content.ilike(f"%{search}%")
        )
    return query.order_by(Statement.created_at.desc()).all()


@router.get("/{statement_id}", response_model=StatementOut)
def get_statement(statement_id: int, db: Session = Depends(get_db)):
    statement = (
        db.query(Statement)
        .options(
            joinedload(Statement.politician),
            joinedload(Statement.issue),
            joinedload(Statement.sources),
        )
        .filter(Statement.id == statement_id)
        .first()
    )
    if not statement:
        raise HTTPException(status_code=404, detail="Statement not found")
    return statement


@router.post("/", response_model=StatementOut, status_code=201)
def create_statement(data: StatementCreate, db: Session = Depends(get_db)):
    sources_data = data.sources
    statement_dict = data.model_dump(exclude={"sources"})
    statement = Statement(**statement_dict)
    db.add(statement)
    db.flush()

    for source_data in sources_data:
        source = Source(statement_id=statement.id, **source_data.model_dump())
        db.add(source)

    db.commit()
    db.refresh(statement)

    # Reload with relationships
    return (
        db.query(Statement)
        .options(
            joinedload(Statement.politician),
            joinedload(Statement.issue),
            joinedload(Statement.sources),
        )
        .filter(Statement.id == statement.id)
        .first()
    )


@router.put("/{statement_id}", response_model=StatementOut)
def update_statement(statement_id: int, data: StatementUpdate, db: Session = Depends(get_db)):
    statement = db.query(Statement).filter(Statement.id == statement_id).first()
    if not statement:
        raise HTTPException(status_code=404, detail="Statement not found")

    sources_data = data.sources
    statement_dict = data.model_dump(exclude={"sources"})
    for key, value in statement_dict.items():
        setattr(statement, key, value)

    # Replace sources
    db.query(Source).filter(Source.statement_id == statement_id).delete()
    for source_data in sources_data:
        source = Source(statement_id=statement_id, **source_data.model_dump())
        db.add(source)

    db.commit()
    db.refresh(statement)

    return (
        db.query(Statement)
        .options(
            joinedload(Statement.politician),
            joinedload(Statement.issue),
            joinedload(Statement.sources),
        )
        .filter(Statement.id == statement.id)
        .first()
    )


@router.delete("/{statement_id}", status_code=204)
def delete_statement(statement_id: int, db: Session = Depends(get_db)):
    statement = db.query(Statement).filter(Statement.id == statement_id).first()
    if not statement:
        raise HTTPException(status_code=404, detail="Statement not found")
    db.delete(statement)
    db.commit()

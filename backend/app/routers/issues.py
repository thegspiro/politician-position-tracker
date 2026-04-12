from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from ..auth import require_admin
from ..database import get_db
from ..models import Issue
from ..schemas import (
    IssueCreate,
    IssueDetailOut,
    IssueOut,
    PaginatedResponse,
)

router = APIRouter(prefix="/api/issues", tags=["issues"])


@router.get("/", response_model=PaginatedResponse[IssueOut])
def list_issues(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    total = db.query(Issue).count()
    items = (
        db.query(Issue)
        .order_by(Issue.name)
        .offset(skip)
        .limit(limit)
        .all()
    )
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.get("/{issue_id}", response_model=IssueDetailOut)
def get_issue(issue_id: int, db: Session = Depends(get_db)):
    issue = (
        db.query(Issue)
        .options(
            joinedload(Issue.statements).joinedload("politician"),
            joinedload(Issue.statements).joinedload("issues"),
        )
        .filter(Issue.id == issue_id)
        .first()
    )
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    return issue


@router.post("/", response_model=IssueOut, status_code=201)
def create_issue(
    data: IssueCreate,
    _admin: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    issue = Issue(**data.model_dump())
    db.add(issue)
    db.commit()
    db.refresh(issue)
    return issue


@router.put("/{issue_id}", response_model=IssueOut)
def update_issue(
    issue_id: int,
    data: IssueCreate,
    _admin: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    for key, value in data.model_dump().items():
        setattr(issue, key, value)
    db.commit()
    db.refresh(issue)
    return issue


@router.delete("/{issue_id}", status_code=204)
def delete_issue(
    issue_id: int,
    _admin: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    db.delete(issue)
    db.commit()

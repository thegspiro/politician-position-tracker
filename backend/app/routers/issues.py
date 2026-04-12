from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..models import Issue
from ..schemas import IssueCreate, IssueDetailOut, IssueOut

router = APIRouter(prefix="/api/issues", tags=["issues"])


@router.get("/", response_model=list[IssueOut])
def list_issues(db: Session = Depends(get_db)):
    return db.query(Issue).order_by(Issue.name).all()


@router.get("/{issue_id}", response_model=IssueDetailOut)
def get_issue(issue_id: int, db: Session = Depends(get_db)):
    issue = (
        db.query(Issue)
        .options(
            joinedload(Issue.statements).joinedload("politician"),
            joinedload(Issue.statements).joinedload("issue"),
        )
        .filter(Issue.id == issue_id)
        .first()
    )
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    return issue


@router.post("/", response_model=IssueOut, status_code=201)
def create_issue(data: IssueCreate, db: Session = Depends(get_db)):
    issue = Issue(**data.model_dump())
    db.add(issue)
    db.commit()
    db.refresh(issue)
    return issue


@router.put("/{issue_id}", response_model=IssueOut)
def update_issue(issue_id: int, data: IssueCreate, db: Session = Depends(get_db)):
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    for key, value in data.model_dump().items():
        setattr(issue, key, value)
    db.commit()
    db.refresh(issue)
    return issue


@router.delete("/{issue_id}", status_code=204)
def delete_issue(issue_id: int, db: Session = Depends(get_db)):
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    db.delete(issue)
    db.commit()

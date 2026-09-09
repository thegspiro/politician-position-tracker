from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from ..auth import require_admin
from ..database import get_db
from ..models import Politician
from ..schemas import (
    PaginatedResponse,
    PoliticianCreate,
    PoliticianDetailOut,
    PoliticianOut,
)

router = APIRouter(prefix="/api/politicians", tags=["politicians"])


@router.get("", response_model=PaginatedResponse[PoliticianOut])
def list_politicians(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    total = db.query(Politician).count()
    items = (
        db.query(Politician)
        .order_by(Politician.name)
        .offset(skip)
        .limit(limit)
        .all()
    )
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.get("/{politician_id}", response_model=PoliticianDetailOut)
def get_politician(politician_id: int, db: Session = Depends(get_db)):
    politician = (
        db.query(Politician)
        .options(
            joinedload(Politician.statements).joinedload("politician"),
            joinedload(Politician.statements).joinedload("issues"),
        )
        .filter(Politician.id == politician_id)
        .first()
    )
    if not politician:
        raise HTTPException(status_code=404, detail="Politician not found")
    return politician


@router.post("", response_model=PoliticianOut, status_code=201)
def create_politician(
    data: PoliticianCreate,
    _admin: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    politician = Politician(**data.model_dump())
    db.add(politician)
    db.commit()
    db.refresh(politician)
    return politician


@router.put("/{politician_id}", response_model=PoliticianOut)
def update_politician(
    politician_id: int,
    data: PoliticianCreate,
    _admin: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    politician = db.query(Politician).filter(Politician.id == politician_id).first()
    if not politician:
        raise HTTPException(status_code=404, detail="Politician not found")
    for key, value in data.model_dump().items():
        setattr(politician, key, value)
    db.commit()
    db.refresh(politician)
    return politician


@router.delete("/{politician_id}", status_code=204)
def delete_politician(
    politician_id: int,
    _admin: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    politician = db.query(Politician).filter(Politician.id == politician_id).first()
    if not politician:
        raise HTTPException(status_code=404, detail="Politician not found")
    db.delete(politician)
    db.commit()

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..models import Politician
from ..schemas import PoliticianCreate, PoliticianDetailOut, PoliticianOut

router = APIRouter(prefix="/api/politicians", tags=["politicians"])


@router.get("/", response_model=list[PoliticianOut])
def list_politicians(db: Session = Depends(get_db)):
    return db.query(Politician).order_by(Politician.name).all()


@router.get("/{politician_id}", response_model=PoliticianDetailOut)
def get_politician(politician_id: int, db: Session = Depends(get_db)):
    politician = (
        db.query(Politician)
        .options(
            joinedload(Politician.statements).joinedload("politician"),
            joinedload(Politician.statements).joinedload("issue"),
        )
        .filter(Politician.id == politician_id)
        .first()
    )
    if not politician:
        raise HTTPException(status_code=404, detail="Politician not found")
    return politician


@router.post("/", response_model=PoliticianOut, status_code=201)
def create_politician(data: PoliticianCreate, db: Session = Depends(get_db)):
    politician = Politician(**data.model_dump())
    db.add(politician)
    db.commit()
    db.refresh(politician)
    return politician


@router.put("/{politician_id}", response_model=PoliticianOut)
def update_politician(politician_id: int, data: PoliticianCreate, db: Session = Depends(get_db)):
    politician = db.query(Politician).filter(Politician.id == politician_id).first()
    if not politician:
        raise HTTPException(status_code=404, detail="Politician not found")
    for key, value in data.model_dump().items():
        setattr(politician, key, value)
    db.commit()
    db.refresh(politician)
    return politician


@router.delete("/{politician_id}", status_code=204)
def delete_politician(politician_id: int, db: Session = Depends(get_db)):
    politician = db.query(Politician).filter(Politician.id == politician_id).first()
    if not politician:
        raise HTTPException(status_code=404, detail="Politician not found")
    db.delete(politician)
    db.commit()

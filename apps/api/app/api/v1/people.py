from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.jockey import Jockey
from app.models.trainer import Trainer
from app.schemas.person import PersonCreate, PersonResponse

router = APIRouter(tags=["People"])


@router.get("/jockeys/", response_model=list[PersonResponse])
def list_jockeys(limit: int = Query(default=100, ge=1, le=500), db: Session = Depends(get_db)):
    return list(db.scalars(select(Jockey).order_by(Jockey.name).limit(limit)))


@router.post("/jockeys/", response_model=PersonResponse, status_code=status.HTTP_201_CREATED)
def create_jockey(payload: PersonCreate, db: Session = Depends(get_db)):
    jockey = Jockey(**payload.model_dump())
    db.add(jockey)
    db.commit()
    db.refresh(jockey)
    return jockey


@router.get("/trainers/", response_model=list[PersonResponse])
def list_trainers(limit: int = Query(default=100, ge=1, le=500), db: Session = Depends(get_db)):
    return list(db.scalars(select(Trainer).order_by(Trainer.name).limit(limit)))


@router.post("/trainers/", response_model=PersonResponse, status_code=status.HTTP_201_CREATED)
def create_trainer(payload: PersonCreate, db: Session = Depends(get_db)):
    trainer = Trainer(**payload.model_dump())
    db.add(trainer)
    db.commit()
    db.refresh(trainer)
    return trainer

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.horse import Horse
from app.schemas.horse import HorseCreate


def list_horses(db: Session, skip: int = 0, limit: int = 100) -> list[Horse]:
    return list(db.scalars(select(Horse).order_by(Horse.id).offset(skip).limit(limit)))


def create_horse(db: Session, payload: HorseCreate) -> Horse:
    horse = Horse(**payload.model_dump())
    db.add(horse)
    db.commit()
    db.refresh(horse)
    return horse

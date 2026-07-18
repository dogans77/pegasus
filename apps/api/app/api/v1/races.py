from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.models.race import Race
from app.models.race_entry import RaceEntry
from app.models.track import Track
from app.schemas.race import RaceCreate, RaceEntryCreate, RaceEntryResponse, RaceResponse

router = APIRouter(prefix="/races", tags=["Races"])


@router.get("/", response_model=list[RaceResponse])
def get_races(race_date: date | None = None, db: Session = Depends(get_db)) -> list[RaceResponse]:
    statement = select(Race).options(selectinload(Race.track)).order_by(Race.race_date, Race.race_number)
    if race_date:
        statement = statement.where(Race.race_date == race_date)
    return list(db.scalars(statement))


@router.post("/", response_model=RaceResponse, status_code=status.HTTP_201_CREATED)
def create_race(payload: RaceCreate, db: Session = Depends(get_db)) -> RaceResponse:
    if not db.get(Track, payload.track_id):
        raise HTTPException(status_code=404, detail="Track not found")
    race = Race(**payload.model_dump())
    db.add(race)
    db.commit()
    return db.scalar(select(Race).options(selectinload(Race.track)).where(Race.id == race.id))


@router.get("/{race_id}/entries", response_model=list[RaceEntryResponse])
def get_race_entries(race_id: int, db: Session = Depends(get_db)) -> list[RaceEntryResponse]:
    if not db.get(Race, race_id):
        raise HTTPException(status_code=404, detail="Race not found")
    return list(db.scalars(select(RaceEntry).where(RaceEntry.race_id == race_id).order_by(RaceEntry.program_number)))


@router.post("/{race_id}/entries", response_model=RaceEntryResponse, status_code=status.HTTP_201_CREATED)
def add_race_entry(race_id: int, payload: RaceEntryCreate, db: Session = Depends(get_db)) -> RaceEntryResponse:
    if not db.get(Race, race_id):
        raise HTTPException(status_code=404, detail="Race not found")
    entry = RaceEntry(race_id=race_id, **payload.model_dump())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry

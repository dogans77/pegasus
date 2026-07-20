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
    statement = (
        select(RaceEntry)
        .options(
            selectinload(RaceEntry.horse),
            selectinload(RaceEntry.jockey),
            selectinload(RaceEntry.trainer),
        )
        .where(RaceEntry.race_id == race_id)
        .order_by(RaceEntry.program_number)
    )
    entries = list(db.scalars(statement))
    return [
        {
            "id": entry.id,
            "race_id": entry.race_id,
            "horse_id": entry.horse_id,
            "jockey_id": entry.jockey_id,
            "trainer_id": entry.trainer_id,
            "program_number": entry.program_number,
            "barrier": entry.barrier if entry.barrier and entry.barrier > 0 else None,
            "weight_kg": entry.weight_kg,
            "handicap_rating": entry.handicap_rating,
            "agf_percent": entry.agf_percent,
            "horse_name": entry.horse.name if entry.horse else None,
            "jockey_name": entry.jockey.name if entry.jockey else None,
            "trainer_name": entry.trainer.name if entry.trainer else None,
        }
        for entry in entries
    ]


@router.post("/{race_id}/entries", response_model=RaceEntryResponse, status_code=status.HTTP_201_CREATED)
def add_race_entry(race_id: int, payload: RaceEntryCreate, db: Session = Depends(get_db)) -> RaceEntryResponse:
    if not db.get(Race, race_id):
        raise HTTPException(status_code=404, detail="Race not found")
    entry = RaceEntry(race_id=race_id, **payload.model_dump())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
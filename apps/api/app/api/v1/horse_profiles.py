from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.horse import Horse
from app.models.race import Race
from app.models.race_entry import RaceEntry
from app.models.race_result import RaceResult
from app.models.track import Track

router = APIRouter(prefix="/horse-profiles", tags=["Horse Profiles"])


def _finish_position(order: list | None, program_number: int) -> int | None:
    for position, value in enumerate(order or [], start=1):
        try:
            if int(str(value)) == int(program_number):
                return position
        except (TypeError, ValueError):
            continue
    return None


@router.get("/{horse_id}")
def horse_profile(horse_id: int, limit: int = 12, db: Session = Depends(get_db)) -> dict:
    horse = db.get(Horse, horse_id)
    if horse is None:
        raise HTTPException(status_code=404, detail="Horse not found")
    statement = (
        select(RaceEntry, Race, RaceResult, Track)
        .join(Race, RaceEntry.race_id == Race.id)
        .join(Track, Race.track_id == Track.id)
        .outerjoin(RaceResult, RaceResult.race_id == Race.id)
        .where(RaceEntry.horse_id == horse_id)
        .order_by(Race.race_date.desc(), Race.race_number.desc(), Race.id.desc())
        .limit(max(1, min(limit, 30)))
    )
    history = []
    for entry, race, result, track in db.execute(statement).all():
        finish = _finish_position(result.official_order if result else None, entry.program_number)
        history.append({
            "race_id": race.id,
            "race_date": race.race_date,
            "city": track.city,
            "race_number": race.race_number,
            "surface": race.surface,
            "distance_meters": race.distance_meters,
            "program_number": entry.program_number,
            "handicap_rating": entry.handicap_rating,
            "weight_kg": float(entry.weight_kg) if entry.weight_kg is not None else None,
            "finish_position": finish,
            "won": bool(result and result.winner_entry_id == entry.id),
        })
    settled = [item for item in history if item["finish_position"] is not None]
    starts = len(settled)
    wins = sum(1 for item in settled if item["won"])
    top3 = sum(1 for item in settled if (item["finish_position"] or 999) <= 3)
    return {
        "horse": {
            "id": horse.id,
            "name": horse.name,
            "country": horse.country,
            "birth_year": horse.birth_year,
            "gender": horse.gender,
            "father": horse.father,
            "mother": horse.mother,
        },
        "summary": {
            "settled_starts": starts,
            "wins": wins,
            "top3_finishes": top3,
            "win_rate": round(wins / starts * 100, 1) if starts else None,
            "top3_rate": round(top3 / starts * 100, 1) if starts else None,
        },
        "history": history,
    }
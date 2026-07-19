from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.models.race import Race
from app.schemas.intelligence import RaceIntelligenceResponse
from app.services.race_intelligence import analyze_race

router = APIRouter(prefix="/races", tags=["Race Intelligence"])


def _response(race_id: int, db: Session) -> RaceIntelligenceResponse:
    chaos_index, entries = analyze_race(db, race_id)
    return RaceIntelligenceResponse(
        race_id=race_id,
        chaos_index=chaos_index,
        method="baseline: handicap 60%, AGF 25%, weight 15%",
        entries=[entry.__dict__ for entry in entries],
    )


@router.get("/daily-intelligence")
def get_daily_intelligence(race_date: date, db: Session = Depends(get_db)) -> list[dict]:
    races = list(
        db.scalars(
            select(Race)
            .options(selectinload(Race.track))
            .where(Race.race_date == race_date)
            .order_by(Race.race_number)
        )
    )
    summaries = []
    for race in races:
        try:
            result = _response(race.id, db)
        except ValueError:
            continue
        summaries.append(
            {
                "race_id": race.id,
                "city": race.track.city,
                "race_number": race.race_number,
                "scheduled_time": race.scheduled_time.isoformat() if race.scheduled_time else None,
                "chaos_index": result.chaos_index,
                "method": result.method,
                "top_entry": result.entries[0].model_dump(),
            }
        )
    return summaries


@router.get("/{race_id}/intelligence", response_model=RaceIntelligenceResponse)
def get_race_intelligence(race_id: int, db: Session = Depends(get_db)) -> RaceIntelligenceResponse:
    try:
        return _response(race_id, db)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
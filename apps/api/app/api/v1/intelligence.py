from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.intelligence import RaceIntelligenceResponse
from app.services.race_intelligence import analyze_race

router = APIRouter(prefix="/races", tags=["Race Intelligence"])


@router.get("/{race_id}/intelligence", response_model=RaceIntelligenceResponse)
def get_race_intelligence(race_id: int, db: Session = Depends(get_db)) -> RaceIntelligenceResponse:
    try:
        chaos_index, entries = analyze_race(db, race_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return RaceIntelligenceResponse(
        race_id=race_id,
        chaos_index=chaos_index,
        method="baseline: handicap 60%, AGF 25%, weight 15%",
        entries=entries,
    )

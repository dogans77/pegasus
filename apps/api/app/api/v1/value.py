from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.race import Race
from app.services.value_engine import analyze_value

router = APIRouter(prefix="/value", tags=["Value Engine"])


@router.get("/races/{race_id}")
def get_value_analysis(race_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        return analyze_value(db, race_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

@router.get("/daily")
def get_daily_value(race_date: date, db: Session = Depends(get_db)) -> list[dict]:
    races = list(db.scalars(select(Race).where(Race.race_date == race_date).order_by(Race.race_number)))
    output: list[dict] = []
    for race in races:
        try:
            analysis = analyze_value(db, race.id)
        except (LookupError, ValueError):
            continue
        candidates = analysis.get("value_candidates") or []
        output.append({
            "race_id": race.id,
            "chaos_index": analysis.get("chaos_index"),
            "value_candidate": candidates[0] if candidates else None,
            "false_favorite": analysis.get("false_favorite"),
            "model_version": analysis.get("model_version"),
            "disclaimer": analysis.get("disclaimer"),
        })
    return output

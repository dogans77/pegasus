from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.prediction_snapshot import PredictionSnapshot
from app.models.race import Race
from app.models.race_entry import RaceEntry
from app.models.race_result import RaceResult
from app.models.track import Track
from app.schemas.race_result import RaceResultCreate, RaceResultResponse

router = APIRouter(prefix="/results", tags=["Results and Performance"])


def serialize(result: RaceResult) -> dict:
    return {
        "id": result.id,
        "race_id": result.race_id,
        "winner_entry_id": result.winner_entry_id,
        "official_order": result.official_order,
        "official_time": result.official_time,
        "source": result.source,
        "recorded_at": result.recorded_at,
    }


@router.post("/races/{race_id}", response_model=RaceResultResponse, status_code=status.HTTP_201_CREATED)
def record_result(race_id: int, payload: RaceResultCreate, db: Session = Depends(get_db)) -> dict:
    if not db.get(Race, race_id):
        raise HTTPException(status_code=404, detail="Race not found")
    entries = list(db.scalars(select(RaceEntry).where(RaceEntry.race_id == race_id)))
    by_program = {entry.program_number: entry for entry in entries}
    unknown = [number for number in payload.official_order if number not in by_program]
    if unknown:
        raise HTTPException(status_code=422, detail={"unknown_program_numbers": unknown})
    winner = by_program[payload.official_order[0]]
    result = db.scalar(select(RaceResult).where(RaceResult.race_id == race_id))
    if result is None:
        result = RaceResult(
            race_id=race_id,
            winner_entry_id=winner.id,
            official_order=payload.official_order,
            official_time=payload.official_time,
            source=payload.source,
        )
        db.add(result)
    else:
        result.winner_entry_id = winner.id
        result.official_order = payload.official_order
        result.official_time = payload.official_time
        result.source = payload.source
    db.commit()
    db.refresh(result)
    return serialize(result)


@router.get("/races/{race_id}", response_model=RaceResultResponse)
def get_result(race_id: int, db: Session = Depends(get_db)) -> dict:
    result = db.scalar(select(RaceResult).where(RaceResult.race_id == race_id))
    if result is None:
        raise HTTPException(status_code=404, detail="Result not found")
    return serialize(result)


@router.get("/performance")
def performance(db: Session = Depends(get_db)) -> dict:
    results = list(db.scalars(select(RaceResult)))
    evaluated = 0
    top1_hits = 0
    top3_hits = 0
    details = []
    for result in results:
        snapshot = db.scalar(
            select(PredictionSnapshot)
            .where(PredictionSnapshot.race_id == result.race_id)
            .order_by(PredictionSnapshot.generated_at.desc())
        )
        if snapshot is None:
            continue
        entries = snapshot.payload.get("entries", [])
        if not entries:
            continue
        winner = result.official_order[0]
        predicted = [entry.get("program_number") for entry in entries]
        evaluated += 1
        top1 = predicted[0] == winner
        top3 = winner in predicted[:3]
        top1_hits += int(top1)
        top3_hits += int(top3)
        details.append({"race_id": result.race_id, "winner_program_number": winner, "predicted_top3": predicted[:3], "top1_hit": top1, "top3_hit": top3})
    return {
        "evaluated_races": evaluated,
        "top1_hits": top1_hits,
        "top3_hits": top3_hits,
        "top1_accuracy": round(100 * top1_hits / evaluated, 2) if evaluated else None,
        "top3_coverage": round(100 * top3_hits / evaluated, 2) if evaluated else None,
        "details": details,
    }

@router.get("/daily-performance")
def daily_performance(race_date: date | None = None, db: Session = Depends(get_db)) -> dict:
    active_date = race_date or db.scalar(select(func.max(Race.race_date)).join(RaceResult, RaceResult.race_id == Race.id))
    if active_date is None:
        return {"race_date": None, "evaluated_races": 0, "top1_hits": 0, "top3_hits": 0, "details": []}
    rows = list(
        db.execute(
            select(RaceResult, Race, Track)
            .join(Race, Race.id == RaceResult.race_id)
            .join(Track, Track.id == Race.track_id)
            .where(Race.race_date == active_date)
            .order_by(Track.name, Race.race_number)
        ).all()
    )
    details = []
    for result, race, track in rows:
        snapshot = db.scalar(
            select(PredictionSnapshot)
            .where(PredictionSnapshot.race_id == race.id)
            .order_by(PredictionSnapshot.generated_at.desc())
        )
        if snapshot is None or not result.official_order:
            continue
        entries = snapshot.payload.get("entries", [])
        predicted = [entry.get("program_number") for entry in entries]
        if not predicted:
            continue
        winner = result.official_order[0]
        details.append({
            "race_id": race.id,
            "city": track.name,
            "race_number": race.race_number,
            "winner_program_number": winner,
            "predicted_top3": predicted[:3],
            "top1_hit": predicted[0] == winner,
            "top3_hit": winner in predicted[:3],
        })
    return {
        "race_date": active_date,
        "evaluated_races": len(details),
        "top1_hits": sum(item["top1_hit"] for item in details),
        "top3_hits": sum(item["top3_hit"] for item in details),
        "details": details,
    }

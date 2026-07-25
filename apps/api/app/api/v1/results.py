from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, func, select
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


def prediction_before_result(db: Session, result: RaceResult) -> PredictionSnapshot | None:
    # A result can only be evaluated against information available before it
    # was recorded. This prevents post-result refreshes from leaking outcome
    # information into published performance metrics.
    return db.scalar(
        select(PredictionSnapshot)
        .where(
            PredictionSnapshot.race_id == result.race_id,
            PredictionSnapshot.generated_at <= result.recorded_at,
        )
        .order_by(desc(PredictionSnapshot.generated_at))
        .limit(1)
    )


def detail_for(result: RaceResult, race: Race | None, track: Track | None, snapshot: PredictionSnapshot) -> dict | None:
    if not result.official_order:
        return None
    entries = snapshot.payload.get("entries", [])
    predicted = [entry.get("program_number") for entry in entries if entry.get("program_number") is not None]
    if not predicted:
        return None
    winner = result.official_order[0]
    return {
        "race_id": result.race_id,
        "city": track.name if track else None,
        "race_number": race.race_number if race else None,
        "winner_program_number": winner,
        "predicted_top3": predicted[:3],
        "top1_hit": predicted[0] == winner,
        "top3_hit": winner in predicted[:3],
        "model_version": snapshot.model_version,
        "prediction_generated_at": snapshot.generated_at,
        "result_recorded_at": result.recorded_at,
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
        result = RaceResult(race_id=race_id, winner_entry_id=winner.id, official_order=payload.official_order, official_time=payload.official_time, source=payload.source)
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


def performance_rows(db: Session, race_date: date | None = None) -> tuple[list[dict], int]:
    statement = select(RaceResult, Race, Track).join(Race, Race.id == RaceResult.race_id).join(Track, Track.id == Race.track_id)
    if race_date is not None:
        statement = statement.where(Race.race_date == race_date)
    rows = list(db.execute(statement.order_by(Race.race_date, Track.name, Race.race_number)).all())
    details, excluded = [], 0
    for result, race, track in rows:
        if result.source == "tjk_needs_reconciliation":
            excluded += 1
            continue
        snapshot = prediction_before_result(db, result)
        if snapshot is None:
            excluded += 1
            continue
        detail = detail_for(result, race, track, snapshot)
        if detail is None:
            excluded += 1
            continue
        details.append(detail)
    return details, excluded


def aggregate(race_date: date | None, details: list[dict], excluded: int) -> dict:
    evaluated = len(details)
    top1_hits = sum(item["top1_hit"] for item in details)
    top3_hits = sum(item["top3_hit"] for item in details)
    return {
        "race_date": race_date,
        "evaluated_races": evaluated,
        "eligible_results": evaluated,
        "excluded_results": excluded,
        "top1_hits": top1_hits,
        "top3_hits": top3_hits,
        "top1_accuracy": round(100 * top1_hits / evaluated, 2) if evaluated else None,
        "top3_coverage": round(100 * top3_hits / evaluated, 2) if evaluated else None,
        "details": details,
        "evaluation_policy": "Only prediction snapshots generated no later than the official result record are evaluated.",
    }


@router.get("/performance")
def performance(db: Session = Depends(get_db)) -> dict:
    details, excluded = performance_rows(db)
    return aggregate(None, details, excluded)


@router.get("/daily-performance")
def daily_performance(race_date: date | None = None, db: Session = Depends(get_db)) -> dict:
    active_date = race_date or db.scalar(select(func.max(Race.race_date)).join(RaceResult, RaceResult.race_id == Race.id))
    if active_date is None:
        return aggregate(None, [], 0)
    details, excluded = performance_rows(db, active_date)
    return aggregate(active_date, details, excluded)
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.prediction_snapshot import PredictionSnapshot
from app.models.race import Race
from app.models.race_entry import RaceEntry
from app.models.race_result import RaceResult

router = APIRouter(prefix="/analytics", tags=["Data Quality Lab"])


@router.get("/model-readiness")
def model_readiness(db: Session = Depends(get_db)) -> dict:
    race_count = db.scalar(select(func.count(Race.id))) or 0
    entry_count = db.scalar(select(func.count(RaceEntry.id))) or 0
    result_count = db.scalar(select(func.count(RaceResult.id))) or 0
    snapshot_count = db.scalar(select(func.count(PredictionSnapshot.id))) or 0
    dated = db.execute(select(func.min(Race.race_date), func.max(Race.race_date))).one()
    races_with_entries = db.scalar(
        select(func.count()).select_from(
            select(RaceEntry.race_id).group_by(RaceEntry.race_id).having(func.count(RaceEntry.id) >= 2).subquery()
        )
    ) or 0
    result_coverage = round(100 * result_count / race_count, 2) if race_count else 0.0
    training_ready = result_count >= 100 and snapshot_count >= 100
    return {
        "race_count": race_count,
        "entry_count": entry_count,
        "result_count": result_count,
        "prediction_snapshot_count": snapshot_count,
        "races_with_two_or_more_entries": races_with_entries,
        "result_coverage_percent": result_coverage,
        "date_range": {"from": dated[0], "to": dated[1]},
        "baseline_ready": races_with_entries > 0,
        "ml_training_ready": training_ready,
        "next_threshold": {
            "minimum_result_races": 100,
            "minimum_prediction_snapshots": 100,
        },
        "note": "Baseline ranking is available now. ML training starts after sufficient historical result coverage.",
    }
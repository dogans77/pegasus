from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.prediction_snapshot import PredictionSnapshot
from app.models.race import Race
from app.models.source_document import SourceDocument


def _stamp(value) -> float:
    if value is None:
        return 0.0
    try:
        return value.timestamp()
    except (AttributeError, OSError, OverflowError):
        return 0.0


def report(db: Session, race_date: date | None = None) -> dict:
    active_date = race_date or datetime.now().date()
    source_at = db.scalar(
        select(func.max(SourceDocument.fetched_at)).where(
            SourceDocument.race_date == active_date,
            SourceDocument.document_type == "daily_program_html",
        )
    )
    races = list(
        db.scalars(
            select(Race).where(Race.race_date == active_date).order_by(Race.scheduled_time, Race.id)
        )
    )
    details = []
    stale_count = 0
    missing_count = 0
    for race in races:
        snapshot_at = db.scalar(
            select(func.max(PredictionSnapshot.generated_at)).where(PredictionSnapshot.race_id == race.id)
        )
        if snapshot_at is None:
            state = "missing"
            missing_count += 1
        elif source_at is not None and _stamp(snapshot_at) < _stamp(source_at):
            state = "stale"
            stale_count += 1
        else:
            state = "fresh"
        details.append({
            "race_id": race.id,
            "race_number": race.race_number,
            "snapshot_at": snapshot_at,
            "state": state,
        })
    ready = bool(races) and source_at is not None and stale_count == 0 and missing_count == 0
    return {
        "race_date": active_date,
        "state": "fresh" if ready else "review",
        "can_display_model_probabilities": ready,
        "source_received_at": source_at,
        "race_count": len(races),
        "fresh_races": sum(1 for item in details if item["state"] == "fresh"),
        "stale_races": stale_count,
        "missing_snapshots": missing_count,
        "races": details,
        "note": "Model probabilities are displayed only when each race has a snapshot at least as recent as the official daily program source.",
    }
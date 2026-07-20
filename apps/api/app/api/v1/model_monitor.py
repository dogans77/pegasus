from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.prediction_snapshot import PredictionSnapshot
from app.models.race import Race
from app.models.race_result import RaceResult
from app.models.track import Track

router = APIRouter(prefix="/analytics", tags=["Model Monitoring"])


def _period(rows: list[tuple[RaceResult, Race]], db: Session) -> dict:
    evaluated = 0
    top1_hits = 0
    top3_hits = 0
    versions: dict[str, int] = {}
    for result, race in rows:
        snapshot = db.scalar(
            select(PredictionSnapshot)
            .where(PredictionSnapshot.race_id == result.race_id)
            .order_by(PredictionSnapshot.generated_at.desc())
        )
        if snapshot is None:
            continue
        entries = snapshot.payload.get("entries", [])
        order = result.official_order or []
        if not entries or not order:
            continue
        winner = order[0]
        predicted = [entry.get("program_number") for entry in entries]
        evaluated += 1
        top1_hits += int(predicted[0] == winner)
        top3_hits += int(winner in predicted[:3])
        version = snapshot.model_version or "unknown"
        versions[version] = versions.get(version, 0) + 1
    return {
        "evaluated_races": evaluated,
        "top1_accuracy": round(100 * top1_hits / evaluated, 2) if evaluated else None,
        "top3_coverage": round(100 * top3_hits / evaluated, 2) if evaluated else None,
        "model_versions": versions,
    }


@router.get("/model-monitor")
def model_monitor(window: int = 60, db: Session = Depends(get_db)) -> dict:
    window = max(20, min(window, 240))
    rows = list(
        db.execute(
            select(RaceResult, Race)
            .join(Race, Race.id == RaceResult.race_id)
            .order_by(Race.race_date.desc(), Race.id.desc())
            .limit(window)
        ).all()
    )
    split = max(1, len(rows) // 2)
    recent = _period(rows[:split], db)
    previous = _period(rows[split:], db)
    recent_top1 = recent["top1_accuracy"]
    previous_top1 = previous["top1_accuracy"]
    delta = None if recent_top1 is None or previous_top1 is None else round(recent_top1 - previous_top1, 2)
    state = "watch"
    if delta is not None and delta >= 3:
        state = "improving"
    elif delta is not None and delta <= -3:
        state = "review"
    return {
        "window": window,
        "recent": recent,
        "previous": previous,
        "top1_change_points": delta,
        "state": state,
        "note": "Performance is descriptive. It is not a return or profitability guarantee.",
    }

def _slice(name: str, rows: list[tuple[RaceResult, Race]], db: Session) -> dict:
    metrics = _period(rows, db)
    return {
        "name": name,
        "evaluated_races": metrics["evaluated_races"],
        "top1_accuracy": metrics["top1_accuracy"],
        "top3_coverage": metrics["top3_coverage"],
    }


@router.get("/model-monitor/slices")
def model_monitor_slices(window: int = 240, db: Session = Depends(get_db)) -> dict:
    window = max(60, min(window, 500))
    rows = list(
        db.execute(
            select(RaceResult, Race, Track)
            .join(Race, Race.id == RaceResult.race_id)
            .join(Track, Track.id == Race.track_id)
            .order_by(Race.race_date.desc(), Race.id.desc())
            .limit(window)
        ).all()
    )
    by_city: dict[str, list[tuple[RaceResult, Race]]] = {}
    by_surface: dict[str, list[tuple[RaceResult, Race]]] = {}
    for result, race, track in rows:
        pair = (result, race)
        by_city.setdefault(track.name, []).append(pair)
        by_surface.setdefault(race.surface or "Unknown", []).append(pair)
    city_slices = [_slice(name, values, db) for name, values in by_city.items()]
    surface_slices = [_slice(name, values, db) for name, values in by_surface.items()]
    sort_key = lambda item: (item["evaluated_races"], item["top1_accuracy"] or -1)
    return {
        "window": window,
        "by_city": sorted(city_slices, key=sort_key, reverse=True),
        "by_surface": sorted(surface_slices, key=sort_key, reverse=True),
        "note": "Slices with a small sample are directional only, not a betting signal.",
    }

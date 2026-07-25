from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.prediction_snapshot import PredictionSnapshot
from app.models.race import Race
from app.models.race_result import RaceResult


def _probability(value) -> float:
    number = float(value or 0)
    return number / 100.0 if number > 1 else number


def report(db: Session, limit: int = 300) -> dict:
    """Audit only predictions recorded before their official result was stored."""
    rows = db.execute(
        select(PredictionSnapshot, RaceResult, Race)
        .join(RaceResult, RaceResult.race_id == PredictionSnapshot.race_id)
        .join(Race, Race.id == PredictionSnapshot.race_id)
        .where(PredictionSnapshot.generated_at <= RaceResult.recorded_at)
        .order_by(Race.race_date.desc(), PredictionSnapshot.generated_at.desc())
    ).all()
    selected = {}
    for snapshot, result, race in rows:
        if snapshot.race_id not in selected:
            selected[snapshot.race_id] = (snapshot, result, race)
        if len(selected) >= limit:
            break
    audited = list(selected.values())
    bins = defaultdict(lambda: {"count": 0, "wins": 0, "probability_total": 0.0})
    top1 = top3 = usable = 0
    skipped = 0
    for snapshot, result, race in audited:
        payload = snapshot.payload or {}
        entries = [item for item in (payload.get("entries") or []) if isinstance(item, dict) and item.get("entry_id") is not None]
        if not entries or result.winner_entry_id is None:
            skipped += 1
            continue
        ranked = sorted(entries, key=lambda item: _probability(item.get("win_probability")), reverse=True)
        winner_id = int(result.winner_entry_id)
        usable += 1
        top1 += int(int(ranked[0]["entry_id"]) == winner_id)
        top3 += int(any(int(item["entry_id"]) == winner_id for item in ranked[:3]))
        for item in ranked:
            probability = _probability(item.get("win_probability"))
            label = f"{int(probability * 100 // 10) * 10}-{min(int(probability * 100 // 10) * 10 + 9, 100)}%"
            bucket = bins[label]
            bucket["count"] += 1
            bucket["wins"] += int(int(item["entry_id"]) == winner_id)
            bucket["probability_total"] += probability
    calibration = []
    for label, bucket in sorted(bins.items(), key=lambda pair: int(pair[0].split("-")[0])):
        count = bucket["count"]
        calibration.append({
            "band": label,
            "entries": count,
            "average_probability": round(bucket["probability_total"] / count, 4) if count else 0.0,
            "actual_win_rate": round(bucket["wins"] / count, 4) if count else 0.0,
        })
    return {
        "audited_races": usable,
        "skipped_races": skipped,
        "top1_accuracy": round(top1 / usable, 4) if usable else None,
        "top3_coverage": round(top3 / usable, 4) if usable else None,
        "calibration_bands": calibration,
        "eligibility": "informational" if usable >= 50 else "insufficient_pre_result_snapshots",
        "note": "Only snapshots generated before the official result was recorded are included. This is retrospective quality control, not a wagering signal.",
    }
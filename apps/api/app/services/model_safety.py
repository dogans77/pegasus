from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.race_result import RaceResult

from app.services import model_research


MIN_SETTLED_RACES = 500
# PEGASUS_MODEL_SAFETY_CACHE
_CACHE: dict | None = None
_CACHE_UNTIL = None
MAX_CALIBRATION_GAP_POINTS = 12.0


def _calibration_gap(rows: list[dict]) -> float | None:
    eligible = [
        abs(float(row["mean_predicted_probability"]) - float(row["actual_win_rate"]))
        for row in rows
        if int(row.get("entries", 0)) >= 20
    ]
    return round(max(eligible), 2) if eligible else None


def report(db: Session, refresh: bool = False) -> dict:
    global _CACHE, _CACHE_UNTIL
    now = datetime.now(timezone.utc)
    if not refresh and _CACHE is not None and _CACHE_UNTIL is not None and now < _CACHE_UNTIL:
        return _CACHE
    try:
        research = model_research.temporal_research(db)
    except ValueError as exc:
        return {
            "state": "blocked",
            "can_publish_actionable_scenarios": False,
            "reason": str(exc),
            "minimum_settled_races": MIN_SETTLED_RACES,
        }

    settled = int(research.get("settled_races", 0))
    model_top1 = research.get("average_model_top1_accuracy")
    handicap_top1 = research.get("average_handicap_top1_accuracy")
    gap = _calibration_gap(research.get("latest_fold_calibration", []))
    reasons: list[str] = []
    if settled < MIN_SETTLED_RACES:
        reasons.append("Insufficient settled-race sample")
    if not research.get("model_beats_handicap_on_average", False):
        reasons.append("Model did not outperform the handicap baseline")
    if gap is None:
        reasons.append("Calibration sample is insufficient")
    elif gap > MAX_CALIBRATION_GAP_POINTS:
        reasons.append("Probability calibration gap exceeds the guardrail")

    unreconciled_official_results = db.scalar(
        select(func.count(RaceResult.id)).where(RaceResult.source == "tjk_needs_reconciliation")
    ) or 0
    if unreconciled_official_results:
        reasons.append("Official result reconciliation is incomplete")
    state = "experimental" if not reasons else "review"
    payload = {
        "state": state,
        "can_publish_actionable_scenarios": False,
        "settled_races": settled,
        "unreconciled_official_results": unreconciled_official_results,
        "minimum_settled_races": MIN_SETTLED_RACES,
        "average_model_top1_accuracy": model_top1,
        "average_handicap_top1_accuracy": handicap_top1,
        "latest_calibration_gap_points": gap,
        "max_calibration_gap_points": MAX_CALIBRATION_GAP_POINTS,
        "reasons": reasons,
        "model_version": research.get("model_version"),
        "note": "The gate is intentionally conservative. It never asserts profitability or a guaranteed outcome.",
    }
    _CACHE = payload
    _CACHE_UNTIL = now + timedelta(minutes=10)
    return payload
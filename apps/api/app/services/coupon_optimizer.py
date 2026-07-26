from __future__ import annotations

from math import prod

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.race import Race
from app.models.track import Track
from app.services import baseline_ml, model_safety
from app.api.v1.recommendations import recommendation_for_race
from app.services.value_engine import analyze_value


def _probability_fraction(value: object) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return number / 100.0 if number > 1.0 else number


def _selection_count(ordered: list[dict], chaos_index: float, risk: str) -> int:
    """Choose coverage from the field shape, not a fixed number per leg."""
    probabilities = [_probability_fraction(item.get("win_probability")) for item in ordered]
    if not probabilities:
        return 1
    top = probabilities[0]
    second = probabilities[1] if len(probabilities) > 1 else 0.0
    margin = top - second
    # A clear leader in a calm race can be narrow.  Flat probability curves
    # or high chaos require wider coverage.  This remains only a draft while
    # the publication safety gate is closed.
    if chaos_index < 35 and margin >= 0.10:
        count = 1
    elif chaos_index < 52 and margin >= 0.055:
        count = 2
    elif chaos_index < 70:
        count = 3
    elif chaos_index < 84:
        count = 4
    else:
        count = 5
    if risk == "conservative":
        count += 1
    elif risk == "aggressive":
        count -= 1
    return max(1, min(len(ordered), 6, count))


def _confidence_label(chaos_index: float, count: int) -> str:
    if chaos_index < 35 and count == 1:
        return "high"
    if chaos_index < 70:
        return "medium"
    return "low"


def _leg(db: Session, race: Race, risk: str) -> dict:
    recommendation = recommendation_for_race(db, race.id)
    value = analyze_value(db, race.id)
    ordered = recommendation.get("ranked_entries") or [recommendation["primary"], *recommendation["alternatives"]]
    desired = _selection_count(ordered, float(recommendation["chaos_index"]), risk)
    by_program = {item["program_number"]: item for item in ordered}
    for item in value["value_candidates"]:
        by_program.setdefault(item["program_number"], {
            "program_number": item["program_number"],
            "horse_name": item["horse_name"],
            "win_probability": item["model_probability"],
        })
    selections = list(by_program.values())[:desired]
    return {
        "race_id": race.id,
        "race_number": race.race_number,
        "scheduled_time": race.scheduled_time.isoformat() if race.scheduled_time else None,
        "city": race.track.city,
        "chaos_index": recommendation["chaos_index"],
        "confidence": _confidence_label(recommendation["chaos_index"], len(selections)),
        "selection_count": len(selections),
        "selection_basis": "field_shape_and_chaos",
        "selections": selections,
        "value_candidate": value["value_candidates"][0] if value["value_candidates"] else None,
        "false_favorite": value["false_favorite"],
    }


def plan_sequence(db: Session, race_id: int, risk: str = "balanced", max_columns: int = 240, leg_count: int = 6) -> dict:
    start = db.get(Race, race_id)
    if start is None:
        raise LookupError("Race not found.")
    safety = model_safety.report(db)
    if not safety.get("can_publish_actionable_scenarios", False):
        raise ValueError("Coverage plans are unavailable while model and official-result integrity checks remain under review.")
    safety = model_safety.report(db)
    if not safety.get("can_publish_actionable_scenarios", False):
        raise ValueError("Coverage plans are unavailable while model and official-result integrity checks remain under review.")
    if risk not in {"conservative", "balanced", "aggressive"}:
        raise ValueError("risk must be conservative, balanced, or aggressive.")
    races = list(db.scalars(
        select(Race).join(Track).options(selectinload(Race.track))
        .where(Race.race_date == start.race_date, Track.city == start.track.city, Race.race_number >= start.race_number)
        .order_by(Race.race_number).limit(max(1, min(leg_count, 8)))
    ))
    if len(races) < 1:
        raise ValueError("No races are available for this sequence.")
    legs = [_leg(db, race, risk) for race in races]
    while prod(max(1, leg["selection_count"]) for leg in legs) > max_columns:
        candidates = [leg for leg in legs if leg["selection_count"] > 1]
        if not candidates:
            break
        # Narrow the least uncertain leg first to preserve wider coverage in chaotic races.
        target = min(candidates, key=lambda leg: leg["chaos_index"])
        target["selection_count"] -= 1
        target["selections"] = target["selections"][:target["selection_count"]]
    columns = prod(max(1, leg["selection_count"]) for leg in legs)
    return {
        "start_race_id": race_id,
        "risk": risk,
        "max_columns": max_columns,
        "estimated_columns": columns,
        "legs": legs,
        "method": "Coverage plan uses model ranking, chaos, and AGF-versus-model value signals.",
        "disclaimer": "This is an analytical coverage plan, not betting advice or a guarantee of outcome.",
    }


def model_health() -> dict:
    status = baseline_ml.status()
    if not status.get("trained"):
        return {"trained": False, "status": "awaiting_training"}
    deployment = status.get("deployment", {})
    metrics = status.get("metrics", {})
    benchmarks = status.get("benchmarks", {})
    return {
        "trained": True,
        "candidate_model": status.get("model_version"),
        "deployed_model": deployment.get("selected_model", status.get("model_version")),
        "policy": deployment.get("policy"),
        "candidate_top1_accuracy": metrics.get("top1_accuracy"),
        "candidate_top3_coverage": metrics.get("top3_coverage"),
        "handicap_benchmark_top1_accuracy": benchmarks.get("handicap_leader", {}).get("top1_accuracy"),
        "decision": deployment.get("reason"),
    }
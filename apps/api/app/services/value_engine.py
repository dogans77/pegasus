from __future__ import annotations

import math

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.race import Race
from app.models.race_entry import RaceEntry
from app.services import baseline_ml


def _chaos_from_probabilities(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    normalized = [max(value, 0.000001) / 100 for value in values]
    entropy = -sum(value * math.log(value) for value in normalized)
    maximum = math.log(len(normalized))
    return round(100 * entropy / maximum if maximum else 0.0, 2)


def analyze_value(db: Session, race_id: int) -> dict:
    race = db.get(Race, race_id)
    if race is None:
        raise LookupError("Race not found.")
    entries = list(db.scalars(select(RaceEntry).options(joinedload(RaceEntry.horse)).where(RaceEntry.race_id == race_id).order_by(RaceEntry.program_number)))
    if len(entries) < 2:
        raise ValueError("At least two entries are required for value analysis.")
    prediction = baseline_ml.predict_race(db, race_id)
    predicted = {item["entry_id"]: float(item["win_probability"]) for item in prediction["entries"]}
    agf_total = sum(float(entry.agf_percent or 0) for entry in entries)
    rows = []
    for entry in entries:
        market_probability = round(float(entry.agf_percent or 0) / agf_total * 100, 2) if agf_total else round(100 / len(entries), 2)
        model_probability = round(predicted.get(entry.id, 0.0), 2)
        gap = round(model_probability - market_probability, 2)
        rows.append({
            "entry_id": entry.id,
            "program_number": entry.program_number,
            "horse_name": entry.horse.name,
            "model_probability": model_probability,
            "agf_market_probability": market_probability,
            "edge_percentage_points": gap,
            "value_score": round(max(0, min(100, 50 + gap * 3)), 1),
        })
    rows.sort(key=lambda item: item["edge_percentage_points"], reverse=True)
    probabilities = [item["model_probability"] for item in rows]
    false_favorite = min(rows, key=lambda item: item["edge_percentage_points"])
    return {
        "race_id": race_id,
        "model_version": prediction["model_version"],
        "candidate_model": prediction.get("candidate_model"),
        "chaos_index": _chaos_from_probabilities(probabilities),
        "market_signal": "AGF normalized share; this is a crowd signal, not fixed odds.",
        "deployment": prediction.get("deployment"),
        "value_candidates": [item for item in rows if item["edge_percentage_points"] > 0][:3],
        "false_favorite": false_favorite,
        "entries": rows,
        "disclaimer": "Value is a model-versus-market signal, not a promise of return.",
    }
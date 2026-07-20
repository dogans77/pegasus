from dataclasses import replace
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.models.race import Race
from app.services import baseline_ml
from app.services.race_intelligence import RankedEntry, analyze_race

router = APIRouter(prefix="/recommendations", tags=["Explainable Recommendations"])
_PEGASUS_RECOMMENDATION_CACHE: dict[int, dict] = {}


def confidence_level(chaos_index: float, top_probability: float) -> str:
    if chaos_index < 40 and top_probability >= 30:
        return "high"
    if chaos_index < 70:
        return "medium"
    return "low"


def explanation(top: RankedEntry, entries: list[RankedEntry], chaos_index: float) -> list[str]:
    reasons: list[str] = []
    ratings = [item.handicap_rating or 0 for item in entries]
    market = [item.agf_percent or 0 for item in entries]
    weights = [item.weight_kg for item in entries if item.weight_kg is not None]
    if top.handicap_rating and top.handicap_rating == max(ratings):
        reasons.append("\u00dcst handikap puan\u0131")
    if top.agf_percent and top.agf_percent == max(market):
        reasons.append("Piyasa deste\u011fi")
    if top.weight_kg is not None and weights and top.weight_kg == min(weights):
        reasons.append("Kilo avantaj\u0131")
    if not reasons:
        reasons.append("G\u00fc\u00e7 skorunda lider")
    if chaos_index >= 70:
        reasons.append("Y\u00fcksek s\u00fcrpriz riski")
    return reasons


def recommendation_for_race(db: Session, race_id: int) -> dict:
    cached = _PEGASUS_RECOMMENDATION_CACHE.get(race_id)
    if cached is not None:
        return cached
    chaos_index, entries = analyze_race(db, race_id)
    model_version = "baseline-rules-v1"
    try:
        model_prediction = baseline_ml.predict_race(db, race_id)
        model_probabilities = {item["entry_id"]: item["win_probability"] for item in model_prediction["entries"]}
        entries = sorted(
            [replace(item, win_probability=model_probabilities.get(item.entry_id, item.win_probability)) for item in entries],
            key=lambda item: item.win_probability,
            reverse=True,
        )
        model_version = model_prediction["model_version"]
    except LookupError:
        pass
    top = entries[0]
    result = {
        "race_id": race_id,
        "model_version": model_version,
        "confidence": confidence_level(chaos_index, top.win_probability),
        "chaos_index": chaos_index,
        "primary": top.__dict__,
        "alternatives": [item.__dict__ for item in entries[1:4]],
        "reasons": explanation(top, entries, chaos_index),
        "disclaimer": "Olasilik tabanli karar destegidir; kesin sonuc iddiasi tasimaz.",
    }
    _PEGASUS_RECOMMENDATION_CACHE[race_id] = result
    return result


@router.get("/races/{race_id}")
def get_recommendation(race_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        return recommendation_for_race(db, race_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/warm/daily")
def warm_daily_recommendations(race_date: date, db: Session = Depends(get_db)) -> dict:
    races = list(db.scalars(select(Race).where(Race.race_date == race_date).order_by(Race.race_number)))
    warmed, skipped = [], []
    for race in races:
        try:
            recommendation_for_race(db, race.id)
            warmed.append(race.id)
        except (LookupError, ValueError):
            skipped.append(race.id)
    return {"race_date": race_date, "warmed_race_ids": warmed, "skipped_race_ids": skipped, "cache_size": len(_PEGASUS_RECOMMENDATION_CACHE)}


@router.post("/cache/clear")
def clear_recommendation_cache() -> dict:
    _PEGASUS_RECOMMENDATION_CACHE.clear()
    return {"cleared": True}

@router.get("/daily")
def get_daily_recommendations(race_date: date, db: Session = Depends(get_db)) -> list[dict]:
    races = list(db.scalars(select(Race).options(selectinload(Race.track)).where(Race.race_date == race_date).order_by(Race.race_number)))
    output = []
    for race in races:
        try:
            item = dict(recommendation_for_race(db, race.id))
        except ValueError:
            continue
        item["city"] = race.track.city
        item["race_number"] = race.race_number
        item["scheduled_time"] = race.scheduled_time.isoformat() if race.scheduled_time else None
        output.append(item)
    return output

@router.get("/shortlist")
def get_shortlist(
    race_date: date,
    max_chaos: float = 65,
    limit: int = 12,
    db: Session = Depends(get_db),
) -> dict:
    limit = max(1, min(limit, 40))
    races = list(
        db.scalars(
            select(Race)
            .options(selectinload(Race.track))
            .where(Race.race_date == race_date)
            .order_by(Race.scheduled_time, Race.id)
        )
    )
    candidates = []
    for race in races:
        try:
            recommendation = recommendation_for_race(db, race.id)
        except (LookupError, ValueError):
            continue
        probability = float(recommendation["primary"].get("win_probability") or 0)
        chaos = float(recommendation.get("chaos_index") or 100)
        if chaos > max_chaos:
            continue
        candidates.append({
            "race_id": race.id,
            "city": race.track.name,
            "race_number": race.race_number,
            "scheduled_time": race.scheduled_time.isoformat() if race.scheduled_time else None,
            "chaos_index": chaos,
            "confidence": recommendation.get("confidence"),
            "primary": recommendation["primary"],
            "reasons": recommendation.get("reasons", []),
        })
    candidates.sort(key=lambda item: (-float(item["primary"].get("win_probability") or 0), item["chaos_index"]))
    return {
        "race_date": race_date,
        "max_chaos": max_chaos,
        "items": candidates[:limit],
        "disclaimer": "Shortlist is probability-based decision support, not a guarantee or betting instruction.",
    }

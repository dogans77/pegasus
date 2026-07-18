import math
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.race import Race
from app.models.race_entry import RaceEntry


@dataclass(frozen=True)
class RankedEntry:
    entry_id: int
    horse_id: int
    horse_name: str
    program_number: int
    handicap_rating: int | None
    agf_percent: float | None
    weight_kg: float | None
    score: float
    win_probability: float


def analyze_race(db: Session, race_id: int) -> tuple[float, list[RankedEntry]]:
    race = db.get(Race, race_id)
    if race is None:
        raise LookupError("Race not found")
    entries = list(db.scalars(
        select(RaceEntry)
        .options(joinedload(RaceEntry.horse))
        .where(RaceEntry.race_id == race_id)
        .order_by(RaceEntry.program_number)
    ))
    if len(entries) < 2:
        raise ValueError("At least two race entries are required for intelligence scoring")

    ratings = [entry.handicap_rating or 0 for entry in entries]
    agfs = [float(entry.agf_percent or 0) for entry in entries]
    weights = [float(entry.weight_kg or 60) for entry in entries]
    max_rating = max(max(ratings), 1)
    min_weight, max_weight = min(weights), max(weights)
    weight_range = max(max_weight - min_weight, 1)

    raw_scores = []
    for entry, rating, agf, weight in zip(entries, ratings, agfs, weights):
        hp_score = 60 * rating / max_rating
        market_score = 25 * min(agf, 100) / 100
        weight_score = 15 * (max_weight - weight) / weight_range
        raw_scores.append(hp_score + market_score + weight_score)

    exp_scores = [math.exp(score / 12) for score in raw_scores]
    total = sum(exp_scores)
    ranked = sorted(
        [RankedEntry(
            entry_id=entry.id,
            horse_id=entry.horse_id,
            horse_name=entry.horse.name,
            program_number=entry.program_number,
            handicap_rating=entry.handicap_rating,
            agf_percent=float(entry.agf_percent) if entry.agf_percent is not None else None,
            weight_kg=float(entry.weight_kg) if entry.weight_kg is not None else None,
            score=round(score, 2),
            win_probability=round(100 * value / total, 2),
        ) for entry, score, value in zip(entries, raw_scores, exp_scores)],
        key=lambda item: item.win_probability,
        reverse=True,
    )
    gap = ranked[0].win_probability - ranked[1].win_probability
    chaos_index = round(max(0, min(100, 85 - gap * 2 + min(len(entries), 15))), 2)
    return chaos_index, ranked

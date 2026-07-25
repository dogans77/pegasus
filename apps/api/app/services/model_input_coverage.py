from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.race import Race


INPUTS = (
    "handicap_rating",
    "weight_kg",
    "agf_percent",
    "barrier",
    "jockey_id",
    "trainer_id",
)


def _present(value) -> bool:
    return value is not None and value != ""


def report(db: Session, race_date: date | None = None) -> dict:
    active_date = race_date or datetime.now().date()
    races = list(
        db.scalars(
            select(Race)
            .options(selectinload(Race.entries), selectinload(Race.track))
            .where(Race.race_date == active_date)
            .order_by(Race.scheduled_time, Race.id)
        )
    )
    cards = []
    all_values = 0
    present_values = 0
    for race in races:
        missing = {name: 0 for name in INPUTS}
        for entry in race.entries:
            for name in INPUTS:
                all_values += 1
                if _present(getattr(entry, name, None)):
                    present_values += 1
                else:
                    missing[name] += 1
        expected = len(race.entries) * len(INPUTS)
        filled = expected - sum(missing.values())
        coverage = round(100 * filled / expected, 1) if expected else 0.0
        cards.append({
            "race_id": race.id,
            "city": race.track.city if race.track else None,
            "race_number": race.race_number,
            "entry_count": len(race.entries),
            "coverage_percent": coverage,
            "missing": {name: count for name, count in missing.items() if count},
            "state": "ready" if coverage >= 80 else "review" if coverage >= 55 else "limited",
        })
    overall = round(100 * present_values / all_values, 1) if all_values else 0.0
    return {
        "race_date": active_date,
        "race_count": len(cards),
        "coverage_percent": overall,
        "ready_races": sum(item["state"] == "ready" for item in cards),
        "review_races": sum(item["state"] == "review" for item in cards),
        "limited_races": sum(item["state"] == "limited" for item in cards),
        "races": cards,
        "note": "Coverage measures the availability of inputs used by the current model. Missing inputs are imputed by the model and should reduce confidence, not be interpreted as positive signals.",
    }
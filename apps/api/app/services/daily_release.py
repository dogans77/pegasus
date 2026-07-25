from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.race import Race
from app.models.source_document import SourceDocument
from app.api.v1.recommendations import recommendation_for_race


def _probability(value) -> float:
    return float(value or 0) / 100.0


def report(db: Session, race_date: date | None = None) -> dict:
    active_date = race_date or datetime.now().date()
    races = list(db.scalars(select(Race).options(selectinload(Race.entries), selectinload(Race.track)).where(Race.race_date == active_date).order_by(Race.scheduled_time, Race.id)))
    source_count = db.scalar(select(func.count(SourceDocument.id)).where(SourceDocument.race_date == active_date, SourceDocument.document_type == "daily_program_html")) or 0
    checks, blockers = [], []
    if not races:
        blockers.append("No imported races for the requested date")
    if not source_count:
        blockers.append("No archived official daily-program source")
    for race in races:
        expected = len(race.entries)
        item = {"race_id": race.id, "city": race.track.city if race.track else None, "race_number": race.race_number, "entry_count": expected, "status": "ready", "issues": []}
        if expected < 2:
            item["issues"].append("Race has fewer than two entries")
        try:
            recommendation = recommendation_for_race(db, race.id)
            ranked = recommendation.get("ranked_entries") or []
            ids = [candidate.get("entry_id") for candidate in ranked]
            probabilities = [_probability(candidate.get("win_probability")) for candidate in ranked]
            if len(ranked) != expected:
                item["issues"].append("Ranked field does not cover every entry")
            if len(set(ids)) != len(ids) or any(value is None for value in ids):
                item["issues"].append("Ranked field contains invalid or duplicate entry identifiers")
            if probabilities != sorted(probabilities, reverse=True):
                item["issues"].append("Ranked probabilities are not descending")
            if any(value < 0 for value in probabilities):
                item["issues"].append("Ranked field contains a negative probability")
            if probabilities and abs(sum(probabilities) - 1.0) > 0.03:
                item["issues"].append("Ranked probability total is outside tolerance")
        except (LookupError, ValueError) as exc:
            item["issues"].append(str(exc))
        if item["issues"]:
            item["status"] = "hold"
            blockers.extend([f"Race {race.id}: {issue}" for issue in item["issues"]])
        checks.append(item)
    return {
        "race_date": active_date,
        "state": "ready" if not blockers else "hold",
        "can_publish_daily_board": not blockers,
        "source_count": source_count,
        "race_count": len(races),
        "ready_races": sum(1 for item in checks if item["status"] == "ready"),
        "blocked_races": sum(1 for item in checks if item["status"] != "ready"),
        "blockers": blockers,
        "races": checks,
        "note": "Daily readiness checks source coverage, complete entry coverage, descending rank order, and normalized probability totals. It does not make wagering claims.",
    }
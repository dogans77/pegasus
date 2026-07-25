import argparse
import json
import time
from datetime import datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.database import SessionLocal
from app.models.race import Race
from app.models.race_entry import RaceEntry
from app.models.race_result import RaceResult
from app.models.track import Track
from app.services.tjk_results import TjkResultsClient

RESULT_CITIES = [
    ("Istanbul", chr(0x0130) + "stanbul", 1), ("Izmir", chr(0x0130) + "zmir", 2),
    ("Bursa", "Bursa", 3), ("Adana", "Adana", 4), ("Ankara", "Ankara", 5),
    ("Kocaeli", "Kocaeli", 6), ("Diyarbakir", "Diyarbak" + chr(0x0131) + "r", 10),
    ("Elazig", "Elaz" + chr(0x0131) + chr(0x011f), 11),
]


def suspicious(order):
    values = [int(value) for value in (order or []) if str(value).isdigit()]
    return len(values) >= 4 and values == list(range(1, len(values) + 1))


def load_checkpoint(path):
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"completed_dates": []}
    except Exception:
        return {"completed_dates": []}


def save_checkpoint(path, state):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=True, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-dates", type=int, default=0)
    parser.add_argument("--checkpoint", default="deploy/reports/tjk-result-reconciliation-checkpoint.json")
    args = parser.parse_args()
    checkpoint_path = Path(args.checkpoint)
    state = load_checkpoint(checkpoint_path)
    completed = set(state.get("completed_dates", []))
    db = SessionLocal()
    summary = {"marked_suspect": 0, "reconciled_races": 0, "unmatched_races": 0, "dates_completed": 0}
    try:
        for result in db.scalars(select(RaceResult).where(RaceResult.source.in_(["tjk", "tjk_needs_reconciliation"]))).all():
            if suspicious(result.official_order):
                result.source = "tjk_needs_reconciliation"
                summary["marked_suspect"] += 1
        db.commit()
        dates = list(db.scalars(
            select(Race.race_date).join(RaceResult, RaceResult.race_id == Race.id)
            .where(RaceResult.source == "tjk_needs_reconciliation").distinct().order_by(Race.race_date)
        ).all())
        dates = [value for value in dates if value.isoformat() not in completed]
        if args.max_dates > 0:
            dates = dates[:args.max_dates]
        client = TjkResultsClient()
        for race_date in dates:
            day = {"reconciled_races": 0, "unmatched_races": 0, "pages": 0}
            for stored_city, request_city, city_id in RESULT_CITIES:
                try:
                    _, _, parsed_races = client.fetch_and_parse(city=request_city, city_id=city_id, race_date=race_date)
                except Exception:
                    continue
                day["pages"] += 1
                for parsed in parsed_races:
                    race = db.scalar(select(Race).join(Race.track).where(
                        Race.race_date == race_date, Race.race_number == parsed.race_number, Track.name == stored_city
                    ))
                    if race is None:
                        continue
                    result = db.scalar(select(RaceResult).where(RaceResult.race_id == race.id))
                    if result is None or result.source != "tjk_needs_reconciliation":
                        continue
                    entries = list(db.scalars(select(RaceEntry).options(selectinload(RaceEntry.horse)).where(RaceEntry.race_id == race.id)))
                    by_program = {entry.program_number: entry for entry in entries}
                    order = [number for number in parsed.finisher_program_numbers if number in by_program]
                    if len(order) < 2:
                        day["unmatched_races"] += 1
                        continue
                    result.winner_entry_id = by_program[order[0]].id
                    result.official_order = order
                    result.official_time = parsed.official_time
                    result.source = "tjk_reconciled"
                    day["reconciled_races"] += 1
            db.commit()
            completed.add(race_date.isoformat())
            state["completed_dates"] = sorted(completed)
            state["last_completed_at"] = datetime.utcnow().isoformat() + "Z"
            save_checkpoint(checkpoint_path, state)
            for key, value in day.items():
                summary[key] = summary.get(key, 0) + value
            summary["dates_completed"] += 1
            print(json.dumps({"date": race_date.isoformat(), **day, "remaining_dates": len(dates) - summary["dates_completed"]}, ensure_ascii=True))
            time.sleep(0.25)
        summary["remaining_suspect_results"] = int(db.scalar(select(func.count()).select_from(RaceResult).where(RaceResult.source == "tjk_needs_reconciliation")) or 0)
        print(json.dumps({"completed": summary, "checkpoint": str(checkpoint_path)}, ensure_ascii=True))
    finally:
        db.close()


if __name__ == "__main__":
    main()
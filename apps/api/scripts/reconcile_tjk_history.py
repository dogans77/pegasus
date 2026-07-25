import argparse
import json
import re
import time
from collections import defaultdict
from datetime import datetime
from difflib import SequenceMatcher
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
    ("Istanbul", "Istanbul", 1), ("Izmir", "Izmir", 2), ("Bursa", "Bursa", 3),
    ("Adana", "Adana", 4), ("Ankara", "Ankara", 5), ("Kocaeli", "Kocaeli", 6),
    ("Diyarbakir", "Diyarbakir", 10), ("Elazig", "Elazig", 11),
]


def key(value):
    table = str.maketrans({"I": "I", "i": "I", "S": "S", "s": "S", "G": "G", "g": "G", "U": "U", "u": "U", "O": "O", "o": "O", "C": "C", "c": "C"})
    return re.sub(r"[^A-Z0-9]", "", (value or "").upper().translate(table))


def suspicious(order):
    values = [int(value) for value in (order or []) if str(value).isdigit()]
    return len(values) >= 4 and values == list(range(1, len(values) + 1))


def best_entry(finisher, entries):
    wanted = key(finisher)
    exact = [entry for entry in entries if entry.horse and key(entry.horse.name) == wanted]
    if len(exact) == 1:
        return exact[0]
    scored = []
    for entry in entries:
        if not entry.horse:
            continue
        score = SequenceMatcher(None, wanted, key(entry.horse.name)).ratio()
        scored.append((score, entry))
    scored.sort(key=lambda item: item[0], reverse=True)
    if len(scored) == 1 and scored[0][0] >= 0.91:
        return scored[0][1]
    if len(scored) >= 2 and scored[0][0] >= 0.91 and scored[0][0] - scored[1][0] >= 0.04:
        return scored[0][1]
    return None


def checkpoint_load(path):
    if not path.exists():
        return {"completed_dates": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"completed_dates": []}


def checkpoint_save(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-dates", type=int, default=0)
    parser.add_argument("--checkpoint", default="deploy/reports/tjk-result-reconciliation-checkpoint.json")
    args = parser.parse_args()
    checkpoint_path = Path(args.checkpoint)
    state = checkpoint_load(checkpoint_path)
    completed = set(state.get("completed_dates", []))
    db = SessionLocal()
    summary = defaultdict(int)
    try:
        suspect_results = list(db.scalars(select(RaceResult).where(RaceResult.source.in_(["tjk", "tjk_needs_reconciliation"]))).all())
        for result in suspect_results:
            if suspicious(result.official_order):
                result.source = "tjk_needs_reconciliation"
                summary["marked_suspect"] += 1
        db.commit()

        dates = list(db.scalars(
            select(Race.race_date)
            .join(RaceResult, RaceResult.race_id == Race.id)
            .where(RaceResult.source == "tjk_needs_reconciliation")
            .distinct()
            .order_by(Race.race_date)
        ).all())
        dates = [item for item in dates if item.isoformat() not in completed]
        if args.max_dates > 0:
            dates = dates[:args.max_dates]

        client = TjkResultsClient()
        for race_date in dates:
            date_key = race_date.isoformat()
            day = defaultdict(int)
            for stored_city, request_city, city_id in RESULT_CITIES:
                try:
                    _, _, parsed_races = client.fetch_and_parse(city=request_city, city_id=city_id, race_date=race_date)
                except Exception:
                    day["unavailable_city_pages"] += 1
                    continue
                for parsed in parsed_races:
                    race = db.scalar(
                        select(Race)
                        .join(Race.track)
                        .where(Race.race_date == race_date, Race.race_number == parsed.race_number, Track.name == stored_city)
                    )
                    if race is None:
                        continue
                    result = db.scalar(select(RaceResult).where(RaceResult.race_id == race.id))
                    if result is None or result.source != "tjk_needs_reconciliation":
                        continue
                    entries = list(db.scalars(
                        select(RaceEntry)
                        .options(selectinload(RaceEntry.horse))
                        .where(RaceEntry.race_id == race.id)
                    ))
                    order = []
                    for finisher in parsed.finisher_names:
                        entry = best_entry(finisher, entries)
                        if entry is not None and entry.program_number not in order:
                            order.append(entry.program_number)
                    if len(order) < 2:
                        day["unmatched_races"] += 1
                        continue
                    winner = next((entry for entry in entries if entry.program_number == order[0]), None)
                    if winner is None:
                        day["unmatched_races"] += 1
                        continue
                    result.winner_entry_id = winner.id
                    result.official_order = order
                    result.official_time = parsed.official_time
                    result.source = "tjk_reconciled"
                    day["reconciled_races"] += 1
            db.commit()
            completed.add(date_key)
            state["completed_dates"] = sorted(completed)
            state["last_completed_at"] = datetime.utcnow().isoformat() + "Z"
            checkpoint_save(checkpoint_path, state)
            summary.update(day)
            summary["dates_completed"] += 1
            print(json.dumps({"date": date_key, **dict(day), "remaining_dates": len(dates) - summary["dates_completed"]}, ensure_ascii=True))
            time.sleep(0.35)
        summary["remaining_suspect_results"] = int(db.scalar(select(func.count()).select_from(RaceResult).where(RaceResult.source == "tjk_needs_reconciliation")) or 0)
        print(json.dumps({"completed": dict(summary), "checkpoint": str(checkpoint_path)}, ensure_ascii=True))
    finally:
        db.close()


if __name__ == "__main__":
    main()
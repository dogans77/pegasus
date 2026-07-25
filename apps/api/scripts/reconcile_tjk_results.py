import argparse
import re
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import SessionLocal
from app.models.race import Race
from app.models.race_entry import RaceEntry
from app.models.race_result import RaceResult
from app.models.track import Track
from app.services.tjk_results import TjkResultsClient

RESULT_CITIES = [
    ("Istanbul", "\u0130stanbul", 1), ("Izmir", "\u0130zmir", 2), ("Bursa", "Bursa", 3),
    ("Adana", "Adana", 4), ("Ankara", "Ankara", 5), ("Kocaeli", "Kocaeli", 6),
    ("Diyarbakir", "Diyarbak\u0131r", 10), ("Elazig", "Elaz\u0131\u011f", 11),
]


def key(value: str | None) -> str:
    text = (value or "").upper().translate(str.maketrans({"\u0130": "I", "\u0131": "I", "\u015e": "S", "\u011e": "G", "\u00dc": "U", "\u00d6": "O", "\u00c7": "C"}))
    return re.sub(r"[^A-Z0-9]", "", text)


def suspicious(order) -> bool:
    values = [int(value) for value in (order or []) if str(value).isdigit()]
    return len(values) >= 4 and values == list(range(1, len(values) + 1))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    args = parser.parse_args()
    race_date = datetime.strptime(args.date, "%Y-%m-%d").date()
    db = SessionLocal()
    marked = corrected = skipped = fetched = 0
    try:
        for result in db.scalars(select(RaceResult).where(RaceResult.source == "tjk")).all():
            if suspicious(result.official_order):
                result.source = "tjk_needs_reconciliation"
                marked += 1
        db.commit()
        client = TjkResultsClient()
        for stored_city, request_city, city_id in RESULT_CITIES:
            try:
                _, _, parsed_races = client.fetch_and_parse(city=request_city, city_id=city_id, race_date=race_date)
            except Exception:
                continue
            fetched += 1
            for parsed in parsed_races:
                race = db.scalar(select(Race).join(Race.track).where(Race.race_date == race_date, Race.race_number == parsed.race_number, Track.name == stored_city))
                if race is None:
                    skipped += 1
                    continue
                entries = list(db.scalars(select(RaceEntry).options(selectinload(RaceEntry.horse)).where(RaceEntry.race_id == race.id)))
                by_horse = {key(entry.horse.name): entry for entry in entries if entry.horse is not None}
                order = []
                for finisher in parsed.finisher_names:
                    entry = by_horse.get(key(finisher))
                    if entry is not None and entry.program_number not in order:
                        order.append(entry.program_number)
                if len(order) < 2:
                    skipped += 1
                    continue
                result = db.scalar(select(RaceResult).where(RaceResult.race_id == race.id))
                if result is None:
                    result = RaceResult(race_id=race.id, winner_entry_id=by_horse[key(parsed.finisher_names[0])].id, official_order=order, official_time=parsed.official_time, source="tjk")
                    db.add(result)
                else:
                    result.winner_entry_id = next(entry.id for entry in entries if entry.program_number == order[0])
                    result.official_order = order
                    result.official_time = parsed.official_time
                    result.source = "tjk"
                corrected += 1
        db.commit()
        print({"suspect_marked": marked, "pages_fetched": fetched, "current_day_corrected": corrected, "skipped": skipped})
    finally:
        db.close()


if __name__ == "__main__":
    main()
from datetime import date, datetime, timezone
import hashlib

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.crawler_run import CrawlerRun
from app.models.race import Race
from app.models.source_document import SourceDocument
from app.models.track import Track
from app.services.tjk_daily_program import TjkDailyProgramClient, TjkFetchError, TjkParseError

router = APIRouter(prefix="/crawler/tjk", tags=["TJK Discovery"])

# City IDs used by the official TJK daily-program route. The importer checks
# each candidate and uses only a page that contains a valid race card.
CANDIDATE_CITIES = [
    ("Istanbul", "\u0130stanbul"),
    ("Izmir", "\u0130zmir"),
    ("Bursa", "Bursa"),
    ("Adana", "Adana"),
    ("Ankara", "Ankara"),
    ("Kocaeli", "Kocaeli"),
    ("Diyarbakir", "Diyarbak\u0131r"),
    ("Elazig", "Elaz\u0131\u011f"),
]


class AvailableProgram(BaseModel):
    city: str
    city_id: int
    race_count: int


class AutoImportResponse(BaseModel):
    crawler_run_id: int
    city: str
    source_url: str
    races_created: int
    races_updated: int


def discover(race_date: date):
    client = TjkDailyProgramClient()
    found = []
    try:
        city_pages = client.discover_city_pages(race_date)
    except (TjkFetchError, TjkParseError):
        return found
    for city, request_city, city_id in city_pages:
        try:
            source_url, raw_html, races = client.fetch_and_parse(
                city=request_city,
                city_id=city_id,
                race_date=race_date,
            )
            found.append((city, city_id, source_url, raw_html, races))
        except (TjkFetchError, TjkParseError):
            continue
    return found


@router.get("/available-programs", response_model=list[AvailableProgram])
def available_programs(race_date: date = Query(...)):
    return [AvailableProgram(city=city, city_id=city_id, race_count=len(races)) for city, city_id, _, _, races in discover(race_date)]


@router.post("/import-first-available", response_model=AutoImportResponse, status_code=status.HTTP_201_CREATED)
def import_first_available(race_date: date, db: Session = Depends(get_db)):
    run = CrawlerRun(source="tjk", job_name="discover_and_import_daily_program", status="running")
    db.add(run); db.commit(); db.refresh(run)
    programs = discover(race_date)
    if not programs:
        run.status = "failed"
        run.error_message = "No valid TJK daily program was found for the requested date."
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
        raise HTTPException(status_code=404, detail=run.error_message)

    city, _, source_url, raw_html, races = programs[0]
    document = db.scalar(select(SourceDocument).where(SourceDocument.source_url == source_url))
    checksum = hashlib.sha256(raw_html.encode("utf-8")).hexdigest()
    if document is None:
        db.add(SourceDocument(provider="tjk", document_type="daily_program_html", source_url=source_url, checksum=checksum, race_date=race_date, city=city, content=raw_html))
    else:
        document.checksum = checksum
        document.content = raw_html

    track = db.scalar(select(Track).where(Track.name == city))
    if track is None:
        track = Track(name=city, city=city)
        db.add(track); db.flush()

    created = updated = 0
    for item in races:
        race = db.scalar(select(Race).where(Race.track_id == track.id, Race.race_date == race_date, Race.race_number == item.race_number))
        if race is None:
            db.add(Race(track_id=track.id, race_date=race_date, **item.__dict__))
            created += 1
        else:
            race.scheduled_time = item.scheduled_time
            race.distance_meters = item.distance_meters
            race.surface = item.surface
            race.race_class = item.race_class
            updated += 1

    run.status = "completed"
    run.records_processed = created + updated
    run.finished_at = datetime.now(timezone.utc)
    db.commit()
    return AutoImportResponse(crawler_run_id=run.id, city=city, source_url=source_url, races_created=created, races_updated=updated)

from app.models.horse import Horse
from app.models.jockey import Jockey
from app.models.trainer import Trainer
from app.models.race_entry import RaceEntry
from app.services.tjk_entries import entry_candidates


def _entry_candidates_for_date(race_date: date, db: Session) -> list[dict]:
    documents = list(
        db.scalars(
            select(SourceDocument).where(
                SourceDocument.race_date == race_date,
                SourceDocument.document_type == "daily_program_html",
            )
        )
    )
    candidates = []
    for document in documents:
        candidates.extend({"city": document.city, **candidate} for candidate in entry_candidates(document.content))
    return candidates


@router.get("/entry-preview")
def entry_preview(race_date: date, limit: int = Query(default=100, ge=1, le=1000), db: Session = Depends(get_db)):
    return _entry_candidates_for_date(race_date, db)[:limit]


@router.post("/import-entries")
def import_entries(race_date: date, db: Session = Depends(get_db)):
    candidates = _entry_candidates_for_date(race_date, db)
    if not candidates:
        raise HTTPException(status_code=422, detail="No entry candidates found in archived TJK documents.")

    created = updated = skipped = 0
    for item in candidates:
        race = db.scalar(
            select(Race)
            .join(Race.track)
            .where(
                Race.race_date == race_date,
                Race.race_number == item["race_number"],
                Track.name == item["city"],
            )
        )
        if race is None:
            skipped += 1
            continue

        horse = db.scalar(select(Horse).where(Horse.name == item["horse_name"]))
        if horse is None:
            horse = Horse(name=item["horse_name"])
            db.add(horse)
            db.flush()

        jockey = None
        if item["jockey_name"]:
            jockey = db.scalar(select(Jockey).where(Jockey.name == item["jockey_name"]))
            if jockey is None:
                jockey = Jockey(name=item["jockey_name"])
                db.add(jockey)
                db.flush()

        trainer = None
        if item["trainer_name"]:
            trainer = db.scalar(select(Trainer).where(Trainer.name == item["trainer_name"]))
            if trainer is None:
                trainer = Trainer(name=item["trainer_name"])
                db.add(trainer)
                db.flush()

        entry = db.scalar(
            select(RaceEntry).where(
                RaceEntry.race_id == race.id,
                RaceEntry.program_number == item["program_number"],
            )
        )
        values = {
            "horse_id": horse.id,
            "jockey_id": jockey.id if jockey else None,
            "trainer_id": trainer.id if trainer else None,
            "barrier": item["barrier"],
            "weight_kg": item["weight_kg"],
            "handicap_rating": item["handicap_rating"],
            "agf_percent": item["agf_percent"],
        }
        if entry is None:
            db.add(RaceEntry(race_id=race.id, program_number=item["program_number"], **values))
            created += 1
        else:
            for field, value in values.items():
                setattr(entry, field, value)
            updated += 1

    db.commit()
    return {
        "candidates_found": len(candidates),
        "entries_created": created,
        "entries_updated": updated,
        "entries_skipped": skipped,
    }

@router.get("/entry-diagnostics")
def entry_diagnostics(race_date: date, db: Session = Depends(get_db)):
    from bs4 import BeautifulSoup
    documents = list(db.scalars(select(SourceDocument).where(SourceDocument.race_date == race_date, SourceDocument.document_type == "daily_program_html")))
    output = []
    for document in documents:
        soup = BeautifulSoup(document.content, "html.parser")
        rows = soup.find_all("tr")
        output.append({
            "city": document.city,
            "html_length": len(document.content),
            "table_count": len(soup.find_all("table")),
            "row_count": len(rows),
            "text_preview": soup.get_text(" ", strip=True)[:5000],
            "first_rows": [row.get_text(" | ", strip=True)[:1000] for row in rows[:12]],
        })
    return output

# PEGASUS_TJK_RESULTS_IMPORTER
from app.models.race_entry import RaceEntry
from app.models.race_result import RaceResult
from app.services.tjk_results import TjkResultsClient

RESULT_CITIES = [
    ("Istanbul", "\u0130stanbul", 1),
    ("Izmir", "\u0130zmir", 2),
    ("Bursa", "Bursa", 3),
    ("Adana", "Adana", 4),
    ("Ankara", "Ankara", 5),
    ("Kocaeli", "Kocaeli", 6),
    ("Diyarbakir", "Diyarbak\u0131r", 10),
    ("Elazig", "Elaz\u0131\u011f", 11),
]
def _result_candidates(race_date: date):
    client = TjkResultsClient()
    output = []
    for stored_city, request_city, city_id in RESULT_CITIES:
        try:
            source_url, raw_html, races = client.fetch_and_parse(
                city=request_city,
                city_id=city_id,
                race_date=race_date,
            )
            output.append((stored_city, source_url, raw_html, races))
        except TjkFetchError:
            continue
    return output


@router.get("/results-preview")
def results_preview(race_date: date):
    return [
        {
            "city": city,
            "source_url": source_url,
            "races": [item.__dict__ for item in races],
        }
        for city, source_url, _, races in _result_candidates(race_date)
    ]


@router.post("/import-results")
def import_results(race_date: date, db: Session = Depends(get_db)):
    found = _result_candidates(race_date)
    if not found:
        raise HTTPException(status_code=404, detail="No TJK result pages could be fetched for this date.")

    created = updated = skipped = 0
    for city, source_url, raw_html, result_races in found:
        checksum = hashlib.sha256(raw_html.encode("utf-8")).hexdigest()
        document = db.scalar(select(SourceDocument).where(SourceDocument.source_url == source_url))
        if document is None:
            db.add(SourceDocument(
                provider="tjk",
                document_type="daily_results_html",
                source_url=source_url,
                checksum=checksum,
                race_date=race_date,
                city=city,
                content=raw_html,
            ))
        else:
            document.checksum = checksum
            document.content = raw_html

        for parsed in result_races:
            race = db.scalar(
                select(Race)
                .join(Race.track)
                .where(Race.race_date == race_date, Race.race_number == parsed.race_number, Track.name == city)
            )
            if race is None:
                skipped += 1
                continue
            entries = list(db.scalars(select(RaceEntry).where(RaceEntry.race_id == race.id)))
            by_program = {entry.program_number: entry for entry in entries}
            known_order = [number for number in parsed.official_order if number in by_program]
            if not known_order:
                skipped += 1
                continue
            result = db.scalar(select(RaceResult).where(RaceResult.race_id == race.id))
            if result is None:
                db.add(RaceResult(
                    race_id=race.id,
                    winner_entry_id=by_program[known_order[0]].id,
                    official_order=known_order,
                    official_time=parsed.official_time,
                    source="tjk",
                ))
                created += 1
            else:
                result.winner_entry_id = by_program[known_order[0]].id
                result.official_order = known_order
                result.official_time = parsed.official_time
                result.source = "tjk"
                updated += 1
    db.commit()
    return {"pages_found": len(found), "results_created": created, "results_updated": updated, "results_skipped": skipped}

# PEGASUS_TJK_IMPORT_ALL_PROGRAMS
@router.post("/import-all-available")
def import_all_available(race_date: date, db: Session = Depends(get_db)):
    run = CrawlerRun(source="tjk", job_name="import_all_daily_programs", status="running")
    db.add(run)
    db.commit()
    db.refresh(run)
    programs = discover(race_date)
    if not programs:
        run.status = "failed"
        run.error_message = "No valid TJK daily program was found for the requested date."
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
        raise HTTPException(status_code=404, detail=run.error_message)

    created = updated = 0
    cities = []
    for city, _, source_url, raw_html, races in programs:
        checksum = hashlib.sha256(raw_html.encode("utf-8")).hexdigest()
        document = db.scalar(select(SourceDocument).where(SourceDocument.source_url == source_url))
        if document is None:
            db.add(SourceDocument(
                provider="tjk",
                document_type="daily_program_html",
                source_url=source_url,
                checksum=checksum,
                race_date=race_date,
                city=city,
                content=raw_html,
            ))
        else:
            document.checksum = checksum
            document.content = raw_html

        track = db.scalar(select(Track).where(Track.name == city))
        if track is None:
            track = Track(name=city, city=city)
            db.add(track)
            db.flush()
        cities.append(city)
        for item in races:
            race = db.scalar(
                select(Race).where(
                    Race.track_id == track.id,
                    Race.race_date == race_date,
                    Race.race_number == item.race_number,
                )
            )
            if race is None:
                db.add(Race(track_id=track.id, race_date=race_date, **item.__dict__))
                created += 1
            else:
                race.scheduled_time = item.scheduled_time
                race.distance_meters = item.distance_meters
                race.surface = item.surface
                race.race_class = item.race_class
                updated += 1

    # Keep the daily board faithful to the official program. If an old
    # ID-based import attached a card to the wrong city, remove only that
    # stale card after the canonical city-name import succeeds.
    active_cities = set(cities)
    stale_races = list(
        db.scalars(
            select(Race)
            .join(Track)
            .where(Race.race_date == race_date, ~Track.name.in_(active_cities))
        )
    )
    for stale_race in stale_races:
        db.delete(stale_race)
    run.status = "completed"
    run.records_processed = created + updated
    run.finished_at = datetime.now(timezone.utc)
    db.commit()
    return {
        "race_date": race_date,
        "cities": cities,
        "races_created": created,
        "races_updated": updated,
    }
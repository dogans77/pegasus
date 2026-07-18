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
    ("Istanbul", 1),
    ("Izmir", 2),
    ("Bursa", 3),
    ("Adana", 4),
    ("Ankara", 5),
    ("Kocaeli", 6),
    ("Diyarbakir", 10),
    ("Elazig", 11),
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
    for city, city_id in CANDIDATE_CITIES:
        try:
            source_url, raw_html, races = client.fetch_and_parse(city=city, city_id=city_id, race_date=race_date)
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

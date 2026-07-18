from datetime import datetime, timezone
import hashlib

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.crawler_run import CrawlerRun
from app.models.race import Race
from app.models.source_document import SourceDocument
from app.models.track import Track
from app.schemas.tjk import (
    TjkDailyProgramPreviewResponse,
    TjkDailyProgramRequest,
    TjkDailyProgramResponse,
    TjkProgramRacePreview,
)
from app.services.tjk_daily_program import TjkDailyProgramClient, TjkFetchError, TjkParseError

router = APIRouter(prefix="/crawler/tjk", tags=["TJK Crawler"])


def get_program(payload: TjkDailyProgramRequest):
    client = TjkDailyProgramClient()
    try:
        return client.fetch_and_parse(city=payload.city, city_id=payload.city_id, race_date=payload.race_date)
    except (TjkFetchError, TjkParseError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/daily-program/preview", response_model=TjkDailyProgramPreviewResponse)
def preview_daily_program(payload: TjkDailyProgramRequest) -> TjkDailyProgramPreviewResponse:
    source_url, _, parsed_races = get_program(payload)
    return TjkDailyProgramPreviewResponse(
        source_url=source_url,
        race_count=len(parsed_races),
        races=[TjkProgramRacePreview(
            race_number=item.race_number,
            scheduled_time=item.scheduled_time.isoformat() if item.scheduled_time else None,
            distance_meters=item.distance_meters,
            surface=item.surface,
            race_class=item.race_class,
        ) for item in parsed_races],
    )


@router.post("/daily-program", response_model=TjkDailyProgramResponse, status_code=status.HTTP_201_CREATED)
def import_daily_program(payload: TjkDailyProgramRequest, db: Session = Depends(get_db)) -> TjkDailyProgramResponse:
    run = CrawlerRun(source="tjk", job_name="daily_program", status="running")
    db.add(run); db.commit(); db.refresh(run)
    try:
        source_url, raw_html, parsed_races = get_program(payload)
        document = db.scalar(select(SourceDocument).where(SourceDocument.source_url == source_url))
        checksum = hashlib.sha256(raw_html.encode("utf-8")).hexdigest()
        if document is None:
            db.add(SourceDocument(provider="tjk", document_type="daily_program_html", source_url=source_url, checksum=checksum, race_date=payload.race_date, city=payload.city, content=raw_html))
        else:
            document.checksum, document.content = checksum, raw_html
        track = db.scalar(select(Track).where(Track.name == payload.city))
        if track is None:
            track = Track(name=payload.city, city=payload.city)
            db.add(track); db.flush()
        created = updated = 0
        for item in parsed_races:
            race = db.scalar(select(Race).where(Race.track_id == track.id, Race.race_date == payload.race_date, Race.race_number == item.race_number))
            if race is None:
                db.add(Race(track_id=track.id, race_date=payload.race_date, **item.__dict__))
                created += 1
            else:
                race.scheduled_time = item.scheduled_time
                race.distance_meters = item.distance_meters
                race.surface = item.surface
                race.race_class = item.race_class
                updated += 1
        run.status = "completed"; run.records_processed = created + updated; run.finished_at = datetime.now(timezone.utc)
        db.commit()
        return TjkDailyProgramResponse(crawler_run_id=run.id, source_url=source_url, races_created=created, races_updated=updated)
    except HTTPException as exc:
        run.status = "failed"; run.error_message = str(exc.detail); run.finished_at = datetime.now(timezone.utc)
        db.commit()
        raise exc

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.crawler_run import CrawlerRun
from app.models.race import Race
from app.models.track import Track
from app.schemas.tjk import TjkDailyProgramRequest, TjkDailyProgramResponse
from app.services.tjk_daily_program import TjkDailyProgramClient, TjkFetchError

router = APIRouter(prefix="/crawler/tjk", tags=["TJK Crawler"])


@router.post("/daily-program", response_model=TjkDailyProgramResponse, status_code=status.HTTP_201_CREATED)
def import_daily_program(payload: TjkDailyProgramRequest, db: Session = Depends(get_db)) -> TjkDailyProgramResponse:
    run = CrawlerRun(source="tjk", job_name="daily_program", status="running")
    db.add(run)
    db.commit()
    db.refresh(run)

    client = TjkDailyProgramClient()
    try:
        source_url, parsed_races = client.fetch_and_parse(
            city=payload.city,
            city_id=payload.city_id,
            race_date=payload.race_date,
        )
        track = db.scalar(select(Track).where(Track.name == payload.city))
        if track is None:
            track = Track(name=payload.city, city=payload.city)
            db.add(track)
            db.flush()

        created = 0
        updated = 0
        for item in parsed_races:
            race = db.scalar(
                select(Race).where(
                    Race.track_id == track.id,
                    Race.race_date == payload.race_date,
                    Race.race_number == item.race_number,
                )
            )
            if race is None:
                db.add(Race(track_id=track.id, race_date=payload.race_date, **item.__dict__))
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
        return TjkDailyProgramResponse(
            crawler_run_id=run.id,
            source_url=source_url,
            races_created=created,
            races_updated=updated,
        )
    except TjkFetchError as exc:
        run.status = "failed"
        run.error_message = str(exc)
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
        raise HTTPException(status_code=502, detail=str(exc)) from exc

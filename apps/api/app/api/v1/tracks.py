from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.track import Track
from app.schemas.track import TrackCreate, TrackResponse

router = APIRouter(prefix="/tracks", tags=["Tracks"])


@router.get("/", response_model=list[TrackResponse])
def list_tracks(limit: int = Query(default=100, ge=1, le=500), db: Session = Depends(get_db)) -> list[TrackResponse]:
    return list(db.scalars(select(Track).order_by(Track.city, Track.name).limit(limit)))


@router.post("/", response_model=TrackResponse, status_code=status.HTTP_201_CREATED)
def create_track(payload: TrackCreate, db: Session = Depends(get_db)) -> TrackResponse:
    track = Track(**payload.model_dump())
    db.add(track)
    db.commit()
    db.refresh(track)
    return track

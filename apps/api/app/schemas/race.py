from datetime import date, time
from decimal import Decimal
from pydantic import Field
from app.schemas.common import ORMModel
from app.schemas.track import TrackResponse


class RaceCreate(ORMModel):
    track_id: int
    race_date: date
    race_number: int = Field(ge=1, le=99)
    scheduled_time: time | None = None
    distance_meters: int = Field(ge=400, le=10000)
    surface: str = Field(min_length=2, max_length=32)
    race_class: str | None = Field(default=None, max_length=64)
    status: str = Field(default="scheduled", max_length=24)


class RaceResponse(RaceCreate):
    id: int
    track: TrackResponse


class RaceEntryCreate(ORMModel):
    horse_id: int
    jockey_id: int | None = None
    trainer_id: int | None = None
    program_number: int = Field(ge=1, le=99)
    barrier: int | None = Field(default=None, ge=1, le=99)
    weight_kg: Decimal | None = Field(default=None, ge=30, le=100)
    handicap_rating: int | None = Field(default=None, ge=0, le=200)
    agf_percent: Decimal | None = Field(default=None, ge=0, le=100)


class RaceEntryResponse(RaceEntryCreate):
    id: int
    race_id: int

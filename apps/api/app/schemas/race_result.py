from datetime import datetime
from pydantic import BaseModel, Field


class RaceResultCreate(BaseModel):
    official_order: list[int] = Field(min_length=1, max_length=99)
    official_time: str | None = Field(default=None, max_length=32)
    source: str = Field(default="manual", max_length=32)


class RaceResultResponse(BaseModel):
    id: int
    race_id: int
    winner_entry_id: int
    official_order: list[int]
    official_time: str | None
    source: str
    recorded_at: datetime | None
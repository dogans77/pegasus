from pydantic import Field
from app.schemas.common import ORMModel


class TrackCreate(ORMModel):
    name: str = Field(min_length=2, max_length=120)
    city: str = Field(min_length=2, max_length=80)
    country: str = Field(default="TR", min_length=2, max_length=2)


class TrackResponse(TrackCreate):
    id: int

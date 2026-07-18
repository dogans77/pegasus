from datetime import date

from pydantic import BaseModel, Field


class TjkDailyProgramRequest(BaseModel):
    city: str = Field(min_length=2, max_length=80, examples=["Ankara"])
    city_id: int = Field(ge=1, examples=[5])
    race_date: date


class TjkProgramRacePreview(BaseModel):
    race_number: int
    scheduled_time: str | None
    distance_meters: int
    surface: str
    race_class: str | None


class TjkDailyProgramPreviewResponse(BaseModel):
    source_url: str
    race_count: int
    races: list[TjkProgramRacePreview]


class TjkDailyProgramResponse(BaseModel):
    crawler_run_id: int
    source_url: str
    races_created: int
    races_updated: int

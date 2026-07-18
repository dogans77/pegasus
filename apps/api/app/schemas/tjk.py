from datetime import date

from pydantic import BaseModel, Field


class TjkDailyProgramRequest(BaseModel):
    city: str = Field(min_length=2, max_length=80, examples=["Ankara"])
    city_id: int = Field(ge=1, examples=[5])
    race_date: date


class TjkDailyProgramResponse(BaseModel):
    crawler_run_id: int
    source_url: str
    races_created: int
    races_updated: int

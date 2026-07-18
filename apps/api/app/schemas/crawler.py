from datetime import datetime
from pydantic import Field
from app.schemas.common import ORMModel


class CrawlerRunCreate(ORMModel):
    source: str = Field(default="tjk", max_length=64)
    job_name: str = Field(default="daily_program", max_length=120)


class CrawlerRunResponse(CrawlerRunCreate):
    id: int
    status: str
    records_processed: int
    error_message: str | None
    started_at: datetime
    finished_at: datetime | None

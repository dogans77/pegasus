from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field

class TjkCsvPreviewRequest(BaseModel):
    city: str = Field(min_length=2, max_length=80)
    race_date: date

class TjkCsvPreviewResponse(BaseModel):
    source_document_id: int
    source_url: str
    headers: list[str]
    row_count: int
    sample_rows: list[dict[str, str]]
    raw_preview: str

class SourceDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    provider: str
    document_type: str
    source_url: str
    checksum: str
    race_date: date
    city: str
    fetched_at: datetime

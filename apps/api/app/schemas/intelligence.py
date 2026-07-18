from pydantic import BaseModel


class RaceRankedEntryResponse(BaseModel):
    entry_id: int
    horse_id: int
    horse_name: str
    program_number: int
    handicap_rating: int | None
    agf_percent: float | None
    weight_kg: float | None
    score: float
    win_probability: float


class RaceIntelligenceResponse(BaseModel):
    race_id: int
    chaos_index: float
    method: str
    entries: list[RaceRankedEntryResponse]

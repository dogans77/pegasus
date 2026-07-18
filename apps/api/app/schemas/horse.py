from pydantic import BaseModel, ConfigDict, Field


class HorseCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    country: str | None = Field(default=None, max_length=50)
    birth_year: int | None = Field(default=None, ge=1900, le=2100)
    gender: str | None = Field(default=None, max_length=20)
    father: str | None = Field(default=None, max_length=150)
    mother: str | None = Field(default=None, max_length=150)
    is_active: bool = True


class HorseResponse(HorseCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int

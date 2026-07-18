from pydantic import Field
from app.schemas.common import ORMModel


class PersonCreate(ORMModel):
    name: str = Field(min_length=2, max_length=120)
    country: str = Field(default="TR", min_length=2, max_length=2)


class PersonResponse(PersonCreate):
    id: int

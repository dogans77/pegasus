from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories.horse_repository import create_horse, list_horses
from app.schemas.horse import HorseCreate, HorseResponse

router = APIRouter(prefix="/horses", tags=["Horses"])


@router.get("/", response_model=list[HorseResponse])
def get_horses(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[HorseResponse]:
    return list_horses(db, skip=skip, limit=limit)


@router.post("/", response_model=HorseResponse, status_code=status.HTTP_201_CREATED)
def add_horse(payload: HorseCreate, db: Session = Depends(get_db)) -> HorseResponse:
    return create_horse(db, payload)

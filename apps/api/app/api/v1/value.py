from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.value_engine import analyze_value

router = APIRouter(prefix="/value", tags=["Value Engine"])


@router.get("/races/{race_id}")
def get_value_analysis(race_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        return analyze_value(db, race_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
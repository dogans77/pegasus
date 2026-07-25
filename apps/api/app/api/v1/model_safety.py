from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services import model_safety

router = APIRouter(prefix="/analytics", tags=["Model Safety"])


@router.get("/model-safety")
def model_safety_report(db: Session = Depends(get_db)) -> dict:
    return model_safety.report(db)
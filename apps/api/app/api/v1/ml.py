from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services import baseline_ml
from app.services import model_research
from app.services import probability_diagnostics

router = APIRouter(prefix="/ml", tags=["Baseline ML"])


@router.get("/status")
def get_status() -> dict:
    return baseline_ml.status()


@router.post("/train")
def train_model(db: Session = Depends(get_db)) -> dict:
    try:
        return baseline_ml.train(db)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/races/{race_id}")
def predict_race(race_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        return baseline_ml.predict_race(db, race_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

@router.get("/research")
def temporal_model_research(db: Session = Depends(get_db)) -> dict:
    try:
        return model_research.temporal_research(db)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

@router.get("/probability-diagnostics")
def probability_diagnostic_report(db: Session = Depends(get_db)) -> dict:
    try:
        return probability_diagnostics.report(db)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

@router.get("/calibration-promotion")
def calibration_promotion_report(db: Session = Depends(get_db)) -> dict:
    try:
        return probability_diagnostics.promotion_report(db)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.coupon_optimizer import model_health, plan_sequence

router = APIRouter(prefix="/decision", tags=["Decision Pack"])


@router.get("/model-health")
def get_model_health() -> dict:
    return model_health()


@router.get("/sequence/{race_id}")
def get_sequence_plan(
    race_id: int,
    risk: str = Query(default="balanced"),
    max_columns: int = Query(default=240, ge=1, le=10000),
    leg_count: int = Query(default=6, ge=1, le=8),
    db: Session = Depends(get_db),
) -> dict:
    try:
        return plan_sequence(db, race_id, risk=risk, max_columns=max_columns, leg_count=leg_count)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
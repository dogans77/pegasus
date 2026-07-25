from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.prediction_snapshot import PredictionSnapshot
from app.models.race import Race
from app.services.race_intelligence import analyze_race
from app.services import baseline_ml

router = APIRouter(prefix="/prediction-audit", tags=["Prediction Audit"])
MODEL_VERSION = "baseline-hp-agf-weight-v1"


def build_snapshot(db: Session, race_id: int) -> PredictionSnapshot:
    try:
        chaos_index, entries = analyze_race(db, race_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    model_version = MODEL_VERSION
    payload = {"entries": [entry.__dict__ for entry in entries], "source": "baseline_rules"}
    try:
        prediction = baseline_ml.predict_race(db, race_id)
        model_version = prediction["model_version"]
        payload = {
            "entries": prediction["entries"],
            "deployment": prediction.get("deployment"),
            "source": "deployed_model",
        }
    except (LookupError, ValueError):
        # The transparent rules model remains a valid fallback before the
        # trained artifact exists or for an incomplete race card.
        pass
    snapshot = db.scalar(
        select(PredictionSnapshot)
        .where(PredictionSnapshot.race_id == race_id, PredictionSnapshot.model_version == model_version)
        .order_by(PredictionSnapshot.generated_at.desc())
    )
    if snapshot is None:
        snapshot = PredictionSnapshot(
            race_id=race_id,
            model_version=model_version,
            chaos_index=chaos_index,
            payload=payload,
        )
        db.add(snapshot)
    else:
        snapshot.chaos_index = chaos_index
        snapshot.payload = payload
    db.commit()
    db.refresh(snapshot)
    return snapshot


def serialize(snapshot: PredictionSnapshot) -> dict:
    return {
        "id": snapshot.id,
        "race_id": snapshot.race_id,
        "model_version": snapshot.model_version,
        "chaos_index": float(snapshot.chaos_index),
        "payload": snapshot.payload,
        "generated_at": snapshot.generated_at,
    }


@router.post("/races/{race_id}/snapshot", status_code=status.HTTP_201_CREATED)
def create_snapshot(race_id: int, db: Session = Depends(get_db)) -> dict:
    return serialize(build_snapshot(db, race_id))


@router.get("/races/{race_id}")
def list_snapshots(race_id: int, db: Session = Depends(get_db)) -> list[dict]:
    if not db.get(Race, race_id):
        raise HTTPException(status_code=404, detail="Race not found")
    snapshots = list(
        db.scalars(
            select(PredictionSnapshot)
            .where(PredictionSnapshot.race_id == race_id)
            .order_by(PredictionSnapshot.generated_at.desc())
        )
    )
    return [serialize(snapshot) for snapshot in snapshots]


@router.post("/daily", status_code=status.HTTP_201_CREATED)
def snapshot_daily(race_date: date, db: Session = Depends(get_db)) -> dict:
    races = list(db.scalars(select(Race).where(Race.race_date == race_date).order_by(Race.race_number)))
    snapshots = []
    skipped = []
    for race in races:
        try:
            snapshots.append(serialize(build_snapshot(db, race.id)))
        except HTTPException:
            skipped.append(race.id)
    return {"race_date": race_date, "snapshots_created": len(snapshots), "race_ids_skipped": skipped, "snapshots": snapshots}
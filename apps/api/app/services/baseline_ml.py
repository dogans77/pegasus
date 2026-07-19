from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.race import Race
from app.models.race_entry import RaceEntry
from app.models.race_result import RaceResult

MODEL_VERSION = "baseline-logistic-v1"
NUMERIC_FEATURES = ["handicap_rating", "weight_kg", "agf_percent", "barrier", "distance_meters", "field_size"]
CATEGORICAL_FEATURES = ["surface", "race_class"]
FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES
ARTIFACT_DIR = Path(__file__).resolve().parent.parent / "ml" / "artifacts"
MODEL_PATH = ARTIFACT_DIR / "baseline_logistic_v1.joblib"
METADATA_PATH = ARTIFACT_DIR / "baseline_logistic_v1.json"


def _entry_row(entry: RaceEntry, race: Race, field_size: int) -> dict:
    return {
        "entry_id": entry.id,
        "race_id": race.id,
        "race_date": race.race_date.isoformat(),
        "program_number": entry.program_number,
        "handicap_rating": float(entry.handicap_rating) if entry.handicap_rating is not None else None,
        "weight_kg": float(entry.weight_kg) if entry.weight_kg is not None else None,
        "agf_percent": float(entry.agf_percent) if entry.agf_percent is not None else None,
        "barrier": entry.barrier,
        "distance_meters": race.distance_meters,
        "field_size": field_size,
        "surface": race.surface or "unknown",
        "race_class": race.race_class or "unknown",
    }


def training_frame(db: Session) -> pd.DataFrame:
    rows = db.execute(
        select(RaceEntry, Race, RaceResult)
        .join(Race, Race.id == RaceEntry.race_id)
        .join(RaceResult, RaceResult.race_id == Race.id)
        .order_by(Race.race_date, Race.id, RaceEntry.program_number)
    ).all()
    field_sizes: dict[int, int] = {}
    for entry, race, _ in rows:
        field_sizes[race.id] = field_sizes.get(race.id, 0) + 1
    records = []
    for entry, race, result in rows:
        if result.winner_entry_id is None:
            continue
        record = _entry_row(entry, race, field_sizes[race.id])
        record["winner"] = int(entry.id == result.winner_entry_id)
        records.append(record)
    return pd.DataFrame(records)


def _pipeline() -> Pipeline:
    numeric = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scale", StandardScaler()),
    ])
    categorical = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(handle_unknown="ignore")),
    ])
    transform = ColumnTransformer([
        ("numeric", numeric, NUMERIC_FEATURES),
        ("categorical", categorical, CATEGORICAL_FEATURES),
    ])
    return Pipeline([
        ("features", transform),
        ("classifier", LogisticRegression(max_iter=2000, class_weight="balanced", random_state=42)),
    ])


def _race_metrics(frame: pd.DataFrame, probabilities) -> dict:
    scored = frame[["race_id", "entry_id", "winner"]].copy()
    scored["raw_probability"] = probabilities
    scored["win_probability"] = scored.groupby("race_id")["raw_probability"].transform(lambda values: values / max(values.sum(), 1e-9))
    ranked = scored.sort_values(["race_id", "win_probability"], ascending=[True, False])
    groups = list(ranked.groupby("race_id", sort=False))
    if not groups:
        return {"evaluated_races": 0, "top1_accuracy": None, "top3_coverage": None}
    top1 = sum(int(group.iloc[0].winner == 1) for _, group in groups) / len(groups)
    top3 = sum(int(group.head(3).winner.sum() > 0) for _, group in groups) / len(groups)
    return {
        "evaluated_races": len(groups),
        "top1_accuracy": round(float(top1), 4),
        "top3_coverage": round(float(top3), 4),
    }


def train(db: Session) -> dict:
    frame = training_frame(db)
    settled_races = int(frame["race_id"].nunique()) if not frame.empty else 0
    if settled_races < 30:
        raise ValueError("At least 30 distinct settled races are required for baseline training.")
    dates = sorted(frame["race_date"].unique())
    split_index = max(1, int(len(dates) * 0.75))
    split_index = min(split_index, len(dates) - 1) if len(dates) > 1 else 1
    train_dates = set(dates[:split_index])
    train_frame = frame[frame["race_date"].isin(train_dates)].copy()
    test_frame = frame[~frame["race_date"].isin(train_dates)].copy()
    if test_frame.empty:
        test_frame = train_frame.copy()
    pipeline = _pipeline()
    pipeline.fit(train_frame[FEATURES], train_frame["winner"])
    probabilities = pipeline.predict_proba(test_frame[FEATURES])[:, 1]
    metrics = _race_metrics(test_frame, probabilities)
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    metadata = {
        "model_version": MODEL_VERSION,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "settled_races": settled_races,
        "training_entries": int(len(train_frame)),
        "test_entries": int(len(test_frame)),
        "feature_names": FEATURES,
        "metrics": metrics,
        "note": "Temporal holdout baseline. This is a decision-support probability model, not a guarantee.",
    }
    joblib.dump({"pipeline": pipeline, "metadata": metadata}, MODEL_PATH)
    METADATA_PATH.write_text(json.dumps(metadata, ensure_ascii=True, indent=2), encoding="utf-8")
    return metadata


def status() -> dict:
    if not METADATA_PATH.exists():
        return {"trained": False, "model_version": MODEL_VERSION}
    return {"trained": True, **json.loads(METADATA_PATH.read_text(encoding="utf-8"))}


def predict_race(db: Session, race_id: int) -> dict:
    if not MODEL_PATH.exists():
        raise LookupError("Baseline model has not been trained yet.")
    race = db.get(Race, race_id)
    if race is None:
        raise LookupError("Race not found.")
    entries = list(db.scalars(select(RaceEntry).where(RaceEntry.race_id == race_id).order_by(RaceEntry.program_number)))
    if len(entries) < 2:
        raise ValueError("At least two entries are required for prediction.")
    rows = [_entry_row(entry, race, len(entries)) for entry in entries]
    artifact = joblib.load(MODEL_PATH)
    raw = artifact["pipeline"].predict_proba(pd.DataFrame(rows)[FEATURES])[:, 1]
    normalizer = max(float(raw.sum()), 1e-9)
    ranked = sorted([
        {
            "entry_id": row["entry_id"],
            "program_number": row["program_number"],
            "win_probability": round(float(value / normalizer * 100), 2),
        }
        for row, value in zip(rows, raw)
    ], key=lambda item: item["win_probability"], reverse=True)
    return {"race_id": race_id, "model_version": MODEL_VERSION, "entries": ranked}
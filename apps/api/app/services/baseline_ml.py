from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models.race import Race
from app.models.race_entry import RaceEntry
from app.models.race_result import RaceResult

MODEL_VERSION = "participant-logistic-v3"
NUMERIC_FEATURES = [
    "handicap_rating", "weight_kg", "agf_percent", "barrier", "distance_meters", "field_size",
    "days_since_last_start", "prior_starts", "prior_wins", "prior_win_rate", "last_start_won",
    "same_surface_starts", "same_surface_win_rate", "same_distance_starts", "same_distance_win_rate",
    "same_track_starts", "same_track_win_rate",
    "jockey_prior_starts", "jockey_prior_win_rate",
    "trainer_prior_starts", "trainer_prior_win_rate",
    "jockey_trainer_prior_starts", "jockey_trainer_prior_win_rate",
]
CATEGORICAL_FEATURES = ["surface", "race_class"]
FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES
ARTIFACT_DIR = Path(__file__).resolve().parent.parent / "ml" / "artifacts"
MODEL_PATH = ARTIFACT_DIR / "participant_logistic_v3.joblib"
METADATA_PATH = ARTIFACT_DIR / "participant_logistic_v3.json"


def _empty_state() -> dict:
    return {"starts": 0, "wins": 0, "last_date": None, "last_won": None, "surface": defaultdict(lambda: [0, 0]), "distance": defaultdict(lambda: [0, 0]), "track": defaultdict(lambda: [0, 0])}


def _rate(bucket) -> float | None:
    return round(bucket[1] / bucket[0], 5) if bucket and bucket[0] else None


def _history_features(entry: RaceEntry, race: Race, state: dict, jockey_state: dict, trainer_state: dict, pair_state: dict) -> dict:
    surface = race.surface or "unknown"
    distance = race.distance_meters or 0
    track_id = race.track_id
    surface_stats = state["surface"][surface]
    distance_stats = state["distance"][distance]
    track_stats = state["track"][track_id]
    last_date = state["last_date"]
    return {
        "days_since_last_start": (race.race_date - last_date).days if last_date else None,
        "prior_starts": state["starts"],
        "prior_wins": state["wins"],
        "prior_win_rate": round(state["wins"] / state["starts"], 5) if state["starts"] else None,
        "last_start_won": int(state["last_won"]) if state["last_won"] is not None else None,
        "same_surface_starts": surface_stats[0],
        "same_surface_win_rate": _rate(surface_stats),
        "same_distance_starts": distance_stats[0],
        "same_distance_win_rate": _rate(distance_stats),
        "same_track_starts": track_stats[0],
        "same_track_win_rate": _rate(track_stats),
        "jockey_prior_starts": jockey_state["starts"],
        "jockey_prior_win_rate": round(jockey_state["wins"] / jockey_state["starts"], 5) if jockey_state["starts"] else None,
        "trainer_prior_starts": trainer_state["starts"],
        "trainer_prior_win_rate": round(trainer_state["wins"] / trainer_state["starts"], 5) if trainer_state["starts"] else None,
        "jockey_trainer_prior_starts": pair_state["starts"],
        "jockey_trainer_prior_win_rate": round(pair_state["wins"] / pair_state["starts"], 5) if pair_state["starts"] else None,
    }


def _entry_row(entry: RaceEntry, race: Race, field_size: int, state: dict | None = None, jockey_state: dict | None = None, trainer_state: dict | None = None, pair_state: dict | None = None) -> dict:
    row = {
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
    row.update(_history_features(entry, race, state or _empty_state(), jockey_state or _empty_state(), trainer_state or _empty_state(), pair_state or _empty_state()))
    return row


def _settled_groups(db: Session, before_date=None) -> list[tuple[Race, RaceResult, list[RaceEntry]]]:
    statement = (
        select(Race, RaceResult, RaceEntry)
        .join(RaceResult, RaceResult.race_id == Race.id)
        .join(RaceEntry, RaceEntry.race_id == Race.id)
        .order_by(Race.race_date, Race.race_number, Race.id, RaceEntry.program_number)
    )
    if before_date is not None:
        statement = statement.where(Race.race_date < before_date)
    grouped: dict[int, tuple[Race, RaceResult, list[RaceEntry]]] = {}
    for race, result, entry in db.execute(statement).all():
        if race.id not in grouped:
            grouped[race.id] = (race, result, [])
        grouped[race.id][2].append(entry)
    return list(grouped.values())


def _record_outcome(state: dict, race: Race, won: bool) -> None:
    state["starts"] += 1
    state["wins"] += int(won)
    state["last_date"] = race.race_date
    state["last_won"] = won
    for key, value in (("surface", race.surface or "unknown"), ("distance", race.distance_meters or 0), ("track", race.track_id)):
        state[key][value][0] += 1
        state[key][value][1] += int(won)


def _apply_race_to_history(race: Race, result: RaceResult, entries: list[RaceEntry], horses: dict, jockeys: dict, trainers: dict, pairs: dict) -> None:
    for entry in entries:
        won = entry.id == result.winner_entry_id
        _record_outcome(horses[entry.horse_id], race, won)
        if entry.jockey_id is not None:
            _record_outcome(jockeys[entry.jockey_id], race, won)
        if entry.trainer_id is not None:
            _record_outcome(trainers[entry.trainer_id], race, won)
        if entry.jockey_id is not None and entry.trainer_id is not None:
            _record_outcome(pairs[(entry.jockey_id, entry.trainer_id)], race, won)


def training_frame(db: Session) -> pd.DataFrame:
    horses, jockeys, trainers, pairs = (defaultdict(_empty_state) for _ in range(4))
    records = []
    for race, result, entries in _settled_groups(db):
        if result.winner_entry_id is None or len(entries) < 2:
            continue
        for entry in entries:
            pair_key = (entry.jockey_id, entry.trainer_id)
            record = _entry_row(entry, race, len(entries), horses[entry.horse_id], jockeys[entry.jockey_id], trainers[entry.trainer_id], pairs[pair_key])
            record["winner"] = int(entry.id == result.winner_entry_id)
            records.append(record)
        _apply_race_to_history(race, result, entries, horses, jockeys, trainers, pairs)
    return pd.DataFrame(records)


def _pipeline() -> Pipeline:
    numeric = Pipeline([("imputer", SimpleImputer(strategy="median")), ("scale", StandardScaler())])
    categorical = Pipeline([("imputer", SimpleImputer(strategy="most_frequent")), ("onehot", OneHotEncoder(handle_unknown="ignore"))])
    transform = ColumnTransformer([("numeric", numeric, NUMERIC_FEATURES), ("categorical", categorical, CATEGORICAL_FEATURES)])
    return Pipeline([("features", transform), ("classifier", LogisticRegression(max_iter=2500, class_weight="balanced", random_state=42))])


def _race_metrics(frame: pd.DataFrame, probabilities) -> dict:
    scored = frame[["race_id", "entry_id", "winner"]].copy()
    scored["raw_probability"] = probabilities
    scored["win_probability"] = scored.groupby("race_id")["raw_probability"].transform(lambda values: values / max(values.sum(), 1e-9))
    groups = list(scored.sort_values(["race_id", "win_probability"], ascending=[True, False]).groupby("race_id", sort=False))
    if not groups:
        return {"evaluated_races": 0, "top1_accuracy": None, "top3_coverage": None}
    return {"evaluated_races": len(groups), "top1_accuracy": round(sum(int(group.iloc[0].winner == 1) for _, group in groups) / len(groups), 4), "top3_coverage": round(sum(int(group.head(3).winner.sum() > 0) for _, group in groups) / len(groups), 4)}


def _favorite_metrics(frame: pd.DataFrame, column: str, ascending: bool = False) -> dict:
    if frame.empty:
        return {"evaluated_races": 0, "top1_accuracy": None}
    scored = frame[["race_id", "winner", column]].copy()
    fallback = float("inf") if ascending else float("-inf")
    scored["signal"] = pd.to_numeric(scored[column], errors="coerce").fillna(fallback)
    groups = list(scored.sort_values(["race_id", "signal"], ascending=[True, ascending]).groupby("race_id", sort=False))
    return {"evaluated_races": len(groups), "top1_accuracy": round(sum(int(group.iloc[0].winner == 1) for _, group in groups) / len(groups), 4)} if groups else {"evaluated_races": 0, "top1_accuracy": None}


def train(db: Session) -> dict:
    frame = training_frame(db)
    settled_races = int(frame["race_id"].nunique()) if not frame.empty else 0
    if settled_races < 100:
        raise ValueError("At least 100 distinct settled races are required for the horse-form model.")
    dates = sorted(frame["race_date"].unique())
    split_index = min(max(1, int(len(dates) * 0.75)), len(dates) - 1)
    train_dates = set(dates[:split_index])
    train_frame, test_frame = frame[frame["race_date"].isin(train_dates)].copy(), frame[~frame["race_date"].isin(train_dates)].copy()
    if test_frame.empty:
        test_frame = train_frame.copy()
    pipeline = _pipeline()
    pipeline.fit(train_frame[FEATURES], train_frame["winner"])
    metrics = _race_metrics(test_frame, pipeline.predict_proba(test_frame[FEATURES])[:, 1])
    benchmarks = {"agf_favorite": _favorite_metrics(test_frame, "agf_percent"), "handicap_leader": _favorite_metrics(test_frame, "handicap_rating"), "lowest_weight": _favorite_metrics(test_frame, "weight_kg", ascending=True)}
    challenger_top1 = metrics.get("top1_accuracy") or 0.0
    benchmark_top1 = benchmarks["handicap_leader"].get("top1_accuracy") or 0.0
    selected = MODEL_VERSION if challenger_top1 >= benchmark_top1 else "handicap-leader-v1"
    deployment = {
        "policy": "champion_challenger_v1",
        "selected_model": selected,
        "challenger_top1_accuracy": challenger_top1,
        "handicap_benchmark_top1_accuracy": benchmark_top1,
        "reason": "Probability model outperformed the transparent handicap benchmark." if selected == MODEL_VERSION else "Transparent handicap benchmark outperformed the probability model on the temporal holdout.",
    }
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    metadata = {"model_version": MODEL_VERSION, "trained_at": datetime.now(timezone.utc).isoformat(), "settled_races": settled_races, "training_entries": int(len(train_frame)), "test_entries": int(len(test_frame)), "feature_names": FEATURES, "metrics": metrics, "benchmarks": benchmarks, "deployment": deployment, "note": "Temporal horse-form model. Probabilities are decision support, not guarantees."}
    joblib.dump({"pipeline": pipeline, "metadata": metadata}, MODEL_PATH)
    METADATA_PATH.write_text(json.dumps(metadata, ensure_ascii=True, indent=2), encoding="utf-8")
    return metadata


def status() -> dict:
    if not METADATA_PATH.exists():
        return {"trained": False, "model_version": MODEL_VERSION}
    return {"trained": True, **json.loads(METADATA_PATH.read_text(encoding="utf-8"))}


def predict_race(db: Session, race_id: int) -> dict:
    if not MODEL_PATH.exists():
        raise LookupError("Horse-form model has not been trained yet.")
    race = db.get(Race, race_id)
    if race is None:
        raise LookupError("Race not found.")
    entries = list(db.scalars(select(RaceEntry).where(RaceEntry.race_id == race_id).order_by(RaceEntry.program_number)))
    if len(entries) < 2:
        raise ValueError("At least two entries are required for prediction.")
    horses, jockeys, trainers, pairs = (defaultdict(_empty_state) for _ in range(4))
    for prior_race, result, prior_entries in _settled_groups(db, before_date=race.race_date):
        _apply_race_to_history(prior_race, result, prior_entries, horses, jockeys, trainers, pairs)
    rows = [_entry_row(entry, race, len(entries), horses[entry.horse_id], jockeys[entry.jockey_id], trainers[entry.trainer_id], pairs[(entry.jockey_id, entry.trainer_id)]) for entry in entries]
    artifact = joblib.load(MODEL_PATH)
    deployment = artifact["metadata"].get("deployment", {"selected_model": MODEL_VERSION})
    selected_model = deployment.get("selected_model", MODEL_VERSION)
    if selected_model == "handicap-leader-v1":
        raw = [max(float(row["handicap_rating"] or 0), 0.01) for row in rows]
    else:
        raw = artifact["pipeline"].predict_proba(pd.DataFrame(rows)[FEATURES])[:, 1]
    normalizer = max(float(sum(raw)), 1e-9)
    ranked = sorted([{"entry_id": row["entry_id"], "program_number": row["program_number"], "win_probability": round(float(value / normalizer * 100), 2), "days_since_last_start": row["days_since_last_start"], "prior_starts": row["prior_starts"], "prior_win_rate": row["prior_win_rate"]} for row, value in zip(rows, raw)], key=lambda item: item["win_probability"], reverse=True)
    return {"race_id": race_id, "model_version": selected_model, "candidate_model": MODEL_VERSION, "deployment": deployment, "entries": ranked}
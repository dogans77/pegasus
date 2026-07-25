from __future__ import annotations

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.services import baseline_ml


def _normalize(frame: pd.DataFrame, raw: np.ndarray) -> pd.DataFrame:
    scored = frame[["race_id", "winner"]].copy()
    scored["raw"] = raw
    scored["probability"] = scored.groupby("race_id")["raw"].transform(lambda values: values / max(float(values.sum()), 1e-9))
    scored["field_size"] = scored.groupby("race_id")["race_id"].transform("size")
    return scored


def _brier(scored: pd.DataFrame, probability: str) -> float:
    return round(float(((scored[probability] - scored["winner"]) ** 2).mean()), 6)


def _ece(scored: pd.DataFrame, probability: str) -> float:
    if scored.empty:
        return 0.0
    working = scored.copy()
    working["bucket"] = pd.cut(working[probability], bins=[0, .05, .1, .15, .2, .3, .45, 1.01], include_lowest=True)
    total = len(working)
    return round(float(sum(abs(group[probability].mean() - group["winner"].mean()) * len(group) / total for _, group in working.groupby("bucket", observed=True))), 6)


def _top1(scored: pd.DataFrame, probability: str) -> float:
    top = scored.loc[scored.groupby("race_id")[probability].idxmax()]
    return round(float(top["winner"].mean()), 6) if not top.empty else 0.0


def report(db: Session) -> dict:
    frame = baseline_ml.training_frame(db)
    dates = sorted(frame["race_date"].unique()) if not frame.empty else []
    if len(dates) < 30:
        raise ValueError("At least 30 race dates are required for probability diagnostics.")
    split = max(1, int(len(dates) * .8))
    train_dates, test_dates = set(dates[:split]), set(dates[split:])
    train = frame[frame["race_date"].isin(train_dates)].copy()
    test = frame[frame["race_date"].isin(test_dates)].copy()
    if train.empty or test.empty:
        raise ValueError("Temporal diagnostic split is empty.")
    pipeline = baseline_ml._pipeline()
    pipeline.fit(train[baseline_ml.FEATURES], train["winner"])
    scored = _normalize(test, pipeline.predict_proba(test[baseline_ml.FEATURES])[:, 1])
    scored["uniform"] = 1.0 / scored["field_size"]
    candidates = []
    for alpha in np.arange(0.0, 0.61, 0.05):
        column = f"shrink_{alpha:.2f}"
        scored[column] = (1.0 - alpha) * scored["probability"] + alpha * scored["uniform"]
        candidates.append({
            "shrinkage": round(float(alpha), 2),
            "brier_score": _brier(scored, column),
            "expected_calibration_error": _ece(scored, column),
            "top1_accuracy": _top1(scored, column),
        })
    raw = {"shrinkage": 0.0, "brier_score": _brier(scored, "probability"), "expected_calibration_error": _ece(scored, "probability"), "top1_accuracy": _top1(scored, "probability")}
    best = min(candidates, key=lambda item: item["brier_score"])
    return {
        "model_version": baseline_ml.MODEL_VERSION,
        "train_race_dates": len(train_dates),
        "test_race_dates": len(test_dates),
        "test_races": int(test["race_id"].nunique()),
        "raw": raw,
        "best_shrinkage_candidate": best,
        "candidate_improves_brier": best["brier_score"] < raw["brier_score"],
        "note": "Research only. The candidate calibration is not deployed automatically.",
    }

def promotion_report(db: Session) -> dict:
    """Choose calibration only on a tune window, then evaluate it on unseen dates."""
    frame = baseline_ml.training_frame(db)
    dates = sorted(frame["race_date"].unique()) if not frame.empty else []
    if len(dates) < 45:
        raise ValueError("At least 45 race dates are required for calibration promotion testing.")
    train_end = max(1, int(len(dates) * .65))
    tune_end = max(train_end + 1, int(len(dates) * .80))
    train_dates = set(dates[:train_end])
    tune_dates = set(dates[train_end:tune_end])
    holdout_dates = set(dates[tune_end:])
    train = frame[frame["race_date"].isin(train_dates)].copy()
    tune = frame[frame["race_date"].isin(tune_dates)].copy()
    holdout = frame[frame["race_date"].isin(holdout_dates)].copy()
    if train.empty or tune.empty or holdout.empty:
        raise ValueError("Calibration promotion temporal partitions are incomplete.")
    pipeline = baseline_ml._pipeline()
    pipeline.fit(train[baseline_ml.FEATURES], train["winner"])
    tune_scored = _normalize(tune, pipeline.predict_proba(tune[baseline_ml.FEATURES])[:, 1])
    tune_scored["uniform"] = 1.0 / tune_scored["field_size"]
    tuning = []
    for alpha in np.arange(0.0, .61, .05):
        column = f"tune_{alpha:.2f}"
        tune_scored[column] = (1.0 - alpha) * tune_scored["probability"] + alpha * tune_scored["uniform"]
        tuning.append((float(alpha), _brier(tune_scored, column)))
    selected_alpha = min(tuning, key=lambda item: item[1])[0]
    holdout_scored = _normalize(holdout, pipeline.predict_proba(holdout[baseline_ml.FEATURES])[:, 1])
    holdout_scored["uniform"] = 1.0 / holdout_scored["field_size"]
    holdout_scored["candidate"] = (1.0 - selected_alpha) * holdout_scored["probability"] + selected_alpha * holdout_scored["uniform"]
    raw_brier = _brier(holdout_scored, "probability")
    candidate_brier = _brier(holdout_scored, "candidate")
    raw_top1 = _top1(holdout_scored, "probability")
    candidate_top1 = _top1(holdout_scored, "candidate")
    eligible = candidate_brier < raw_brier and candidate_top1 >= raw_top1 - .005
    return {
        "selected_shrinkage": round(selected_alpha, 2),
        "tune_races": int(tune["race_id"].nunique()),
        "holdout_races": int(holdout["race_id"].nunique()),
        "raw_holdout_brier": raw_brier,
        "candidate_holdout_brier": candidate_brier,
        "raw_holdout_top1": raw_top1,
        "candidate_holdout_top1": candidate_top1,
        "eligible_for_manual_promotion": eligible,
        "note": "Eligible means only that the candidate passed this holdout gate. It is not deployed automatically.",
    }
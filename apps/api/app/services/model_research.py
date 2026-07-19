from __future__ import annotations

import pandas as pd

from sqlalchemy.orm import Session

from app.services import baseline_ml


def _normalized_scores(frame: pd.DataFrame, probabilities) -> pd.DataFrame:
    scored = frame[["race_id", "entry_id", "winner"]].copy()
    scored["raw_probability"] = probabilities
    scored["probability"] = scored.groupby("race_id")["raw_probability"].transform(lambda values: values / max(values.sum(), 1e-9))
    return scored


def _calibration(scored: pd.DataFrame) -> list[dict]:
    if scored.empty:
        return []
    bins = [0, 0.05, 0.10, 0.15, 0.20, 0.30, 0.45, 1.01]
    labels = ["0-5", "5-10", "10-15", "15-20", "20-30", "30-45", "45+"]
    working = scored.copy()
    working["bucket"] = pd.cut(working["probability"], bins=bins, labels=labels, include_lowest=True)
    report = []
    for bucket, group in working.groupby("bucket", observed=True):
        report.append({
            "bucket": str(bucket),
            "entries": int(len(group)),
            "mean_predicted_probability": round(float(group["probability"].mean() * 100), 2),
            "actual_win_rate": round(float(group["winner"].mean() * 100), 2),
        })
    return report


def temporal_research(db: Session) -> dict:
    frame = baseline_ml.training_frame(db)
    if frame.empty:
        raise ValueError("No settled race data is available.")
    dates = sorted(frame["race_date"].unique())
    if len(dates) < 20:
        raise ValueError("At least 20 race dates are required for temporal research.")
    fractions = [(0.55, 0.70), (0.70, 0.85), (0.85, 1.00)]
    folds = []
    final_scored = None
    for index, (train_fraction, test_fraction) in enumerate(fractions, start=1):
        train_end = max(1, int(len(dates) * train_fraction))
        test_end = max(train_end + 1, int(len(dates) * test_fraction))
        train_dates = set(dates[:train_end])
        test_dates = set(dates[train_end:test_end])
        train_frame = frame[frame["race_date"].isin(train_dates)].copy()
        test_frame = frame[frame["race_date"].isin(test_dates)].copy()
        if train_frame.empty or test_frame.empty:
            continue
        pipeline = baseline_ml._pipeline()
        pipeline.fit(train_frame[baseline_ml.FEATURES], train_frame["winner"])
        probabilities = pipeline.predict_proba(test_frame[baseline_ml.FEATURES])[:, 1]
        metrics = baseline_ml._race_metrics(test_frame, probabilities)
        benchmark = baseline_ml._favorite_metrics(test_frame, "handicap_rating")
        folds.append({
            "fold": index,
            "train_through": str(dates[train_end - 1]),
            "test_through": str(dates[min(test_end - 1, len(dates) - 1)]),
            "evaluated_races": metrics["evaluated_races"],
            "model_top1_accuracy": metrics["top1_accuracy"],
            "model_top3_coverage": metrics["top3_coverage"],
            "handicap_top1_accuracy": benchmark["top1_accuracy"],
        })
        final_scored = _normalized_scores(test_frame, probabilities)
    if not folds:
        raise ValueError("Temporal research folds could not be created.")
    model_average = round(sum(item["model_top1_accuracy"] or 0 for item in folds) / len(folds), 4)
    handicap_average = round(sum(item["handicap_top1_accuracy"] or 0 for item in folds) / len(folds), 4)
    return {
        "model_version": baseline_ml.MODEL_VERSION,
        "settled_races": int(frame["race_id"].nunique()),
        "folds": folds,
        "average_model_top1_accuracy": model_average,
        "average_handicap_top1_accuracy": handicap_average,
        "model_beats_handicap_on_average": model_average >= handicap_average,
        "latest_fold_calibration": _calibration(final_scored) if final_scored is not None else [],
        "note": "Expanding-window temporal evaluation. It tests only on races later than each training period.",
    }
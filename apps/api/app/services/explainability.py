from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.race import Race
from app.models.race_entry import RaceEntry
from app.services import baseline_ml


def _format_percent(value):
    return round(float(value) * 100, 1) if value is not None else None


def _signals(entry, race, features, probability):
    strengths, risks = [], []
    add_strength = strengths.append
    add_risk = risks.append
    if features['recent_top3_rate'] is not None and features['recent_top3_rate'] >= 0.66:
        add_strength({'label': 'Recent form', 'detail': f"Top-3 rate: {_format_percent(features['recent_top3_rate'])}%"})
    if features['recent_finish_average'] is not None and features['recent_finish_average'] <= 3.5:
        add_strength({'label': 'Finishing trend', 'detail': f"Last 3 average finish: {features['recent_finish_average']}"})
    if features['days_since_last_start'] is not None and 14 <= features['days_since_last_start'] <= 45:
        add_strength({'label': 'Rest profile', 'detail': f"{features['days_since_last_start']} days since last start"})
    if features['same_surface_finish_average'] is not None and features['same_surface_finish_average'] <= 3.5:
        add_strength({'label': 'Surface fit', 'detail': f"Surface average finish: {features['same_surface_finish_average']}"})
    if features['same_distance_finish_average'] is not None and features['same_distance_finish_average'] <= 3.5:
        add_strength({'label': 'Distance fit', 'detail': f"Distance average finish: {features['same_distance_finish_average']}"})
    if features['jockey_prior_win_rate'] is not None and features['jockey_prior_win_rate'] >= 0.12:
        add_strength({'label': 'Jockey form', 'detail': f"Prior win rate: {_format_percent(features['jockey_prior_win_rate'])}%"})
    if features['trainer_prior_win_rate'] is not None and features['trainer_prior_win_rate'] >= 0.10:
        add_strength({'label': 'Trainer form', 'detail': f"Prior win rate: {_format_percent(features['trainer_prior_win_rate'])}%"})
    if entry.handicap_rating is not None:
        add_strength({'label': 'Handicap rating', 'detail': f"Rating: {entry.handicap_rating}"})
    if features['days_since_last_start'] is not None and features['days_since_last_start'] > 60:
        add_risk({'label': 'Long layoff', 'detail': f"{features['days_since_last_start']} days since last start"})
    if features['last_finish_position'] is not None and features['last_finish_position'] >= 7:
        add_risk({'label': 'Last run', 'detail': f"Last finish: {features['last_finish_position']}"})
    if features['prior_starts'] == 0:
        add_risk({'label': 'Limited history', 'detail': 'No settled historical start in this data set'})
    return {'probability': probability, 'strengths': strengths[:4], 'risks': risks[:3]}


def explain_race(db: Session, race_id: int) -> dict:
    race = db.get(Race, race_id)
    if race is None:
        raise LookupError('Race not found.')
    prediction = baseline_ml.predict_race(db, race_id)
    probabilities = {item['entry_id']: item['win_probability'] for item in prediction['entries']}
    entries = list(db.scalars(select(RaceEntry).where(RaceEntry.race_id == race_id).order_by(RaceEntry.program_number)))
    horses, jockeys, trainers, pairs = (defaultdict(baseline_ml._empty_state) for _ in range(4))
    for prior_race, result, prior_entries in baseline_ml._settled_groups(db, before_date=race.race_date):
        baseline_ml._apply_race_to_history(prior_race, result, prior_entries, horses, jockeys, trainers, pairs)
    candidates = []
    for entry in entries:
        features = baseline_ml._history_features(entry, race, horses[entry.horse_id], jockeys[entry.jockey_id], trainers[entry.trainer_id], pairs[(entry.jockey_id, entry.trainer_id)])
        payload = _signals(entry, race, features, probabilities.get(entry.id, 0))
        candidates.append({
            'entry_id': entry.id,
            'program_number': entry.program_number,
            'horse_name': entry.horse.name if entry.horse else f'Entry {entry.program_number}',
            'win_probability': probabilities.get(entry.id, 0),
            **payload,
        })
    candidates.sort(key=lambda item: item['win_probability'], reverse=True)
    return {
        'race_id': race_id,
        'model_version': prediction['model_version'],
        'methodology': 'Transparent historical signals; these explain available form inputs and do not claim causal certainty.',
        'candidates': candidates[:5],
    }
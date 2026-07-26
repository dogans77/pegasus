from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func, select

from app.core.database import SessionLocal
from app.models.prediction_snapshot import PredictionSnapshot
from app.models.race import Race
from app.models.race_entry import RaceEntry
from app.models.race_result import RaceResult
from app.models.source_document import SourceDocument


def ranking_status(payload: object) -> list[str]:
    if not isinstance(payload, dict):
        return ['payload_not_object']
    rows = payload.get('entries') or payload.get('ranked_entries') or payload.get('ranking')
    if not isinstance(rows, list) or not rows:
        return ['ranking_missing']
    values = []
    for row in rows:
        if not isinstance(row, dict):
            return ['ranking_row_invalid']
        try:
            values.append(float(row.get('win_probability', row.get('probability'))))
        except (TypeError, ValueError):
            return ['probability_missing']
    if any(value < 0 for value in values):
        return ['negative_probability']
    if any(values[index] < values[index + 1] - 1e-8 for index in range(len(values) - 1)):
        return ['ranking_not_descending']
    total = sum(values)
    # Legacy rules snapshots store percentages (0..100); trained snapshots store
    # fractions (0..1). Both are accepted only when their own unit is coherent.
    if max(values) <= 1.00001:
        if not 0.98 <= total <= 1.02:
            return ['fractional_probability_total_invalid']
    elif max(values) <= 100.0001:
        if not 98.0 <= total <= 102.0:
            return ['percentage_probability_total_invalid']
    else:
        return ['probability_outside_known_units']
    return []


def result_status(result: RaceResult, entries: list[RaceEntry]) -> list[str]:
    try:
        order = [int(value) for value in (result.official_order or [])]
    except (TypeError, ValueError):
        return ['official_order_invalid']
    by_program = {int(entry.program_number): entry for entry in entries}
    if len(order) < 2:
        return ['official_order_too_short']
    if len(order) != len(set(order)):
        return ['official_order_duplicate']
    if any(program not in by_program for program in order):
        return ['official_order_not_on_card']
    if result.winner_entry_id != by_program[order[0]].id:
        return ['winner_does_not_match_order']
    return []


def main() -> None:
    db = SessionLocal()
    try:
        results = db.scalars(select(RaceResult)).all()
        result_issues = Counter()
        for result in results:
            entries = db.scalars(select(RaceEntry).where(RaceEntry.race_id == result.race_id)).all()
            result_issues.update(result_status(result, entries))
        snapshot_issues = Counter()
        for snapshot in db.scalars(select(PredictionSnapshot)).all():
            snapshot_issues.update(ranking_status(snapshot.payload))
        current_day = datetime.now().date()
        daily_races = db.scalar(select(func.count(Race.id)).where(Race.race_date == current_day)) or 0
        daily_entries = db.scalar(select(func.count(RaceEntry.id)).join(Race, Race.id == RaceEntry.race_id).where(Race.race_date == current_day)) or 0
        daily_sources = db.scalar(select(func.count(SourceDocument.id)).where(SourceDocument.race_date == current_day, SourceDocument.document_type == 'daily_program_html')) or 0
        output = {
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'current_day': current_day.isoformat(),
            'result_rows_checked': len(results),
            'result_contract_issues': dict(result_issues),
            'prediction_contract_issues': dict(snapshot_issues),
            'daily_program': {'races': daily_races, 'entries': daily_entries, 'sources': daily_sources},
            'interpretation': 'Only internally consistent records are eligible for future training. This closeout does not retrain, promote, or market a model.',
        }
    finally:
        db.close()
    report = Path('deploy/reports') / ('data-foundation-closeout-' + datetime.now().strftime('%Y%m%d-%H%M%S') + '.json')
    report.write_text(json.dumps(output, ensure_ascii=True, indent=2), encoding='utf-8')
    print(json.dumps({'report': str(report), **output}, ensure_ascii=True))


if __name__ == '__main__':
    main()
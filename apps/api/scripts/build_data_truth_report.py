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


def payload_issues(payload: object) -> list[str]:
    if not isinstance(payload, dict):
        return ['payload_is_not_an_object']
    rows = payload.get('ranked_entries') or payload.get('entries') or payload.get('ranking')
    if not isinstance(rows, list) or not rows:
        return ['ranking_is_missing']
    probabilities = []
    for row in rows:
        if not isinstance(row, dict):
            return ['ranking_row_is_not_an_object']
        value = row.get('win_probability', row.get('probability'))
        try:
            probabilities.append(float(value))
        except (TypeError, ValueError):
            return ['ranking_probability_is_missing']
    if any(value < 0 or value > 1.00001 for value in probabilities):
        return ['ranking_probability_is_outside_unit_interval']
    if any(probabilities[index] < probabilities[index + 1] - 1e-8 for index in range(len(probabilities) - 1)):
        return ['ranking_probabilities_are_not_descending']
    total = sum(probabilities)
    if total < 0.98 or total > 1.02:
        return ['ranking_probability_total_is_outside_tolerance']
    return []


def main() -> None:
    db = SessionLocal()
    try:
        race_count = db.scalar(select(func.count(Race.id))) or 0
        entry_count = db.scalar(select(func.count(RaceEntry.id))) or 0
        result_count = db.scalar(select(func.count(RaceResult.id))) or 0
        result_sources = dict(db.execute(select(RaceResult.source, func.count()).group_by(RaceResult.source)).all())
        snapshots = db.scalars(select(PredictionSnapshot)).all()
        snapshot_problems = Counter()
        snapshot_examples = []
        for snapshot in snapshots:
            issues = payload_issues(snapshot.payload)
            if issues:
                snapshot_problems.update(issues)
                if len(snapshot_examples) < 20:
                    snapshot_examples.append({'snapshot_id': snapshot.id, 'race_id': snapshot.race_id, 'issues': issues})
        current_day = datetime.now().date()
        daily_races = db.scalar(select(func.count(Race.id)).where(Race.race_date == current_day)) or 0
        daily_entries = db.scalar(select(func.count(RaceEntry.id)).join(Race, Race.id == RaceEntry.race_id).where(Race.race_date == current_day)) or 0
        daily_sources = db.scalar(select(func.count(SourceDocument.id)).where(SourceDocument.race_date == current_day, SourceDocument.document_type == 'daily_program_html')) or 0
        report = {
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'current_day': current_day.isoformat(),
            'race_count': race_count,
            'entry_count': entry_count,
            'result_count': result_count,
            'result_sources': result_sources,
            'prediction_snapshot_count': len(snapshots),
            'prediction_contract_issue_counts': dict(snapshot_problems),
            'prediction_contract_examples': snapshot_examples,
            'daily_program': {'race_count': daily_races, 'entry_count': daily_entries, 'source_count': daily_sources},
            'publication_policy': 'Model publication remains safety-gated. This report never converts a prediction into a betting instruction.',
        }
    finally:
        db.close()
    output = Path('deploy/reports') / ('data-truth-evidence-' + datetime.now().strftime('%Y%m%d-%H%M%S') + '.json')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=True, indent=2), encoding='utf-8')
    print(json.dumps({'report': str(output), 'prediction_contract_issue_counts': report['prediction_contract_issue_counts'], 'daily_program': report['daily_program']}, ensure_ascii=True))


if __name__ == '__main__':
    main()
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.race import Race
from app.models.race_entry import RaceEntry
from app.models.race_result import RaceResult


def as_program_numbers(value: object) -> list[int]:
    if not isinstance(value, list):
        return []
    numbers: list[int] = []
    for item in value:
        try:
            numbers.append(int(item))
        except (TypeError, ValueError):
            return []
    return numbers


def main() -> None:
    db = SessionLocal()
    invalid: list[dict[str, object]] = []
    checked = 0
    valid = 0
    examples: list[dict[str, object]] = []

    try:
        rows = db.execute(select(RaceResult, Race).join(Race, Race.id == RaceResult.race_id)).all()
        for result, race in rows:
            checked += 1
            entries = db.scalars(select(RaceEntry).where(RaceEntry.race_id == race.id)).all()
            entry_by_program = {int(entry.program_number): entry for entry in entries}
            order = as_program_numbers(result.official_order)
            problems: list[str] = []

            if len(order) < 2:
                problems.append('official_order_missing_or_too_short')
            elif len(order) != len(set(order)):
                problems.append('official_order_contains_duplicates')
            elif any(number not in entry_by_program for number in order):
                problems.append('official_order_contains_unknown_program_number')
            elif result.winner_entry_id != entry_by_program[order[0]].id:
                problems.append('winner_entry_does_not_match_official_order')

            record = {
                'race_id': race.id,
                'race_date': race.race_date.isoformat(),
                'race_number': race.race_number,
                'source': result.source,
                'official_order': order,
                'entry_program_numbers': sorted(entry_by_program),
                'problems': problems,
            }
            if problems:
                invalid.append(record)
                if len(examples) < 25:
                    examples.append(record)
                # Preserve the record for a later official re-import, but prevent it
                # from being treated as settled training/evaluation data.
                result.source = 'tjk_needs_reconciliation'
            else:
                valid += 1

        db.commit()
    finally:
        db.close()

    report = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'checked_results': checked,
        'valid_results': valid,
        'quarantined_results': len(invalid),
        'problem_counts': dict(Counter(problem for item in invalid for problem in item['problems'])),
        'examples': examples,
        'note': 'Only result contracts that cannot be matched to the race card were quarantined. No result was invented or rewritten.',
    }
    output = Path('deploy/reports') / ('result-contract-audit-' + datetime.now().strftime('%Y%m%d-%H%M%S') + '.json')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=True, indent=2), encoding='utf-8')
    print(json.dumps({'report': str(output), **{key: report[key] for key in ('checked_results', 'valid_results', 'quarantined_results', 'problem_counts')}}, ensure_ascii=True))


if __name__ == '__main__':
    main()
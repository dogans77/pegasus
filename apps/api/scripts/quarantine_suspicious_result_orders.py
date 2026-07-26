import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.race_result import RaceResult


def is_suspicious(order) -> bool:
    if not isinstance(order, list) or len(order) < 4:
        return False
    try:
        values = [int(value) for value in order]
    except (TypeError, ValueError):
        return False
    return values == list(range(1, len(values) + 1))


with SessionLocal() as session:
    rows = list(session.scalars(select(RaceResult)))
    suspicious = [row for row in rows if row.source != "tjk_needs_reconciliation" and is_suspicious(row.official_order)]
    for row in suspicious:
        row.source = "tjk_needs_reconciliation"
    session.commit()
    payload = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "total_results": len(rows),
        "quarantined_result_ids": [row.id for row in suspicious],
        "quarantined_race_ids": [row.race_id for row in suspicious],
        "quarantined_count": len(suspicious),
        "rule": "Only exact ascending program-number orders [1,2,3,...] of length four or more are quarantined.",
    }
print(json.dumps(payload, ensure_ascii=False))
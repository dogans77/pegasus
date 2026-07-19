from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.race import Race
from app.models.track import Track

target = date.fromisoformat(sys.argv[1])
db = SessionLocal()
try:
    # Before the mapping repair, city id 3 was stored as Bursa although TJK
    # serves Istanbul at that id. Move only the requested day's records so
    # entries, results, snapshots and model audit history remain intact.
    wrong_track = db.scalar(select(Track).where(Track.name == 'Bursa'))
    right_track = db.scalar(select(Track).where(Track.name == 'Istanbul'))
    if right_track is None:
        right_track = Track(name='Istanbul', city='Istanbul')
        db.add(right_track)
        db.flush()
    moved_races = 0
    if wrong_track is not None:
        for race in db.scalars(select(Race).where(Race.track_id == wrong_track.id, Race.race_date == target)).all():
            race.track_id = right_track.id
            moved_races += 1
    db.commit()
    print(f'Moved {moved_races} incorrectly mapped race(s) from Bursa to Istanbul.')
finally:
    db.close()
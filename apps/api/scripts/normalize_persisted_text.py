from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.horse import Horse
from app.models.jockey import Jockey
from app.models.trainer import Trainer
from app.models.race import Race
from app.models.race_entry import RaceEntry
from app.models.source_document import SourceDocument
from app.models.track import Track
from app.services.text_normalization import repair_text


def merge_named(session, model, foreign_key: str) -> tuple[int, int]:
    changed = 0
    merged = 0
    for row in list(session.scalars(select(model).order_by(model.id))):
        original = row.name
        fixed = repair_text(original)
        if fixed == original:
            continue
        existing = session.scalar(select(model).where(model.name == fixed))
        if existing is not None and existing.id != row.id:
            for entry in session.scalars(select(RaceEntry).where(getattr(RaceEntry, foreign_key) == row.id)):
                setattr(entry, foreign_key, existing.id)
            session.delete(row)
            merged += 1
        else:
            row.name = fixed
            changed += 1
    return changed, merged


with SessionLocal() as session:
    horse_changed, horse_merged = merge_named(session, Horse, "horse_id")
    jockey_changed, jockey_merged = merge_named(session, Jockey, "jockey_id")
    trainer_changed, trainer_merged = merge_named(session, Trainer, "trainer_id")
    race_changed = 0
    source_changed = 0
    track_changed = 0
    for race in session.scalars(select(Race)):
        fixed = repair_text(race.race_class)
        if fixed != race.race_class:
            race.race_class = fixed
            race_changed += 1
    for track in session.scalars(select(Track)):
        fixed_name = repair_text(track.name)
        fixed_city = repair_text(track.city)
        if fixed_name != track.name:
            track.name = fixed_name
            track_changed += 1
        if fixed_city != track.city:
            track.city = fixed_city
            track_changed += 1
    for document in session.scalars(select(SourceDocument)):
        fixed_city = repair_text(document.city)
        if fixed_city != document.city:
            document.city = fixed_city
            source_changed += 1
    session.commit()
    print({
        "horses_changed": horse_changed,
        "horses_merged": horse_merged,
        "jockeys_changed": jockey_changed,
        "jockeys_merged": jockey_merged,
        "trainers_changed": trainer_changed,
        "trainers_merged": trainer_merged,
        "race_fields_changed": race_changed,
        "track_fields_changed": track_changed,
        "source_fields_changed": source_changed,
    })
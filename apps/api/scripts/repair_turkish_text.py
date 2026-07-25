from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.horse import Horse
from app.models.jockey import Jockey
from app.models.race_entry import RaceEntry
from app.models.trainer import Trainer
from app.services.text_normalization import has_mojibake, repair_text


def repair_model(db, model, field: str) -> tuple[int, int]:
    repaired = merged = 0
    for item in list(db.scalars(select(model))):
        name = getattr(item, "name")
        clean = repair_text(name)
        if clean == name:
            continue
        duplicate = db.scalar(select(model).where(model.name == clean))
        if duplicate is not None and duplicate.id != item.id:
            foreign = {Horse: "horse_id", Jockey: "jockey_id", Trainer: "trainer_id"}[model]
            for entry in db.scalars(select(RaceEntry).where(getattr(RaceEntry, foreign) == item.id)):
                setattr(entry, foreign, duplicate.id)
            db.delete(item)
            merged += 1
        else:
            item.name = clean
            repaired += 1
    return repaired, merged


with SessionLocal() as db:
    totals = {}
    for model, label in ((Horse, "horses"), (Jockey, "jockeys"), (Trainer, "trainers")):
        totals[label] = repair_model(db, model, "name")
    db.commit()
    remaining = {
        label: sum(1 for item in db.scalars(select(model)) if has_mojibake(item.name))
        for model, label in ((Horse, "horses"), (Jockey, "jockeys"), (Trainer, "trainers"))
    }
    print({"updated": totals, "remaining": remaining})
    if any(remaining.values()):
        raise SystemExit("Some malformed Turkish text remains after repair")
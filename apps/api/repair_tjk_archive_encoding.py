from sqlalchemy import select
from app.core.database import SessionLocal
from app.models.source_document import SourceDocument


def bad_score(value: str) -> int:
    return sum(value.count(character) for character in ("\u00c3", "\u00c4", "\u00c5"))


def repair(value: str) -> str:
    if not value or not bad_score(value):
        return value
    for encoding in ("cp1252", "latin1"):
        try:
            candidate = value.encode(encoding).decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
        if bad_score(candidate) < bad_score(value):
            return candidate
    return value


changed = 0
with SessionLocal() as db:
    documents = list(db.scalars(select(SourceDocument).where(SourceDocument.document_type == "daily_program_html")))
    for document in documents:
        fixed = repair(document.content)
        if fixed != document.content:
            document.content = fixed
            changed += 1
    db.commit()

print(f"Repaired {changed} archived TJK document(s).")
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.source_document import SourceDocument
from app.schemas.source_document import SourceDocumentResponse, TjkCsvPreviewRequest, TjkCsvPreviewResponse
from app.services.tjk_csv import TjkCsvError, fetch_csv

router = APIRouter(prefix="/crawler/tjk", tags=["TJK CSV"])

@router.post("/csv-preview", response_model=TjkCsvPreviewResponse, status_code=status.HTTP_201_CREATED)
def preview_csv(payload: TjkCsvPreviewRequest, db: Session = Depends(get_db)):
    try:
        url, checksum, headers, rows, content = fetch_csv(payload.city, payload.race_date)
    except TjkCsvError as exc:
        raise HTTPException(status_code=502, detail=f"TJK CSV fetch failed: {exc}") from exc
    document = db.scalar(select(SourceDocument).where(SourceDocument.source_url == url))
    if document is None:
        document = SourceDocument(provider="tjk", document_type="daily_program_csv", source_url=url, checksum=checksum, race_date=payload.race_date, city=payload.city, content=content)
        db.add(document)
    else:
        document.checksum, document.content = checksum, content
    db.commit(); db.refresh(document)
    return TjkCsvPreviewResponse(source_document_id=document.id, source_url=url, headers=headers, row_count=len(rows), sample_rows=rows[:5], raw_preview=content[:800])

@router.get("/documents", response_model=list[SourceDocumentResponse])
def list_documents(db: Session = Depends(get_db)):
    return list(db.scalars(select(SourceDocument).order_by(SourceDocument.id.desc())))

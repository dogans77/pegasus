from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.crawler_run import CrawlerRun
from app.schemas.crawler import CrawlerRunCreate, CrawlerRunResponse

router = APIRouter(prefix="/crawler", tags=["Crawler"])


@router.get("/health")
def crawler_health() -> dict[str, str]:
    return {"status": "ready", "provider": "tjk", "mode": "manual"}


@router.get("/runs", response_model=list[CrawlerRunResponse])
def list_runs(db: Session = Depends(get_db)) -> list[CrawlerRunResponse]:
    return list(db.scalars(select(CrawlerRun).order_by(CrawlerRun.id.desc())))


@router.post("/runs", response_model=CrawlerRunResponse, status_code=status.HTTP_201_CREATED)
def create_run(payload: CrawlerRunCreate, db: Session = Depends(get_db)) -> CrawlerRunResponse:
    run = CrawlerRun(**payload.model_dump())
    db.add(run)
    db.commit()
    db.refresh(run)
    return run

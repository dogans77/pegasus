from fastapi import FastAPI

from app.api.v1.horses import router as horse_router
from app.api.v1.intelligence import router as intelligence_router
from app.api.v1.crawler import router as crawler_router
from app.api.v1.people import router as people_router
from app.api.v1.races import router as race_router
from app.api.v1.tracks import router as track_router
from app.api.v1.tjk import router as tjk_router

app = FastAPI(
    title="Pegasus AI",
    version="0.1.0"
)

app.include_router(horse_router, prefix="/api/v1")
app.include_router(intelligence_router, prefix="/api/v1")
app.include_router(race_router, prefix="/api/v1")
app.include_router(track_router, prefix="/api/v1")
app.include_router(people_router, prefix="/api/v1")
app.include_router(crawler_router, prefix="/api/v1")
app.include_router(tjk_router, prefix="/api/v1")


@app.get("/")
def root():
    return {
        "project": "Pegasus AI",
        "status": "running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


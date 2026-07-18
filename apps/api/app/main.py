from fastapi import FastAPI

from app.api.v1.horses import router as horse_router
from app.api.v1.races import router as race_router

app = FastAPI(
    title="Pegasus AI",
    version="0.1.0"
)

app.include_router(horse_router, prefix="/api/v1")
app.include_router(race_router, prefix="/api/v1")


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
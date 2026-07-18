from fastapi import APIRouter

router = APIRouter(
    prefix="/races",
    tags=["Races"],
)


@router.get("/")
def get_races():
    return {
        "items": [],
        "count": 0,
    }
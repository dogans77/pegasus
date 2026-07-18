from fastapi import APIRouter

router = APIRouter(
    prefix="/horses",
    tags=["Horses"]
)


@router.get("/")
def get_horses():
    return {
        "items": [],
        "count": 0
    }
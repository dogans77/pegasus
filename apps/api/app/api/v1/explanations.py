from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.explainability import explain_race

router = APIRouter(prefix='/explanations', tags=['Explainability'])


@router.get('/races/{race_id}')
def get_race_explanation(race_id: int, db: Session = Depends(get_db)):
    try:
        return explain_race(db, race_id)
    except LookupError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
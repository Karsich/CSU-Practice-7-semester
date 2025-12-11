"""
Основные роуты системы
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from core.database import get_db
from core import schemas
from core.models import Stop

router = APIRouter()


@router.get("/stops/{stop_id}", response_model=schemas.Stop)
async def get_stop(stop_id: int, db: Session = Depends(get_db)):
    """Получение информации об остановке"""
    stop = db.query(Stop).filter(Stop.id == stop_id).first()
    if not stop:
        raise HTTPException(status_code=404, detail="Остановка не найдена")
    return stop


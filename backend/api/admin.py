"""
API для администраторов (управление остановками)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from core.database import get_db
from core import schemas
from core.models import Stop

router = APIRouter()


@router.post("/stops", response_model=schemas.Stop)
async def create_stop(stop: schemas.StopCreate, db: Session = Depends(get_db)):
    """Создание новой остановки"""
    db_stop = Stop(**stop.dict())
    db.add(db_stop)
    db.commit()
    db.refresh(db_stop)
    return db_stop


@router.get("/stops", response_model=List[schemas.Stop])
async def get_stops(db: Session = Depends(get_db)):
    """Получение списка всех остановок"""
    stops = db.query(Stop).filter(Stop.is_active == True).all()
    return stops


@router.get("/stops/{stop_id}", response_model=schemas.Stop)
async def get_stop(stop_id: int, db: Session = Depends(get_db)):
    """Получение информации об остановке"""
    stop = db.query(Stop).filter(Stop.id == stop_id).first()
    if not stop:
        raise HTTPException(status_code=404, detail="Остановка не найдена")
    return stop


@router.put("/stops/{stop_id}", response_model=schemas.Stop)
async def update_stop(
    stop_id: int,
    stop_update: schemas.StopBase,
    db: Session = Depends(get_db)
):
    """Обновление информации об остановке"""
    stop = db.query(Stop).filter(Stop.id == stop_id).first()
    if not stop:
        raise HTTPException(status_code=404, detail="Остановка не найдена")
    
    for key, value in stop_update.dict(exclude_unset=True).items():
        setattr(stop, key, value)
    
    db.commit()
    db.refresh(stop)
    return stop


"""
Основные роуты системы
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from core.database import get_db
from core import schemas
from core.models import Route, Stop, Bus

router = APIRouter()


@router.get("/routes", response_model=List[schemas.Route])
async def get_routes(db: Session = Depends(get_db)):
    """Получение списка всех маршрутов"""
    routes = db.query(Route).filter(Route.is_active == True).all()
    return routes


@router.get("/routes/{route_id}", response_model=schemas.Route)
async def get_route(route_id: int, db: Session = Depends(get_db)):
    """Получение информации о маршруте"""
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Маршрут не найден")
    return route


@router.get("/stops/{stop_id}", response_model=schemas.Stop)
async def get_stop(stop_id: int, db: Session = Depends(get_db)):
    """Получение информации об остановке"""
    stop = db.query(Stop).filter(Stop.id == stop_id).first()
    if not stop:
        raise HTTPException(status_code=404, detail="Остановка не найдена")
    return stop


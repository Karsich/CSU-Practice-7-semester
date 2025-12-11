"""
API для администраторов (управление маршрутами, остановками)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from core.database import get_db
from core import schemas
from core.models import Route, Stop, Bus

router = APIRouter()


@router.post("/routes", response_model=schemas.Route)
async def create_route(route: schemas.RouteCreate, db: Session = Depends(get_db)):
    """Создание нового маршрута"""
    db_route = Route(**route.dict())
    db.add(db_route)
    db.commit()
    db.refresh(db_route)
    return db_route


@router.post("/stops", response_model=schemas.Stop)
async def create_stop(stop: schemas.StopCreate, db: Session = Depends(get_db)):
    """Создание новой остановки"""
    # Проверка существования маршрута
    route = db.query(Route).filter(Route.id == stop.route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Маршрут не найден")
    
    db_stop = Stop(**stop.dict())
    db.add(db_stop)
    db.commit()
    db.refresh(db_stop)
    return db_stop


@router.post("/buses", response_model=schemas.Bus)
async def create_bus(bus: schemas.BusCreate, db: Session = Depends(get_db)):
    """Добавление нового автобуса"""
    # Проверка существования маршрута
    route = db.query(Route).filter(Route.id == bus.route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Маршрут не найден")
    
    db_bus = Bus(**bus.dict())
    db.add(db_bus)
    db.commit()
    db.refresh(db_bus)
    return db_bus


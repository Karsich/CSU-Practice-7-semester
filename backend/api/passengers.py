"""
API для пассажиров
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy import func, and_

from core.database import get_db
from core import schemas
from core.models import Route, Stop, LoadData, Bus
from services.forecast_service import forecast_service

router = APIRouter()


@router.get("/current-load/{route_id}", response_model=schemas.CurrentLoadResponse)
async def get_current_load(
    route_id: int,
    stop_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Получение текущей загруженности маршрута"""
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Маршрут не найден")
    
    # Получение последних данных о загруженности
    query = db.query(LoadData).filter(
        and_(
            LoadData.route_id == route_id,
            LoadData.timestamp >= datetime.now() - timedelta(minutes=10)
        )
    )
    
    if stop_id:
        query = query.filter(LoadData.stop_id == stop_id)
    
    latest_data = query.order_by(LoadData.timestamp.desc()).first()
    
    if not latest_data:
        # Если нет данных, возвращаем пустое значение
        load_percentage = 0.0
        people_count = 0
    else:
        load_percentage = latest_data.load_percentage
        people_count = latest_data.people_count
    
    # Определение статуса
    load_status = forecast_service.get_current_load_status(load_percentage)
    
    # Получение информации об остановке
    stop_name = "Общая"
    if stop_id:
        stop = db.query(Stop).filter(Stop.id == stop_id).first()
        if stop:
            stop_name = stop.name
    
    # Получение информации о ближайших автобусах
    buses = db.query(Bus).filter(
        and_(
            Bus.route_id == route_id,
            Bus.is_active == True,
            Bus.last_seen >= datetime.now() - timedelta(minutes=30)
        )
    ).all()
    
    next_buses = []
    for bus in buses[:5]:  # Ближайшие 5 автобусов
        next_buses.append({
            'id': bus.id,
            'vehicle_number': bus.vehicle_number,
            'current_load': bus.current_load,
            'load_percentage': (bus.current_load / bus.max_capacity) * 100 if bus.max_capacity > 0 else 0,
            'load_status': forecast_service.get_current_load_status(
                (bus.current_load / bus.max_capacity) * 100 if bus.max_capacity > 0 else 0
            )
        })
    
    return schemas.CurrentLoadResponse(
        route_id=route_id,
        route_number=route.number,
        stop_id=stop_id or 0,
        stop_name=stop_name,
        current_load=people_count,
        load_percentage=load_percentage,
        load_status=load_status,
        updated_at=latest_data.timestamp if latest_data else datetime.now(),
        next_buses=next_buses
    )


@router.get("/forecast/{route_id}", response_model=List[schemas.ForecastResponse])
async def get_forecast(
    route_id: int,
    stop_id: Optional[int] = None,
    hours: int = 24,
    db: Session = Depends(get_db)
):
    """Получение прогноза загруженности"""
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Маршрут не найден")
    
    forecast_result = forecast_service.forecast_load(db, route_id, stop_id, hours)
    
    if forecast_result.get('error'):
        raise HTTPException(status_code=400, detail=forecast_result['error'])
    
    forecasts = []
    for item in forecast_result['forecast']:
        forecasts.append(schemas.ForecastResponse(
            route_id=route_id,
            stop_id=stop_id,
            forecast_time=item['timestamp'],
            predicted_load=item['predicted_load'],
            confidence_interval_lower=item.get('lower_bound'),
            confidence_interval_upper=item.get('upper_bound')
        ))
    
    return forecasts


@router.get("/routes/{route_id}/stops", response_model=List[schemas.Stop])
async def get_route_stops(route_id: int, db: Session = Depends(get_db)):
    """Получение списка остановок маршрута"""
    stops = db.query(Stop).filter(
        and_(Stop.route_id == route_id, Stop.is_active == True)
    ).order_by(Stop.id).all()
    return stops


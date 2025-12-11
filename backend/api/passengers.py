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
from core.models import Stop, LoadData, BusDetection
from services.forecast_service import forecast_service

router = APIRouter()


@router.get("/current-load/{stop_id}", response_model=schemas.CurrentLoadResponse)
async def get_current_load(
    stop_id: int,
    db: Session = Depends(get_db)
):
    """Получение текущей загруженности остановки"""
    stop = db.query(Stop).filter(Stop.id == stop_id).first()
    if not stop:
        raise HTTPException(status_code=404, detail="Остановка не найдена")
    
    # Получение последних данных о загруженности
    latest_data = db.query(LoadData).filter(
        and_(
            LoadData.stop_id == stop_id,
            LoadData.timestamp >= datetime.now() - timedelta(minutes=10)
        )
    ).order_by(LoadData.timestamp.desc()).first()
    
    if not latest_data:
        # Если нет данных, возвращаем пустое значение
        people_count = 0
        buses_detected = 0
    else:
        people_count = latest_data.people_count
        buses_detected = latest_data.buses_detected
    
    # Определение статуса загруженности
    if people_count == 0:
        load_status = "free"
    elif people_count < 10:
        load_status = "medium"
    else:
        load_status = "crowded"
    
    # Получение информации о недавно обнаруженных автобусах
    recent_buses = db.query(BusDetection).filter(
        and_(
            BusDetection.stop_id == stop_id,
            BusDetection.detected_at >= datetime.now() - timedelta(minutes=30)
        )
    ).order_by(BusDetection.detected_at.desc()).limit(5).all()
    
    recent_buses_list = []
    for bus_det in recent_buses:
        recent_buses_list.append({
            'bus_number': bus_det.bus_number,
            'detected_at': bus_det.detected_at.isoformat(),
            'confidence': bus_det.confidence
        })
    
    return schemas.CurrentLoadResponse(
        stop_id=stop_id,
        stop_name=stop.name,
        people_count=people_count,
        buses_detected=buses_detected,
        load_status=load_status,
        updated_at=latest_data.timestamp if latest_data else datetime.now(),
        recent_buses=recent_buses_list
    )


@router.get("/forecast/{stop_id}", response_model=List[schemas.ForecastResponse])
async def get_forecast(
    stop_id: int,
    hours: int = 24,
    db: Session = Depends(get_db)
):
    """Получение прогноза загруженности остановки"""
    stop = db.query(Stop).filter(Stop.id == stop_id).first()
    if not stop:
        raise HTTPException(status_code=404, detail="Остановка не найдена")
    
    forecast_result = forecast_service.forecast_load(db, None, stop_id, hours)
    
    if forecast_result.get('error'):
        raise HTTPException(status_code=400, detail=forecast_result['error'])
    
    forecasts = []
    for item in forecast_result['forecast']:
        forecasts.append(schemas.ForecastResponse(
            stop_id=stop_id,
            forecast_time=item['timestamp'],
            predicted_people_count=item['predicted_load'],
            confidence_interval_lower=item.get('lower_bound'),
            confidence_interval_upper=item.get('upper_bound')
        ))
    
    return forecasts


@router.get("/stops", response_model=List[schemas.Stop])
async def get_stops(db: Session = Depends(get_db)):
    """Получение списка всех остановок"""
    stops = db.query(Stop).filter(Stop.is_active == True).all()
    return stops


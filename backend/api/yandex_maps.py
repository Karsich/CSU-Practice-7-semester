"""
API для интеграции с Яндекс.Картами
Отслеживание автобусов на остановках
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import httpx

from core.database import get_db
from core.models import Stop
from core.config import settings

router = APIRouter()

# API ключ Яндекс.Карт (должен быть в .env)
YANDEX_MAPS_API_KEY = getattr(settings, 'YANDEX_MAPS_API_KEY', None)


@router.get("/stops/{stop_id}/buses")
async def get_buses_near_stop(
    stop_id: int,
    radius: int = 500,  # Радиус поиска в метрах
    db: Session = Depends(get_db)
):
    """
    Получение информации об автобусах рядом с остановкой через Яндекс.Карты
    
    Args:
        stop_id: ID остановки
        radius: Радиус поиска в метрах (по умолчанию 500)
        
    Returns:
        Список автобусов рядом с остановкой
    """
    stop = db.query(Stop).filter(Stop.id == stop_id).first()
    if not stop:
        raise HTTPException(status_code=404, detail="Остановка не найдена")
    
    if not stop.latitude or not stop.longitude:
        raise HTTPException(status_code=400, detail="Координаты остановки не указаны")
    
    # Здесь должна быть интеграция с Яндекс.Картами API
    # Для демонстрации возвращаем данные из детекций камер
    from core.models import BusDetection
    
    recent_detections = db.query(BusDetection).filter(
        BusDetection.stop_id == stop_id,
        BusDetection.detected_at >= datetime.now() - timedelta(minutes=5)
    ).order_by(BusDetection.detected_at.desc()).all()
    
    buses = []
    for detection in recent_detections:
        buses.append({
            'bus_number': detection.bus_number,
            'detected_at': detection.detected_at.isoformat(),
            'confidence': detection.confidence,
            'source': 'camera'
        })
    
    # Если есть ссылка на Яндекс.Карты, можно попытаться получить данные оттуда
    # Это требует дополнительной настройки и API ключа
    
    return {
        'stop_id': stop_id,
        'stop_name': stop.name,
        'coordinates': {
            'latitude': stop.latitude,
            'longitude': stop.longitude
        },
        'buses': buses,
        'total': len(buses)
    }


@router.get("/stops/{stop_id}/yandex-info")
async def get_yandex_stop_info(
    stop_id: int,
    db: Session = Depends(get_db)
):
    """
    Получение информации об остановке из Яндекс.Карт
    
    Args:
        stop_id: ID остановки
        
    Returns:
        Информация об остановке из Яндекс.Карт
    """
    stop = db.query(Stop).filter(Stop.id == stop_id).first()
    if not stop:
        raise HTTPException(status_code=404, detail="Остановка не найдена")
    
    if not YANDEX_MAPS_API_KEY:
        return {
            'error': 'Yandex Maps API key not configured',
            'yandex_map_url': stop.yandex_map_url
        }
    
    # Здесь можно использовать Яндекс.Карты API для получения информации
    # Например, поиск остановок общественного транспорта рядом с координатами
    
    return {
        'stop_id': stop_id,
        'yandex_map_url': stop.yandex_map_url,
        'coordinates': {
            'latitude': stop.latitude,
            'longitude': stop.longitude
        },
        'note': 'Для полной интеграции требуется настройка Яндекс.Карты API'
    }


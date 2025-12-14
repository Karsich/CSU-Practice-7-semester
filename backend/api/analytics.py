"""
API для аналитики (диспетчеры транспортных компаний)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy import func, and_

from core.database import get_db
from core.models import Stop, LoadData

router = APIRouter()


@router.get("/load-statistics/{stop_id}")
async def get_load_statistics(
    stop_id: int,
    days: int = 7,
    db: Session = Depends(get_db)
):
    """Получение статистики загруженности остановки за период"""
    stop = db.query(Stop).filter(Stop.id == stop_id).first()
    if not stop:
        raise HTTPException(status_code=404, detail="Остановка не найдена")
    
    start_date = datetime.now() - timedelta(days=days)
    end_date = datetime.now()
    
    query = db.query(LoadData).filter(
        and_(
            LoadData.stop_id == stop_id,
            LoadData.timestamp >= start_date,
            LoadData.timestamp <= end_date
        )
    )
    
    data = query.all()
    
    # Если данных нет, возвращаем пустой список
    if not data:
        return {
            'stop_id': stop_id,
            'stop_name': stop.name,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'statistics': [],
            'message': 'Нет данных за указанный период'
        }
    
    # Агрегация по часам
    hourly_stats = {}
    for record in data:
        hour_key = record.timestamp.replace(minute=0, second=0, microsecond=0)
        if hour_key not in hourly_stats:
            hourly_stats[hour_key] = {
                'timestamp': hour_key,
                'total_people': 0,
                'total_buses': 0,
                'avg_people': 0.0,
                'count': 0
            }
        
        hourly_stats[hour_key]['total_people'] += record.people_count
        hourly_stats[hour_key]['total_buses'] += record.buses_detected
        hourly_stats[hour_key]['avg_people'] += record.people_count
        hourly_stats[hour_key]['count'] += 1
    
    # Вычисление средних значений
    statistics = []
    for hour_key in sorted(hourly_stats.keys()):
        stats = hourly_stats[hour_key]
        if stats['count'] > 0:
            stats['avg_people'] = stats['avg_people'] / stats['count']
        statistics.append(stats)
    
    return {
        'stop_id': stop_id,
        'stop_name': stop.name,
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'statistics': statistics
    }


@router.get("/peak-hours/{stop_id}")
async def get_peak_hours(
    stop_id: int,
    days: int = 7,
    db: Session = Depends(get_db)
):
    """Определение часов пиковой загруженности остановки"""
    stop = db.query(Stop).filter(Stop.id == stop_id).first()
    if not stop:
        raise HTTPException(status_code=404, detail="Остановка не найдена")
    
    start_date = datetime.now() - timedelta(days=days)
    
    query = db.query(
        func.extract('hour', LoadData.timestamp).label('hour'),
        func.avg(LoadData.people_count).label('avg_people'),
        func.avg(LoadData.buses_detected).label('avg_buses')
    ).filter(
        and_(
            LoadData.stop_id == stop_id,
            LoadData.timestamp >= start_date
        )
    )
    
    results = query.group_by('hour').order_by(func.avg(LoadData.people_count).desc()).all()
    
    # Если данных нет, возвращаем пустой список
    if not results:
        return {
            'stop_id': stop_id,
            'stop_name': stop.name,
            'period_days': days,
            'peak_hours': [],
            'message': 'Нет данных за указанный период'
        }
    
    peak_hours = []
    for hour, avg_people, avg_buses in results:
        peak_hours.append({
            'hour': int(hour),
            'average_people_count': float(avg_people),
            'average_buses_count': float(avg_buses)
        })
    
    return {
        'stop_id': stop_id,
        'stop_name': stop.name,
        'period_days': days,
        'peak_hours': peak_hours
    }


@router.get("/people-history/{stop_id}")
async def get_people_history(
    stop_id: int,
    days: int = 7,
    db: Session = Depends(get_db)
):
    """Получение истории количества людей на остановке по времени"""
    stop = db.query(Stop).filter(Stop.id == stop_id).first()
    if not stop:
        raise HTTPException(status_code=404, detail="Остановка не найдена")
    
    start_date = datetime.now() - timedelta(days=days)
    
    query = db.query(LoadData).filter(
        and_(
            LoadData.stop_id == stop_id,
            LoadData.timestamp >= start_date
        )
    ).order_by(LoadData.timestamp.asc())
    
    data = query.all()
    
    # Если данных нет, возвращаем пустой список
    if not data:
        return {
            'stop_id': stop_id,
            'stop_name': stop.name,
            'period_days': days,
            'history': [],
            'message': 'Нет данных за указанный период'
        }
    
    history = []
    for record in data:
        history.append({
            'timestamp': record.timestamp.isoformat(),
            'people_count': record.people_count,
            'buses_detected': record.buses_detected
        })
    
    return {
        'stop_id': stop_id,
        'stop_name': stop.name,
        'period_days': days,
        'history': history
    }


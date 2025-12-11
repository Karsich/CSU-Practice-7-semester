"""
API для аналитики (диспетчеры транспортных компаний)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy import func, and_

from core.database import get_db
from core.models import Route, Stop, LoadData, Bus

router = APIRouter()


@router.get("/load-statistics/{route_id}")
async def get_load_statistics(
    route_id: int,
    stop_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """Получение статистики загруженности за период"""
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Маршрут не найден")
    
    if not start_date:
        start_date = datetime.now() - timedelta(days=7)
    if not end_date:
        end_date = datetime.now()
    
    query = db.query(LoadData).filter(
        and_(
            LoadData.route_id == route_id,
            LoadData.timestamp >= start_date,
            LoadData.timestamp <= end_date
        )
    )
    
    if stop_id:
        query = query.filter(LoadData.stop_id == stop_id)
    
    data = query.all()
    
    # Агрегация по часам
    hourly_stats = {}
    for record in data:
        hour_key = record.timestamp.replace(minute=0, second=0, microsecond=0)
        if hour_key not in hourly_stats:
            hourly_stats[hour_key] = {
                'timestamp': hour_key,
                'total_people': 0,
                'total_boarding': 0,
                'total_alighting': 0,
                'avg_load': 0.0,
                'count': 0
            }
        
        hourly_stats[hour_key]['total_people'] += record.people_count
        hourly_stats[hour_key]['total_boarding'] += record.boarding_count
        hourly_stats[hour_key]['total_alighting'] += record.alighting_count
        hourly_stats[hour_key]['avg_load'] += record.load_percentage
        hourly_stats[hour_key]['count'] += 1
    
    # Вычисление средних значений
    statistics = []
    for hour_key in sorted(hourly_stats.keys()):
        stats = hourly_stats[hour_key]
        if stats['count'] > 0:
            stats['avg_load'] = stats['avg_load'] / stats['count']
        statistics.append(stats)
    
    return {
        'route_id': route_id,
        'route_number': route.number,
        'stop_id': stop_id,
        'start_date': start_date,
        'end_date': end_date,
        'statistics': statistics
    }


@router.get("/peak-hours/{route_id}")
async def get_peak_hours(
    route_id: int,
    stop_id: Optional[int] = None,
    days: int = 7,
    db: Session = Depends(get_db)
):
    """Определение часов пиковой загруженности"""
    start_date = datetime.now() - timedelta(days=days)
    
    query = db.query(
        func.extract('hour', LoadData.timestamp).label('hour'),
        func.avg(LoadData.load_percentage).label('avg_load'),
        func.avg(LoadData.people_count).label('avg_people')
    ).filter(
        and_(
            LoadData.route_id == route_id,
            LoadData.timestamp >= start_date
        )
    )
    
    if stop_id:
        query = query.filter(LoadData.stop_id == stop_id)
    
    results = query.group_by('hour').order_by(func.avg(LoadData.load_percentage).desc()).all()
    
    peak_hours = []
    for hour, avg_load, avg_people in results:
        peak_hours.append({
            'hour': int(hour),
            'average_load_percentage': float(avg_load),
            'average_people_count': float(avg_people)
        })
    
    return {
        'route_id': route_id,
        'stop_id': stop_id,
        'period_days': days,
        'peak_hours': peak_hours
    }


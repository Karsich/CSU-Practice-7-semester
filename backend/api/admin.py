"""
API для администраторов (управление остановками)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta

from core.database import get_db
from core import schemas
from core.models import Stop, LoadData
from tasks.monitoring_tasks import monitor_stop_passive_task, monitor_all_stops_passive_task

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


@router.post("/trigger-monitoring/{stop_id}")
async def trigger_monitoring(stop_id: int, db: Session = Depends(get_db)):
    """Ручной запуск задачи мониторинга для конкретной остановки"""
    stop = db.query(Stop).filter(Stop.id == stop_id).first()
    if not stop:
        raise HTTPException(status_code=404, detail="Остановка не найдена")
    
    # Проверяем конфигурацию остановки
    if not stop.is_active:
        raise HTTPException(status_code=400, detail="Остановка не активна")
    if not stop.camera_id:
        raise HTTPException(status_code=400, detail="Camera ID не настроен")
    if not stop.stop_zone_coords:
        raise HTTPException(status_code=400, detail="Зона остановки не настроена")
    
    # Запоминаем время до выполнения
    from datetime import datetime
    before_time = datetime.now()
    
    try:
        # Запускаем задачу синхронно для немедленного выполнения
        result = monitor_stop_passive_task(stop_id)
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=f"Ошибка выполнения задачи: {result['error']}")
        
        # Проверяем, что данные сохранились
        from core.models import LoadData
        after_time = datetime.now()
        saved_data = db.query(LoadData).filter(
            LoadData.stop_id == stop_id,
            LoadData.timestamp >= before_time,
            LoadData.timestamp <= after_time
        ).order_by(LoadData.timestamp.desc()).first()
        
        if not saved_data:
            raise HTTPException(
                status_code=500, 
                detail="Задача выполнилась, но данные не были сохранены в БД. Проверьте логи."
            )
        
        # Проверяем, что это не тестовая запись
        is_test = saved_data.detection_data and isinstance(saved_data.detection_data, dict) and saved_data.detection_data.get('test_data')
        if is_test:
            raise HTTPException(
                status_code=500,
                detail="Сохранена тестовая запись вместо актуальной. Проверьте код задачи."
            )
        
        return {
            "success": True,
            "stop_id": stop_id,
            "stop_name": stop.name,
            "result": result,
            "saved_data": {
                "id": saved_data.id,
                "timestamp": saved_data.timestamp.isoformat(),
                "people_count": saved_data.people_count,
                "buses_detected": saved_data.buses_detected
            },
            "message": "Задача мониторинга выполнена успешно, данные сохранены"
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        raise HTTPException(status_code=500, detail=f"Ошибка при запуске задачи: {str(e)}\n{tb}")


@router.post("/trigger-monitoring-all")
async def trigger_monitoring_all(db: Session = Depends(get_db)):
    """Ручной запуск задачи мониторинга для всех остановок"""
    try:
        # Запускаем задачу синхронно
        result = monitor_all_stops_passive_task()
        
        return {
            "success": True,
            "result": result,
            "message": "Задача мониторинга для всех остановок выполнена"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при запуске задачи: {str(e)}")


@router.get("/monitoring-status")
async def get_monitoring_status(db: Session = Depends(get_db)):
    """Получение статуса мониторинга (последние записи, активность)"""
    # Проверяем последние записи
    ten_min_ago = datetime.now() - timedelta(minutes=10)
    recent_data = db.query(LoadData).filter(
        LoadData.timestamp >= ten_min_ago
    ).order_by(LoadData.timestamp.desc()).all()
    
    # Группируем по остановкам
    stops_data = {}
    for data in recent_data:
        if data.stop_id not in stops_data:
            stops_data[data.stop_id] = []
        stops_data[data.stop_id].append({
            "timestamp": data.timestamp.isoformat(),
            "people_count": data.people_count,
            "buses_detected": data.buses_detected
        })
    
    # Проверяем активные остановки
    active_stops = db.query(Stop).filter(
        Stop.is_active == True,
        Stop.camera_id.isnot(None),
        Stop.stop_zone_coords.isnot(None)
    ).count()
    
    return {
        "recent_records_count": len(recent_data),
        "active_stops_count": active_stops,
        "stops_with_recent_data": len(stops_data),
        "last_10_minutes": {
            stop_id: records[0] if records else None
            for stop_id, records in stops_data.items()
        },
        "is_monitoring_active": len(recent_data) > 0
    }


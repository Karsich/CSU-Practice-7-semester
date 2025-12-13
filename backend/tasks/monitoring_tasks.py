"""
Celery задачи для пассивного мониторинга остановок
"""
import cv2
import numpy as np
import httpx
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from typing import Optional, Dict, List

from tasks.celery_app import celery_app
from services.cv_service import cv_service
from core.database import SessionLocal
from core.models import LoadData, Stop, BusDetection
from core.cameras import IS74_CAMERAS


@celery_app.task(name="monitor_stop_passive")
def monitor_stop_passive_task(stop_id: int):
    """
    Пассивный мониторинг остановки - получение snapshot и анализ
    
    Args:
        stop_id: ID остановки
    """
    db = SessionLocal()
    
    try:
        # Получаем информацию об остановке
        stop = db.query(Stop).filter(Stop.id == stop_id).first()
        if not stop:
            return {"error": "Stop not found"}
        
        if not stop.camera_id or stop.camera_id not in IS74_CAMERAS:
            return {"error": "Camera not configured for this stop"}
        
        camera = IS74_CAMERAS[stop.camera_id]
        stop_zone_coords = stop.stop_zone_coords if stop.stop_zone_coords else None
        
        # Получаем snapshot с камеры
        snapshot_urls = [
            f"https://cdn.cams.is74.ru/snapshot?uuid={camera['uuid']}&lossy=1",
            f"https://cdn.cams.is74.ru/snapshot?uuid={camera['uuid']}",
            f"https://cdn.cams.is74.ru/snapshot/{camera['uuid']}",
        ]
        
        frame = None
        with httpx.Client(timeout=10.0) as client:
            for snapshot_url in snapshot_urls:
                try:
                    response = client.get(snapshot_url, follow_redirects=True)
                    if response.status_code == 200:
                        nparr = np.frombuffer(response.content, np.uint8)
                        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                        if frame is not None:
                            break
                except Exception:
                    continue
        
        if frame is None:
            return {"error": "Failed to get snapshot from camera"}
        
        # Обрабатываем кадр
        results = cv_service.process_video_frame(frame, stop_zone_coords)
        
        # Получаем количество людей до (последняя запись)
        last_data = db.query(LoadData).filter(
            LoadData.stop_id == stop_id
        ).order_by(LoadData.timestamp.desc()).first()
        
        people_before = last_data.people_count if last_data else 0
        
        # Сохраняем данные о количестве людей и автобусах
        load_data = LoadData(
            stop_id=stop_id,
            timestamp=datetime.now(),
            people_count=results['people_count'],
            buses_detected=results.get('buses_count', 0),
            detection_data={
                'people_detections': results.get('people_detections', []),
                'stop_zone': results.get('stop_zone'),
                'people_before': people_before
            }
        )
        db.add(load_data)
        
        # Сохраняем информацию об автобусах
        buses_info = results.get('buses', [])
        for bus_info in buses_info:
            bus_detection = BusDetection(
                stop_id=stop_id,
                bus_number=bus_info.get('bus_number'),
                detected_at=datetime.now(),
                confidence=bus_info.get('confidence', 0.0),
                bus_bbox=bus_info.get('bbox'),
                detection_data={
                    'people_before': people_before,
                    'people_after': results['people_count']
                }
            )
            db.add(bus_detection)
        
        db.commit()
        
        return {
            "stop_id": stop_id,
            "people_count": results['people_count'],
            "buses_count": results.get('buses_count', 0),
            "people_before": people_before,
            "people_after": results['people_count'],
            "buses_detected": [b.get('bus_number') for b in buses_info if b.get('bus_number')]
        }
        
    except Exception as e:
        db.rollback()
        return {"error": str(e)}
    finally:
        db.close()


@celery_app.task(name="monitor_all_stops_passive")
def monitor_all_stops_passive_task():
    """
    Пассивный мониторинг всех активных остановок
    Выполняется раз в минуту
    """
    db = SessionLocal()
    
    try:
        # Получаем все активные остановки с настроенными камерами
        stops = db.query(Stop).filter(
            Stop.is_active == True,
            Stop.camera_id.isnot(None),
            Stop.stop_zone_coords.isnot(None)
        ).all()
        
        results = []
        for stop in stops:
            try:
                result = monitor_stop_passive_task.delay(stop.id)
                results.append({
                    "stop_id": stop.id,
                    "stop_name": stop.name,
                    "task_id": result.id
                })
            except Exception as e:
                results.append({
                    "stop_id": stop.id,
                    "stop_name": stop.name,
                    "error": str(e)
                })
        
        return {
            "monitored_stops": len(results),
            "results": results
        }
        
    finally:
        db.close()


@celery_app.task(name="check_buses_from_yandex_maps")
def check_buses_from_yandex_maps_task(stop_id: int):
    """
    Проверка автобусов через Yandex Maps API
    
    Args:
        stop_id: ID остановки
    """
    db = SessionLocal()
    
    try:
        stop = db.query(Stop).filter(Stop.id == stop_id).first()
        if not stop:
            return {"error": "Stop not found"}
        
        if not stop.yandex_map_url:
            return {"error": "Yandex Map URL not configured"}
        
        # Получаем последние данные о количестве людей
        last_data = db.query(LoadData).filter(
            LoadData.stop_id == stop_id
        ).order_by(LoadData.timestamp.desc()).first()
        
        people_before = last_data.people_count if last_data else 0
        
        # TODO: Реализовать интеграцию с Yandex Maps API
        # Здесь будет запрос к Yandex Maps API для получения информации о приближающихся автобусах
        # Пока используем данные из детекций камер
        
        # Проверяем, есть ли новые автобусы (обнаруженные в последние 2 минуты)
        recent_buses = db.query(BusDetection).filter(
            BusDetection.stop_id == stop_id,
            BusDetection.detected_at >= datetime.now() - timedelta(minutes=2)
        ).order_by(BusDetection.detected_at.desc()).all()
        
        buses_info = []
        for bus_det in recent_buses:
            if bus_det.bus_number:
                buses_info.append({
                    'bus_number': bus_det.bus_number,
                    'detected_at': bus_det.detected_at.isoformat(),
                    'confidence': bus_det.confidence,
                    'people_before': bus_det.detection_data.get('people_before', 0) if bus_det.detection_data else 0,
                    'people_after': bus_det.detection_data.get('people_after', 0) if bus_det.detection_data else 0
                })
        
        return {
            "stop_id": stop_id,
            "buses": buses_info,
            "people_before": people_before,
            "message": "Using camera detections (Yandex Maps API integration pending)"
        }
        
    finally:
        db.close()


"""
Celery задачи для обработки видеопотоков
"""
import cv2
import numpy as np
from datetime import datetime
from sqlalchemy.orm import Session

from tasks.celery_app import celery_app
from services.video_processor import video_processor
from services.cv_service import cv_service
from core.database import SessionLocal
from core.models import LoadData, Stop, BusDetection


@celery_app.task(name="process_video_frame")
def process_video_frame_task(frame_data: bytes, stop_id: int):
    """
    Обработка одного кадра видеопотока
    
    Args:
        frame_data: данные кадра в формате bytes
        stop_id: ID остановки
    """
    db = SessionLocal()
    
    try:
        # Декодирование кадра
        nparr = np.frombuffer(frame_data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            return {"error": "Failed to decode frame"}
        
        # Получение информации об остановке
        stop = db.query(Stop).filter(Stop.id == stop_id).first()
        if not stop:
            return {"error": "Stop not found"}
        
        # Получение координат зоны остановки
        stop_zone_coords = stop.stop_zone_coords if stop.stop_zone_coords else None
        
        # Обработка кадра
        results = video_processor.process_frame(frame, stop_zone_coords)
        
        # Сохранение данных о количестве людей и автобусах
        load_data = LoadData(
            stop_id=stop_id,
            timestamp=datetime.now(),
            people_count=results['people_count'],
            buses_detected=results.get('buses_count', 0),
            detection_data={
                'people_detections': results.get('people_detections', []),
                'stop_zone': results.get('stop_zone')
            }
        )
        db.add(load_data)
        
        # Обработка автобусов - сохранение детекций
        for bus_info in results.get('buses', []):
            detection = BusDetection(
                stop_id=stop_id,
                bus_number=bus_info.get('bus_number'),
                detected_at=datetime.now(),
                confidence=bus_info.get('confidence'),
                bus_bbox=bus_info.get('bbox'),
                detection_data=bus_info
            )
            db.add(detection)
        
        db.commit()
        
        return {
            "success": True,
            "people_count": results['people_count'],
            "buses_detected": results.get('buses_count', 0)
        }
        
    except Exception as e:
        db.rollback()
        return {"error": str(e)}
    finally:
        db.close()


@celery_app.task(name="process_video_stream")
def process_video_stream_task(stream_url: str, stop_id: int):
    """
    Обработка видеопотока (для длительных потоков)
    
    Args:
        stream_url: URL видеопотока
        stop_id: ID остановки
    """
    # Для длительных задач можно использовать другой подход
    # Например, запуск отдельного процесса обработки
    pass


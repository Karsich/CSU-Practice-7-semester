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
from core.models import LoadData, Stop, Bus, BusDetection, Route


@celery_app.task(name="process_video_frame")
def process_video_frame_task(frame_data: bytes, stop_id: int, route_id: int):
    """
    Обработка одного кадра видеопотока
    
    Args:
        frame_data: данные кадра в формате bytes
        stop_id: ID остановки
        route_id: ID маршрута
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
        
        # Обработка кадра
        results = video_processor.process_frame(frame)
        
        # Сохранение данных о количестве людей
        load_data = LoadData(
            route_id=route_id,
            stop_id=stop_id,
            timestamp=datetime.now(),
            people_count=results['people_count'],
            boarding_count=0,  # Трекинг потребует обработки нескольких кадров
            alighting_count=0,
            load_percentage=min(100, (results['people_count'] / 30) * 100)  # Предполагаем макс. 30 человек
        )
        db.add(load_data)
        
        # Обработка автобусов
        for bus_info in results['buses']:
            # Поиск автобуса по номеру маршрута
            if bus_info.get('route_number'):
                route = db.query(Route).filter(
                    Route.number == bus_info['route_number']
                ).first()
                
                if route:
                    bus = db.query(Bus).filter(
                        Bus.route_id == route.id
                    ).first()
                    
                    if bus:
                        # Обновление последнего времени обнаружения
                        bus.last_seen = datetime.now()
                        
                        # Сохранение детекции
                        detection = BusDetection(
                            bus_id=bus.id,
                            stop_id=stop_id,
                            detected_at=datetime.now(),
                            confidence=bus_info['confidence'],
                            route_number=bus_info['route_number'],
                            detection_data=bus_info
                        )
                        db.add(detection)
        
        db.commit()
        
        return {
            "success": True,
            "people_count": results['people_count'],
            "buses_detected": len(results['buses'])
        }
        
    except Exception as e:
        db.rollback()
        return {"error": str(e)}
    finally:
        db.close()


@celery_app.task(name="process_video_stream")
def process_video_stream_task(stream_url: str, stop_id: int, route_id: int):
    """
    Обработка видеопотока (для длительных потоков)
    
    Args:
        stream_url: URL видеопотока
        stop_id: ID остановки
        route_id: ID маршрута
    """
    # Для длительных задач можно использовать другой подход
    # Например, запуск отдельного процесса обработки
    pass


"""
API для работы с компьютерным зрением
"""
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from fastapi.responses import StreamingResponse
import cv2
import numpy as np
from io import BytesIO
from PIL import Image

from services.cv_service import cv_service
from services.video_processor import video_processor
from tasks.video_tasks import process_video_frame_task

router = APIRouter()


@router.post("/detect")
async def detect_objects(file: UploadFile = File(...)):
    """
    Детекция объектов на загруженном изображении
    """
    # Чтение изображения
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if frame is None:
        raise HTTPException(status_code=400, detail="Не удалось декодировать изображение")
    
    # Детекция
    detections = cv_service.detect_objects(frame)
    
    return {
        "people_count": len(detections['people']),
        "buses_count": len(detections['buses']),
        "detections": detections
    }


@router.post("/detect-with-visualization")
async def detect_with_visualization(file: UploadFile = File(...)):
    """
    Детекция объектов с визуализацией результатов
    """
    # Чтение изображения
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if frame is None:
        raise HTTPException(status_code=400, detail="Не удалось декодировать изображение")
    
    # Детекция
    detections = cv_service.detect_objects(frame)
    
    # Отрисовка детекций
    result_frame = cv_service.draw_detections(frame, detections)
    
    # Конвертация в формат для отправки
    _, encoded_img = cv2.imencode('.jpg', result_frame)
    img_bytes = encoded_img.tobytes()
    
    return StreamingResponse(
        BytesIO(img_bytes),
        media_type="image/jpeg",
        headers={
            "people_count": str(len(detections['people'])),
            "buses_count": str(len(detections['buses']))
        }
    )


@router.post("/process-frame/{stop_id}/{route_id}")
async def process_frame_endpoint(
    stop_id: int,
    route_id: int,
    file: UploadFile = File(...)
):
    """
    Обработка кадра с сохранением результатов в БД
    """
    contents = await file.read()
    
    # Отправка задачи в Celery
    result = process_video_frame_task.delay(contents, stop_id, route_id)
    
    return {
        "task_id": result.id,
        "status": "processing"
    }


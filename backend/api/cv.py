"""
API для работы с компьютерным зрением
"""
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse, FileResponse
import cv2
import numpy as np
from io import BytesIO
from PIL import Image
import asyncio
import tempfile
import os
from typing import Optional

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


@router.post("/process-video")
async def process_video_file(
    file: UploadFile = File(...),
    save_output: bool = False
):
    """
    Обработка видеофайла с визуализацией детекций
    Возвращает обработанное видео или информацию об обработке
    """
    # Сохраняем временный файл
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
        content = await file.read()
        tmp_file.write(content)
        tmp_path = tmp_file.name
    
    try:
        # Открываем видео
        cap = cv2.VideoCapture(tmp_path)
        if not cap.isOpened():
            raise HTTPException(status_code=400, detail="Не удалось открыть видеофайл")
        
        fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        output_path = None
        frame_count = 0
        processed_count = 0
        
        if save_output:
            output_path = tmp_path.replace(".mp4", "_processed.mp4")
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        else:
            out = None
        
        # Обрабатываем каждый кадр
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_count += 1
            
            # Обрабатываем каждый кадр (можно настроить пропуск через конфиг)
            detections = cv_service.detect_objects(frame)
            result_frame = cv_service.draw_detections(frame, detections)
            
            if out:
                out.write(result_frame)
            
            processed_count += 1
        
        cap.release()
        if out:
            out.release()
        
        # Удаляем исходный временный файл
        os.unlink(tmp_path)
        
        if save_output and output_path and os.path.exists(output_path):
            return FileResponse(
                output_path,
                media_type="video/mp4",
                filename="processed_video.mp4",
                headers={
                    "X-Frames-Processed": str(processed_count),
                    "X-Total-Frames": str(total_frames)
                }
            )
        else:
            return {
                "message": "Видео обработано",
                "total_frames": total_frames,
                "frames_processed": processed_count,
                "fps": fps,
                "resolution": f"{width}x{height}",
                "note": "Используйте save_output=true для получения обработанного видео"
            }
            
    except Exception as e:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise HTTPException(status_code=500, detail=f"Ошибка обработки видео: {str(e)}")


@router.websocket("/process-video-stream")
async def process_video_stream_websocket(websocket: WebSocket):
    """
    WebSocket endpoint для обработки видео в реальном времени
    Клиент отправляет кадры, сервер возвращает обработанные кадры с визуализацией
    """
    await websocket.accept()
    
    try:
        while True:
            # Получаем данные от клиента
            data = await websocket.receive()
            
            if "bytes" in data:
                # Получаем кадр в байтах
                frame_data = data["bytes"]
            elif "text" in data:
                # Если это команда (например, "stop")
                if data["text"] == "stop":
                    break
                continue
            else:
                continue
            
            # Декодируем кадр
            nparr = np.frombuffer(frame_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is None:
                continue
            
            # Обрабатываем кадр
            detections = cv_service.detect_objects(frame)
            
            # Визуализируем детекции
            result_frame = cv_service.draw_detections(frame, detections)
            
            # Кодируем обработанный кадр
            _, encoded = cv2.imencode('.jpg', result_frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
            
            # Отправляем обратно клиенту
            await websocket.send_bytes(encoded.tobytes())
            
            # Отправляем метаданные через JSON (после изображения)
            await asyncio.sleep(0.001)  # Небольшая задержка для разделения сообщений
            await websocket.send_json({
                "people_count": len(detections['people']),
                "buses_count": len(detections['buses']),
                "cars_count": len(detections.get('cars', []))
            })
            
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"Ошибка WebSocket: {e}")
    finally:
        try:
            await websocket.close()
        except:
            pass


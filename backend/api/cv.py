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

# Конфигурация камер с сайта stream.is74.ru
IS74_CAMERAS = {
    "camera1": {
        "name": "250-летия Челябинска - Академика Макеева",
        "rtsp": "rtsp://cdn.cams.is74.ru:8554?uuid=ab7346d3-b64c-4754-a02a-96f01fd2a2fa&quality=main",
        "hls": "https://cdn.cams.is74.ru/hls/playlists/multivariant.m3u8?uuid=ab7346d3-b64c-4754-a02a-96f01fd2a2fa",
        "uuid": "ab7346d3-b64c-4754-a02a-96f01fd2a2fa"
    },
    "camera2": {
        "name": "250-летия Челябинска - Салавата Юлаева",
        "rtsp": "rtsp://cdn.cams.is74.ru:8554?uuid=0cff55c4-ba25-4976-bd39-276fcbdb054a&quality=main",
        "hls": "https://cdn.cams.is74.ru/hls/playlists/multivariant.m3u8?uuid=0cff55c4-ba25-4976-bd39-276fcbdb054a",
        "uuid": "0cff55c4-ba25-4976-bd39-276fcbdb054a"
    },
    "camera3": {
        "name": "Академика Королёва - Университетская Набережная",
        "rtsp": "rtsp://cdn.cams.is74.ru:8554?uuid=57164ea3-c4fa-45ae-b315-79544770eb36&quality=main",
        "hls": "https://cdn.cams.is74.ru/hls/playlists/multivariant.m3u8?uuid=57164ea3-c4fa-45ae-b315-79544770eb36",
        "uuid": "57164ea3-c4fa-45ae-b315-79544770eb36"
    }
}


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


@router.post("/process-frame/{stop_id}")
async def process_frame_endpoint(
    stop_id: int,
    file: UploadFile = File(...)
):
    """
    Обработка кадра с сохранением результатов в БД
    """
    contents = await file.read()
    
    # Отправка задачи в Celery
    result = process_video_frame_task.delay(contents, stop_id)
    
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


@router.get("/cameras")
async def get_available_cameras():
    """
    Получение списка доступных камер
    """
    return {
        "cameras": [
            {
                "id": cam_id,
                "name": cam_info["name"],
                "uuid": cam_info["uuid"]
            }
            for cam_id, cam_info in IS74_CAMERAS.items()
        ]
    }


@router.get("/camera/{camera_id}/stream")
async def get_camera_stream(camera_id: str, with_detection: bool = False):
    """
    Получение видеопотока с камеры
    
    Args:
        camera_id: ID камеры (camera1, camera2, camera3)
        with_detection: Включить детекцию объектов (по умолчанию False)
    """
    if camera_id not in IS74_CAMERAS:
        raise HTTPException(status_code=404, detail="Камера не найдена")
    
    camera = IS74_CAMERAS[camera_id]
    
    if with_detection:
        # Возвращаем информацию о потоке с детекцией
        return {
            "camera_id": camera_id,
            "camera_name": camera["name"],
            "stream_url": camera["rtsp"],
            "hls_url": camera["hls"],
            "detection_enabled": True,
            "note": "Используйте WebSocket эндпоинт /camera/{camera_id}/stream-ws для просмотра с детекцией"
        }
    else:
        # Возвращаем прямую ссылку на поток
        return {
            "camera_id": camera_id,
            "camera_name": camera["name"],
            "rtsp_url": camera["rtsp"],
            "hls_url": camera["hls"],
            "detection_enabled": False
        }


@router.websocket("/camera/{camera_id}/stream-ws")
async def camera_stream_websocket(websocket: WebSocket, camera_id: str, with_detection: bool = True):
    """
    WebSocket поток с камеры с возможностью детекции
    
    Args:
        camera_id: ID камеры (camera1, camera2, camera3)
        with_detection: Включить детекцию объектов
    """
    if camera_id not in IS74_CAMERAS:
        await websocket.close(code=1008, reason="Камера не найдена")
        return
    
    await websocket.accept()
    
    camera = IS74_CAMERAS[camera_id]
    stream_url = camera["rtsp"]
    
    try:
        # Открываем видеопоток
        cap = cv2.VideoCapture(stream_url)
        
        if not cap.isOpened():
            await websocket.send_json({
                "error": f"Не удалось открыть видеопоток камеры {camera_id}"
            })
            await websocket.close()
            return
        
        await websocket.send_json({
            "status": "connected",
            "camera_name": camera["name"],
            "detection_enabled": with_detection
        })
        
        frame_count = 0
        last_time = asyncio.get_event_loop().time()
        
        while True:
            ret, frame = cap.read()
            
            if not ret:
                await websocket.send_json({"error": "Ошибка чтения кадра"})
                break
            
            frame_count += 1
            
            # Обрабатываем каждый кадр или пропускаем для оптимизации
            if frame_count % 3 == 0:  # Обрабатываем каждый 3-й кадр
                if with_detection:
                    # Детекция объектов
                    detections = cv_service.detect_objects(frame)
                    result_frame = cv_service.draw_detections(frame, detections)
                else:
                    result_frame = frame
                
                # Кодируем кадр
                _, encoded = cv2.imencode('.jpg', result_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                
                # Отправляем кадр
                await websocket.send_bytes(encoded.tobytes())
                
                # Отправляем метаданные если включена детекция
                if with_detection:
                    await asyncio.sleep(0.001)
                    await websocket.send_json({
                        "people_count": len(detections['people']),
                        "buses_count": len(detections['buses']),
                        "cars_count": len(detections.get('cars', [])),
                        "frame_number": frame_count
                    })
                
                # Ограничение FPS (примерно 10 FPS)
                await asyncio.sleep(0.1)
            
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"Ошибка обработки потока камеры {camera_id}: {e}")
        try:
            await websocket.send_json({"error": str(e)})
        except:
            pass
    finally:
        if 'cap' in locals():
            cap.release()
        try:
            await websocket.close()
        except:
            pass


@router.get("/camera/{camera_id}/snapshot")
async def get_camera_snapshot(camera_id: str, with_detection: bool = False):
    """
    Получение снимка с камеры
    
    Args:
        camera_id: ID камеры
        with_detection: Включить детекцию объектов
    """
    if camera_id not in IS74_CAMERAS:
        raise HTTPException(status_code=404, detail="Камера не найдена")
    
    camera = IS74_CAMERAS[camera_id]
    
    try:
        # Получаем снимок через API
        snapshot_url = f"https://cdn.cams.is74.ru/snapshot?uuid={camera['uuid']}"
        
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(snapshot_url, timeout=10.0)
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="Не удалось получить снимок")
            
            # Декодируем изображение
            nparr = np.frombuffer(response.content, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is None:
                raise HTTPException(status_code=500, detail="Не удалось декодировать изображение")
            
            detections = None
            if with_detection:
                # Обрабатываем с детекцией
                detections = cv_service.detect_objects(frame)
                result_frame = cv_service.draw_detections(frame, detections)
            else:
                result_frame = frame
            
            # Кодируем результат
            _, encoded_img = cv2.imencode('.jpg', result_frame)
            img_bytes = encoded_img.tobytes()
            
            headers = {
                "X-Camera-Name": camera["name"]
            }
            if with_detection and detections:
                headers["X-People-Count"] = str(len(detections.get('people', [])))
                headers["X-Buses-Count"] = str(len(detections.get('buses', [])))
            
            return StreamingResponse(
                BytesIO(img_bytes),
                media_type="image/jpeg",
                headers=headers
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения снимка: {str(e)}")


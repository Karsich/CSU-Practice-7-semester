"""
API для работы с компьютерным зрением
"""
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse, FileResponse, Response
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
from core.cameras import IS74_CAMERAS

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


@router.websocket("/process-video-stream")
async def process_video_stream(websocket: WebSocket):
    """
    WebSocket для обработки видеопотока в реальном времени
    """
    await websocket.accept()
    
    try:
        while True:
            # Получаем данные от клиента
            data = await websocket.receive()
            
            frame_data = None
            if "bytes" in data:
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
                "buses_count": len(detections['buses'])
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
async def camera_stream_websocket(websocket: WebSocket, camera_id: str):
    """
    WebSocket поток с камеры с возможностью детекции
    Использует HD качество для лучшего распознавания номеров автобусов
    
    Args:
        camera_id: ID камеры (camera1, camera2, camera3)
        Query параметры:
        - with_detection: Включить детекцию объектов (по умолчанию True)
        - fps_mode: Режим FPS - "active" (8 FPS) или "passive" (1 FPS, по умолчанию)
    """
    if camera_id not in IS74_CAMERAS:
        await websocket.close(code=1008, reason="Камера не найдена")
        return
    
    # Получаем query параметры
    query_params = dict(websocket.query_params)
    with_detection = query_params.get('with_detection', 'true').lower() == 'true'
    fps_mode = query_params.get('fps_mode', 'passive').lower()
    
    await websocket.accept()
    
    camera = IS74_CAMERAS[camera_id]
    # Пытаемся использовать HD качество, если недоступно - переключаемся на main
    # Пробуем разные форматы RTSP URL и HLS как альтернативу
    stream_urls = [
        # RTSP варианты
        f"rtsp://cdn.cams.is74.ru:8554/stream?uuid={camera['uuid']}&quality=hd",
        f"rtsp://cdn.cams.is74.ru:8554/stream?uuid={camera['uuid']}&quality=main",
        f"rtsp://cdn.cams.is74.ru:8554?uuid={camera['uuid']}&quality=hd",
        f"rtsp://cdn.cams.is74.ru:8554?uuid={camera['uuid']}&quality=main",
        f"rtsp://cdn.cams.is74.ru:8554/{camera['uuid']}?quality=hd",
        camera["rtsp"],
        camera.get("rtsp_main"),
        # HLS как последняя попытка (требует специальной обработки)
        camera.get("hls"),
    ]
    
    cap = None
    stream_url = None
    
    try:
        # Пробуем разные форматы URL
        for url in stream_urls:
            if not url:
                continue
            try:
                test_cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
                test_cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Минимальный буфер для снижения задержки
                test_cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'H264'))
                
                # Даем больше времени на подключение для RTSP
                await asyncio.sleep(1.0)
                
                if test_cap.isOpened():
                    # Проверяем, что поток действительно работает
                    ret, test_frame = test_cap.read()
                    if ret and test_frame is not None and test_frame.size > 0:
                        cap = test_cap
                        stream_url = url
                        print(f"✓ Успешное подключение к камере {camera_id} через URL: {url}")
                        break
                test_cap.release()
            except Exception as e:
                print(f"Ошибка при попытке подключения к {url}: {e}")
                if 'test_cap' in locals():
                    try:
                        test_cap.release()
                    except:
                        pass
                continue
        
        if not cap or not cap.isOpened():
            await websocket.send_json({
                "error": f"Не удалось открыть видеопоток камеры {camera_id}. Попробованы все форматы URL."
            })
            await websocket.close()
            return
        
        await websocket.send_json({
            "status": "connected",
            "camera_name": camera["name"],
            "detection_enabled": with_detection
        })
        
        frame_count = 0
        last_processing_time = asyncio.get_event_loop().time()
        
        # Определяем целевой FPS в зависимости от режима
        if fps_mode == "active":
            target_fps = 8  # 8 кадров в секунду для активного просмотра (fullscreen)
        else:
            target_fps = 1  # 1 кадр в секунду для пассивного режима
        
        frame_interval = 1.0 / target_fps
        
        # Получаем FPS потока для правильной синхронизации
        stream_fps = cap.get(cv2.CAP_PROP_FPS) or 25
        frames_to_skip = max(1, int(stream_fps / target_fps))  # Сколько кадров пропускать
        
        while True:
            ret, frame = cap.read()
            
            if not ret:
                await websocket.send_json({"error": "Ошибка чтения кадра"})
                break
            
            frame_count += 1
            current_time = asyncio.get_event_loop().time()
            
            # Пропускаем кадры для достижения 2 FPS
            if frame_count % frames_to_skip != 0:
                continue
            
            # Контроль времени для точной синхронизации
            time_since_last = current_time - last_processing_time
            if time_since_last < frame_interval:
                continue
            
            last_processing_time = current_time
            
            if with_detection:
                # Детекция объектов
                detections = cv_service.detect_objects(frame)
                # Используем сглаженные значения для стабильности
                smoothed_counts = cv_service.get_smoothed_counts()
                result_frame = cv_service.draw_detections(frame, detections)
                display_counts = smoothed_counts
            else:
                result_frame = frame
                display_counts = {"people": 0, "buses": 0}
            
            # Кодируем кадр (используем качество 90 для лучшей детализации)
            _, encoded = cv2.imencode('.jpg', result_frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
            
            # Отправляем кадр
            await websocket.send_bytes(encoded.tobytes())
            
            # Отправляем метаданные если включена детекция (со сглаженными значениями)
            if with_detection:
                await asyncio.sleep(0.001)
                await websocket.send_json({
                    "people_count": display_counts['people'],
                    "buses_count": display_counts['buses'],
                    "frame_number": frame_count,
                    "raw_people": len(detections['people']),  # Сырые значения для отладки
                    "raw_buses": len(detections['buses'])
                })
            
            # Небольшая задержка для стабильности (уже контролируется через frame_interval)
            await asyncio.sleep(0.01)
            
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"Ошибка обработки потока камеры {camera_id}: {e}")
        try:
            await websocket.send_json({"error": str(e)})
        except:
            pass
    finally:
        if 'cap' in locals() and cap is not None:
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
        # Получаем снимок через API (пробуем разные варианты URL)
        snapshot_urls = [
            f"https://cdn.cams.is74.ru/snapshot?uuid={camera['uuid']}&lossy=1",
            f"https://cdn.cams.is74.ru/snapshot?uuid={camera['uuid']}",
            f"https://cdn.cams.is74.ru/snapshot/{camera['uuid']}",
        ]
        
        import httpx
        frame = None
        last_error = None
        
        async with httpx.AsyncClient() as client:
            for snapshot_url in snapshot_urls:
                try:
                    response = await client.get(snapshot_url, timeout=10.0, follow_redirects=True)
                    if response.status_code == 200:
                        # Декодируем изображение
                        nparr = np.frombuffer(response.content, np.uint8)
                        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                        if frame is not None:
                            break
                except Exception as e:
                    last_error = str(e)
                    continue
            
            if frame is None:
                raise HTTPException(
                    status_code=500, 
                    detail=f"Не удалось получить снимок с камеры {camera_id}. Попробованы все варианты URL. Последняя ошибка: {last_error}"
                )
            
            detections = None
            if with_detection:
                # Обрабатываем с детекцией
                detections = cv_service.detect_objects(frame)
                result_frame = cv_service.draw_detections(frame, detections)
            else:
                result_frame = frame
            
            # Кодируем результат
            _, encoded_img = cv2.imencode('.jpg', result_frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
            img_bytes = encoded_img.tobytes()
            
            # Заголовки без кириллицы (избегаем проблем с кодировкой)
            headers = {}
            if with_detection and detections:
                headers["X-People-Count"] = str(len(detections.get('people', [])))
                headers["X-Buses-Count"] = str(len(detections.get('buses', [])))
            
            return StreamingResponse(
                BytesIO(img_bytes),
                media_type="image/jpeg",
                headers=headers
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения снимка: {str(e)}")

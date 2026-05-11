"""
API для работы с компьютерным зрением
"""
from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Depends,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    BackgroundTasks,
    Form,
)
from fastapi.responses import StreamingResponse, FileResponse, Response
import cv2
import numpy as np
from io import BytesIO
from PIL import Image
import asyncio
import tempfile
import os
import json
import uuid
from typing import Optional

from services.cv_service import cv_service
from services.video_processor import video_processor
from tasks.video_tasks import process_video_frame_task
from core.cameras import IS74_CAMERAS
from core.database import SessionLocal
from core.models import Stop

router = APIRouter()

def _parse_zone_coords_json(raw: str):
    """
    Ожидается JSON вида: [[x1, y1], [x2, y2], ...]
    """
    try:
        data = json.loads(raw)
    except Exception:
        raise HTTPException(status_code=400, detail="stop_zone_coords_json должен быть валидным JSON")
    if data is None:
        return None
    if not isinstance(data, list):
        raise HTTPException(status_code=400, detail="stop_zone_coords_json должен быть JSON-массивом точек")
    if len(data) < 2:
        # допускаем пустое/маленькое => будет трактоваться как весь кадр
        return data
    pts = []
    for pt in data:
        if not isinstance(pt, (list, tuple)) or len(pt) < 2:
            continue
        try:
            pts.append([float(pt[0]), float(pt[1])])
        except Exception:
            continue
    return pts if pts else data

def _safe_unlink(path: str) -> None:
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


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

@router.post("/process-video-file")
async def process_video_file_endpoint(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Видеофайл (mp4/avi/...)"),
    stop_zone_coords_json: str = Form(
        ...,
        description='JSON массива точек зоны, например: [[100,200],[400,200],[400,500],[100,500]]. '
        "Если точек <2 — будет использован весь кадр.",
    ),
    original_width: Optional[int] = Form(
        None,
        description="Ширина оригинального кадра, в котором задавались координаты зоны (если нужно масштабирование)",
    ),
    original_height: Optional[int] = Form(
        None,
        description="Высота оригинального кадра, в котором задавались координаты зоны (если нужно масштабирование)",
    ),
    fps: Optional[float] = Form(
        None,
        description="Принудительный FPS для выходного файла (если не задан — берём из входного видео)",
    ),
):
    """
    Загружаете видео + задаёте координаты зоны остановки — на выходе получаете обработанное видео
    (трекинг людей в зоне, статусы ожидания и цветовая идентификация как в режиме cameras).
    """
    coords = _parse_zone_coords_json(stop_zone_coords_json)
    original_resolution = None
    if original_width and original_height and original_width > 0 and original_height > 0:
        original_resolution = {"width": int(original_width), "height": int(original_height)}

    # Сохраняем входной файл во временное хранилище
    suffix = os.path.splitext(file.filename or "")[1] or ".mp4"
    in_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    in_path = in_tmp.name
    try:
        contents = await file.read()
        in_tmp.write(contents)
    finally:
        in_tmp.close()

    # Выходной файл
    request_id = uuid.uuid4().hex
    out_mp4_path = os.path.join(tempfile.gettempdir(), f"processed_{request_id}.mp4")
    out_avi_path = os.path.join(tempfile.gettempdir(), f"processed_{request_id}.avi")

    cap = cv2.VideoCapture(in_path)
    if not cap.isOpened():
        _safe_unlink(in_path)
        raise HTTPException(status_code=400, detail="Не удалось открыть загруженное видео")

    try:
        in_fps = cap.get(cv2.CAP_PROP_FPS)
        out_fps = float(fps) if fps and fps > 0 else (float(in_fps) if in_fps and in_fps > 1e-3 else 25.0)

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        if width <= 0 or height <= 0:
            # Пробуем прочитать первый кадр для определения размера
            ret, frame0 = cap.read()
            if not ret or frame0 is None:
                raise HTTPException(status_code=400, detail="Не удалось прочитать кадры из видео")
            height, width = frame0.shape[:2]
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

        # Пишем MP4, если не вышло — AVI
        fourcc_mp4 = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(out_mp4_path, fourcc_mp4, out_fps, (width, height))
        out_path = out_mp4_path
        media_type = "video/mp4"
        if not writer.isOpened():
            try:
                writer.release()
            except Exception:
                pass
            fourcc_avi = cv2.VideoWriter_fourcc(*"MJPG")
            writer = cv2.VideoWriter(out_avi_path, fourcc_avi, out_fps, (width, height))
            out_path = out_avi_path
            media_type = "video/x-msvideo"
            if not writer.isOpened():
                raise HTTPException(status_code=500, detail="Не удалось создать выходной видеофайл (кодек недоступен)")

        # Уникальный контекст, чтобы ByteTrack/WaitingTracker не смешивался с камерами/остановками
        context_key = f"upload:{request_id}"

        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            results = video_processor.process_frame(
                frame,
                coords,
                original_resolution=original_resolution,
                context_key=context_key,
            )
            result_frame = cv_service.draw_detections(frame, results)
            writer.write(result_frame)

    finally:
        try:
            cap.release()
        except Exception:
            pass
        try:
            writer.release()
        except Exception:
            pass

    # Удаляем временные файлы после отдачи ответа
    background_tasks.add_task(_safe_unlink, in_path)
    background_tasks.add_task(_safe_unlink, out_path)

    download_name = f"processed_{os.path.splitext(file.filename or 'video')[0] or 'video'}{os.path.splitext(out_path)[1]}"
    return FileResponse(
        out_path,
        media_type=media_type,
        filename=download_name,
    )


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
        - stop_id: (опционально) ID остановки, чтобы включить зоны + ByteTrack статусы ожидания
    """
    if camera_id not in IS74_CAMERAS:
        await websocket.close(code=1008, reason="Камера не найдена")
        return
    
    # Получаем query параметры
    query_params = dict(websocket.query_params)
    with_detection = query_params.get('with_detection', 'true').lower() == 'true'
    fps_mode = query_params.get('fps_mode', 'passive').lower()
    stop_id_raw = query_params.get("stop_id")
    stop_id: Optional[int] = None
    if stop_id_raw is not None:
        try:
            stop_id = int(stop_id_raw)
        except Exception:
            stop_id = None
    
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

        # Если передан stop_id — попробуем загрузить зону/оригинальное разрешение из БД.
        # Если stop_id не задан — попробуем найти Stop по camera_id (первый активный).
        stop_zone_coords = None
        original_resolution = None
        context_key = None
        loaded_stop_id = None
        if with_detection:
            db = SessionLocal()
            try:
                stop = None
                if stop_id is not None:
                    stop = db.query(Stop).filter(Stop.id == stop_id).first()
                else:
                    stop = (
                        db.query(Stop)
                        .filter(Stop.camera_id == camera_id)
                        .filter(Stop.is_active == True)  # noqa: E712
                        .first()
                    )
                if stop and stop.stop_zone_coords:
                    stop_zone_coords = stop.stop_zone_coords
                    original_resolution = stop.original_resolution
                    loaded_stop_id = stop.id
                    context_key = f"stop:{stop.id}"
            finally:
                db.close()
        
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
                if stop_zone_coords and context_key:
                    # Полный режим: зона + ByteTrack + статусы ожидания
                    results = video_processor.process_frame(
                        frame,
                        stop_zone_coords,
                        original_resolution=original_resolution,
                        context_key=context_key,
                    )
                    result_frame = cv_service.draw_detections(frame, results)
                    display_counts = {
                        "people_waiting": int(results.get("people_waiting_count") or 0),
                        "people_in_zone": int(results.get("people_in_zone_count") or 0),
                        "buses": int(results.get("buses_count") or 0),
                    }
                    detections = results  # для raw_* в метаданных ниже
                else:
                    # Фолбэк: только детекция (как раньше)
                    detections = cv_service.detect_objects(frame)
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
                if stop_zone_coords and context_key:
                    await websocket.send_json({
                        "mode": "waiting_tracking",
                        "camera_id": camera_id,
                        "stop_id": loaded_stop_id,
                        "frame_number": frame_count,
                        "people_waiting_count": display_counts["people_waiting"],
                        "people_in_zone_count": display_counts["people_in_zone"],
                        "buses_count": display_counts["buses"],
                        "raw_tracks": len((detections.get("people_tracks") or [])),
                        "raw_waiting_tracks": len((detections.get("people_waiting_tracks") or [])),
                    })
                else:
                    await websocket.send_json({
                        "mode": "detection_only",
                        "camera_id": camera_id,
                        "frame_number": frame_count,
                        "people_count": display_counts['people'],
                        "buses_count": display_counts['buses'],
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

@router.get("/stop/{stop_id}/zone-snapshot-meta")
async def get_stop_zone_snapshot_meta(stop_id: int, with_detection: bool = True):
    '''
    Возвращает ссылку на изображение + people_count и buses_count (единый JSON для фронта)
    '''
    from core.models import Stop
    from core.database import SessionLocal
    db = SessionLocal()
    stop = db.query(Stop).filter(Stop.id == stop_id).first()
    if not stop:
        db.close()
        raise HTTPException(status_code=404, detail="Остановка не найдена")
    if not stop.camera_id or stop.camera_id not in IS74_CAMERAS:
        db.close()
        raise HTTPException(status_code=404, detail="Камера не найдена")
    if not stop.stop_zone_coords:
        db.close()
        raise HTTPException(status_code=404, detail="Не задана зона остановки")
    camera = IS74_CAMERAS[stop.camera_id]
    try:
        import httpx
        import time
        snapshot_urls = [
            f"https://cdn.cams.is74.ru/snapshot?uuid={camera['uuid']}&lossy=1",
            f"https://cdn.cams.is74.ru/snapshot?uuid={camera['uuid']}",
            f"https://cdn.cams.is74.ru/snapshot/{camera['uuid']}",
        ]
        frame = None
        last_error = None
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
            db.close()
            raise HTTPException(status_code=500, detail=f"Не удалось получить снимок с камеры {stop.camera_id}")
        # Получаем ROI зоны
        coords = stop.stop_zone_coords
        if not coords or len(coords) < 2:
            h, w = frame.shape[:2]
            x1, y1, x2, y2 = 0, 0, w, h
        else:
            x_coords = [c[0] for c in coords]
            y_coords = [c[1] for c in coords]
            x1, y1 = int(min(x_coords)), int(min(y_coords))
            x2, y2 = int(max(x_coords)), int(max(y_coords))
        zone_frame = frame[y1:y2, x1:x2]
        detections = cv_service.detect_objects(zone_frame) if with_detection else None
        people_count = len(detections.get('people', [])) if detections else 0
        buses_count = len(detections.get('buses', [])) if detections else 0
        # URL для изображения делаем с уникальным nocache=секунды, чтобы избежать кеша браузера
        url = f"/api/v1/cv/stop/{stop_id}/zone-snapshot?with_detection=true&nocache={int(time.time())}"
        db.close()
        return {
            "zone_img_url": url,
            "people_count": people_count,
            "buses_count": buses_count
        }
    except Exception as e:
        db.close()
        raise HTTPException(status_code=500, detail=f"Ошибка snapshot-meta: {str(e)}")

@router.get("/stop/{stop_id}/zone-snapshot")
async def get_stop_zone_snapshot(stop_id: int, with_detection: bool = True):
    '''
    Возвращает изображение только зоны остановки, пропущенной через детекцию
    '''
    from core.models import Stop
    from core.database import SessionLocal
    db = SessionLocal()
    stop = db.query(Stop).filter(Stop.id == stop_id).first()
    if not stop:
        db.close()
        raise HTTPException(status_code=404, detail="Остановка не найдена")
    if not stop.camera_id or stop.camera_id not in IS74_CAMERAS:
        db.close()
        raise HTTPException(status_code=404, detail="Камера не найдена")
    if not stop.stop_zone_coords:
        db.close()
        raise HTTPException(status_code=404, detail="Не задана зона остановки")
    camera = IS74_CAMERAS[stop.camera_id]
    try:
        import httpx
        snapshot_urls = [
            f"https://cdn.cams.is74.ru/snapshot?uuid={camera['uuid']}&lossy=1",
            f"https://cdn.cams.is74.ru/snapshot?uuid={camera['uuid']}",
            f"https://cdn.cams.is74.ru/snapshot/{camera['uuid']}",
        ]
        frame = None
        last_error = None
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
            db.close()
            raise HTTPException(status_code=500, detail=f"Не удалось получить снимок с камеры {stop.camera_id}")
        # Получаем ROI зоны
        coords = stop.stop_zone_coords
        if not coords or len(coords) < 2:
            h, w = frame.shape[:2]
            x1, y1, x2, y2 = 0, 0, w, h
        else:
            x_coords = [c[0] for c in coords]
            y_coords = [c[1] for c in coords]
            x1, y1 = int(min(x_coords)), int(min(y_coords))
            x2, y2 = int(max(x_coords)), int(max(y_coords))
        zone_frame = frame[y1:y2, x1:x2]
        result_frame = zone_frame
        detections = None
        if with_detection:
            detections = cv_service.detect_objects(zone_frame)
            result_frame = cv_service.draw_detections(zone_frame, detections)
        _, encoded_img = cv2.imencode('.jpg', result_frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
        img_bytes = encoded_img.tobytes()
        headers = {}
        if with_detection and detections:
            headers["X-People-Count"] = str(len(detections.get('people', [])))
            headers["X-Buses-Count"] = str(len(detections.get('buses', [])))
        db.close()
        return StreamingResponse(
            BytesIO(img_bytes),
            media_type="image/jpeg",
            headers=headers
        )
    except HTTPException:
        db.close()
        raise
    except Exception as e:
        db.close()
        raise HTTPException(status_code=500, detail=f"Ошибка получения снимка зоны: {str(e)}")

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

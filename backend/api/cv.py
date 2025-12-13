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
# Используется HD качество для лучшего распознавания номеров автобусов
# Правильный формат RTSP: rtsp://cdn.cams.is74.ru:8554?uuid=UUID&quality=hd (БЕЗ /stream)
IS74_CAMERAS = {
    "camera1": {
        "name": "250-летия Челябинска - Академика Макеева",
        "rtsp": "rtsp://cdn.cams.is74.ru:8554?uuid=ab7346d3-b64c-4754-a02a-96f01fd2a2fa&quality=hd",
        "rtsp_main": "rtsp://cdn.cams.is74.ru:8554?uuid=ab7346d3-b64c-4754-a02a-96f01fd2a2fa&quality=main",
        "hls": "https://cdn.cams.is74.ru/hls/playlists/multivariant.m3u8?uuid=ab7346d3-b64c-4754-a02a-96f01fd2a2fa",
        "uuid": "ab7346d3-b64c-4754-a02a-96f01fd2a2fa"
    },
    "camera2": {
        "name": "250-летия Челябинска - Салавата Юлаева",
        "rtsp": "rtsp://cdn.cams.is74.ru:8554?uuid=0cff55c4-ba25-4976-bd39-276fcbdb054a&quality=hd",
        "rtsp_main": "rtsp://cdn.cams.is74.ru:8554?uuid=0cff55c4-ba25-4976-bd39-276fcbdb054a&quality=main",
        "hls": "https://cdn.cams.is74.ru/hls/playlists/multivariant.m3u8?uuid=0cff55c4-ba25-4976-bd39-276fcbdb054a",
        "uuid": "0cff55c4-ba25-4976-bd39-276fcbdb054a"
    },
    "camera3": {
        "name": "Академика Королёва - Университетская Набережная",
        "rtsp": "rtsp://cdn.cams.is74.ru:8554?uuid=57164ea3-c4fa-45ae-b315-79544770eb36&quality=hd",
        "rtsp_main": "rtsp://cdn.cams.is74.ru:8554?uuid=57164ea3-c4fa-45ae-b315-79544770eb36&quality=main",
        "hls": "https://cdn.cams.is74.ru/hls/playlists/multivariant.m3u8?uuid=57164ea3-c4fa-45ae-b315-79544770eb36",
        "uuid": "57164ea3-c4fa-45ae-b315-79544770eb36"
    },
    "camera4": {
        "name": "Артиллерийская - 1й Пятилетки",
        "rtsp": "rtsp://cdn.cams.is74.ru:8554?uuid=16ee1359-be80-461d-a277-26e2f8c0ab03&quality=hd",
        "rtsp_main": "rtsp://cdn.cams.is74.ru:8554?uuid=16ee1359-be80-461d-a277-26e2f8c0ab03&quality=main",
        "hls": "https://cdn.cams.is74.ru/hls/playlists/multivariant.m3u8?uuid=16ee1359-be80-461d-a277-26e2f8c0ab03",
        "uuid": "16ee1359-be80-461d-a277-26e2f8c0ab03"
    },
    "camera5": {
        "name": "Бейвеля - Краснопольский проспект",
        "rtsp": "rtsp://cdn.cams.is74.ru:8554?uuid=683366ee-ad7f-4edb-a181-2c4bb15e78a0&quality=hd",
        "rtsp_main": "rtsp://cdn.cams.is74.ru:8554?uuid=683366ee-ad7f-4edb-a181-2c4bb15e78a0&quality=main",
        "hls": "https://cdn.cams.is74.ru/hls/playlists/multivariant.m3u8?uuid=683366ee-ad7f-4edb-a181-2c4bb15e78a0",
        "uuid": "683366ee-ad7f-4edb-a181-2c4bb15e78a0"
    },
    "camera6": {
        "name": "Бейвеля - Скульптора Головницкого",
        "rtsp": "rtsp://cdn.cams.is74.ru:8554?uuid=30bb3006-25af-44be-9a27-3e3ec3e178f2&quality=hd",
        "rtsp_main": "rtsp://cdn.cams.is74.ru:8554?uuid=30bb3006-25af-44be-9a27-3e3ec3e178f2&quality=main",
        "hls": "https://cdn.cams.is74.ru/hls/playlists/multivariant.m3u8?uuid=30bb3006-25af-44be-9a27-3e3ec3e178f2",
        "uuid": "30bb3006-25af-44be-9a27-3e3ec3e178f2"
    },
    "camera7": {
        "name": "Блюхера - Курчатова",
        "rtsp": "rtsp://cdn.cams.is74.ru:8554?uuid=9fbcab7f-4ab8-459f-b23b-b082489f2ea7&quality=hd",
        "rtsp_main": "rtsp://cdn.cams.is74.ru:8554?uuid=9fbcab7f-4ab8-459f-b23b-b082489f2ea7&quality=main",
        "hls": "https://cdn.cams.is74.ru/hls/playlists/multivariant.m3u8?uuid=9fbcab7f-4ab8-459f-b23b-b082489f2ea7",
        "uuid": "9fbcab7f-4ab8-459f-b23b-b082489f2ea7"
    },
    "camera8": {
        "name": "Братьев Кашириных - 40 лет Победы",
        "rtsp": "rtsp://cdn.cams.is74.ru:8554?uuid=646a8bb7-dd24-4a70-94fd-65fede465c30&quality=hd",
        "rtsp_main": "rtsp://cdn.cams.is74.ru:8554?uuid=646a8bb7-dd24-4a70-94fd-65fede465c30&quality=main",
        "hls": "https://cdn.cams.is74.ru/hls/playlists/multivariant.m3u8?uuid=646a8bb7-dd24-4a70-94fd-65fede465c30",
        "uuid": "646a8bb7-dd24-4a70-94fd-65fede465c30"
    },
    "camera9": {
        "name": "Братьев Кашириных - Академика Королева",
        "rtsp": "rtsp://cdn.cams.is74.ru:8554?uuid=1f3563e8-d978-4caf-a0bc-b1932aa99ba4&quality=hd",
        "rtsp_main": "rtsp://cdn.cams.is74.ru:8554?uuid=1f3563e8-d978-4caf-a0bc-b1932aa99ba4&quality=main",
        "hls": "https://cdn.cams.is74.ru/hls/playlists/multivariant.m3u8?uuid=1f3563e8-d978-4caf-a0bc-b1932aa99ba4",
        "uuid": "1f3563e8-d978-4caf-a0bc-b1932aa99ba4"
    },
    "camera10": {
        "name": "Братьев Кашириных - Каслинская",
        "rtsp": "rtsp://cdn.cams.is74.ru:8554?uuid=ecd5dec1-e571-4a9c-9ace-ae7fbbabd05f&quality=hd",
        "rtsp_main": "rtsp://cdn.cams.is74.ru:8554?uuid=ecd5dec1-e571-4a9c-9ace-ae7fbbabd05f&quality=main",
        "hls": "https://cdn.cams.is74.ru/hls/playlists/multivariant.m3u8?uuid=ecd5dec1-e571-4a9c-9ace-ae7fbbabd05f",
        "uuid": "ecd5dec1-e571-4a9c-9ace-ae7fbbabd05f"
    },
    "camera11": {
        "name": "Братьев Кашириных - Косарева",
        "rtsp": "rtsp://cdn.cams.is74.ru:8554?uuid=9fa656c8-14fc-44fd-a5de-f4027aafe5ca&quality=hd",
        "rtsp_main": "rtsp://cdn.cams.is74.ru:8554?uuid=9fa656c8-14fc-44fd-a5de-f4027aafe5ca&quality=main",
        "hls": "https://cdn.cams.is74.ru/hls/playlists/multivariant.m3u8?uuid=9fa656c8-14fc-44fd-a5de-f4027aafe5ca",
        "uuid": "9fa656c8-14fc-44fd-a5de-f4027aafe5ca"
    },
    "camera12": {
        "name": "Братьев Кашириных - Салавата Юлаева",
        "rtsp": "rtsp://cdn.cams.is74.ru:8554?uuid=f0674d33-27ad-474b-adb9-94a7629b9989&quality=hd",
        "rtsp_main": "rtsp://cdn.cams.is74.ru:8554?uuid=f0674d33-27ad-474b-adb9-94a7629b9989&quality=main",
        "hls": "https://cdn.cams.is74.ru/hls/playlists/multivariant.m3u8?uuid=f0674d33-27ad-474b-adb9-94a7629b9989",
        "uuid": "f0674d33-27ad-474b-adb9-94a7629b9989"
    },
    "camera13": {
        "name": "Бульвар Славы",
        "rtsp": "rtsp://cdn.cams.is74.ru:8554?uuid=5ee19d52-94b2-4bb7-94a0-14bbc7e4f181&quality=hd",
        "rtsp_main": "rtsp://cdn.cams.is74.ru:8554?uuid=5ee19d52-94b2-4bb7-94a0-14bbc7e4f181&quality=main",
        "hls": "https://cdn.cams.is74.ru/hls/playlists/multivariant.m3u8?uuid=5ee19d52-94b2-4bb7-94a0-14bbc7e4f181",
        "uuid": "5ee19d52-94b2-4bb7-94a0-14bbc7e4f181"
    },
    "camera14": {
        "name": "Воровского - Курчатова",
        "rtsp": "rtsp://cdn.cams.is74.ru:8554?uuid=f205cf9d-a922-4a06-b5d5-46b0acf078cb&quality=hd",
        "rtsp_main": "rtsp://cdn.cams.is74.ru:8554?uuid=f205cf9d-a922-4a06-b5d5-46b0acf078cb&quality=main",
        "hls": "https://cdn.cams.is74.ru/hls/playlists/multivariant.m3u8?uuid=f205cf9d-a922-4a06-b5d5-46b0acf078cb",
        "uuid": "f205cf9d-a922-4a06-b5d5-46b0acf078cb"
    },
    "camera15": {
        "name": "Воровского - Сони Кривой",
        "rtsp": "rtsp://cdn.cams.is74.ru:8554?uuid=4ea52ccb-ddbb-4789-b563-cec04a5b1d67&quality=hd",
        "rtsp_main": "rtsp://cdn.cams.is74.ru:8554?uuid=4ea52ccb-ddbb-4789-b563-cec04a5b1d67&quality=main",
        "hls": "https://cdn.cams.is74.ru/hls/playlists/multivariant.m3u8?uuid=4ea52ccb-ddbb-4789-b563-cec04a5b1d67",
        "uuid": "4ea52ccb-ddbb-4789-b563-cec04a5b1d67"
    },
    "camera16": {
        "name": "Гагарина - Дзержинского",
        "rtsp": "rtsp://cdn.cams.is74.ru:8554?uuid=e30b6791-df24-485e-90cb-4e987ef336d2&quality=hd",
        "rtsp_main": "rtsp://cdn.cams.is74.ru:8554?uuid=e30b6791-df24-485e-90cb-4e987ef336d2&quality=main",
        "hls": "https://cdn.cams.is74.ru/hls/playlists/multivariant.m3u8?uuid=e30b6791-df24-485e-90cb-4e987ef336d2",
        "uuid": "e30b6791-df24-485e-90cb-4e987ef336d2"
    },
    "camera17": {
        "name": "Гагарина - Руставели",
        "rtsp": "rtsp://cdn.cams.is74.ru:8554?uuid=7f3d95d0-39c4-4ff4-ac5a-07649eeca6e6&quality=hd",
        "rtsp_main": "rtsp://cdn.cams.is74.ru:8554?uuid=7f3d95d0-39c4-4ff4-ac5a-07649eeca6e6&quality=main",
        "hls": "https://cdn.cams.is74.ru/hls/playlists/multivariant.m3u8?uuid=7f3d95d0-39c4-4ff4-ac5a-07649eeca6e6",
        "uuid": "7f3d95d0-39c4-4ff4-ac5a-07649eeca6e6"
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
async def camera_stream_websocket(websocket: WebSocket, camera_id: str, with_detection: bool = True):
    """
    WebSocket поток с камеры с возможностью детекции
    Использует HD качество для лучшего распознавания номеров автобусов
    
    Args:
        camera_id: ID камеры (camera1, camera2, camera3)
        with_detection: Включить детекцию объектов
    """
    if camera_id not in IS74_CAMERAS:
        await websocket.close(code=1008, reason="Камера не найдена")
        return
    
    await websocket.accept()
    
    camera = IS74_CAMERAS[camera_id]
    # Пытаемся использовать HD качество, если недоступно - переключаемся на main
    # Пробуем разные форматы RTSP URL (проверено: правильный формат без /stream)
    stream_urls = [
        f"rtsp://cdn.cams.is74.ru:8554?uuid={camera['uuid']}&quality=hd",  # Правильный формат (без /stream)
        f"rtsp://cdn.cams.is74.ru:8554?uuid={camera['uuid']}&quality=main",  # Main качество
        camera["rtsp"],  # HD качество с /stream (резерв)
        camera.get("rtsp_main"),  # Main качество с /stream (резерв)
    ]
    
    cap = None
    stream_url = None
    
    try:
        # Пробуем разные форматы URL
        for url in stream_urls:
            if not url:
                continue
            test_cap = cv2.VideoCapture(url)
            test_cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Минимальный буфер для снижения задержки
            
            # Даем время на подключение
            await asyncio.sleep(0.5)
            
            if test_cap.isOpened():
                # Проверяем, что поток действительно работает
                ret, test_frame = test_cap.read()
                if ret and test_frame is not None:
                    cap = test_cap
                    stream_url = url
                    break
            test_cap.release()
        
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
        target_fps = 2  # 2 кадра в секунду для синхронизации
        frame_interval = 1.0 / target_fps  # 0.5 секунды между кадрами
        
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
            
            # Проверяем, прошло ли достаточно времени с последней обработки
            time_since_last = current_time - last_processing_time
            if time_since_last < frame_interval:
                # Пропускаем кадр, если еще не прошло 0.5 секунды
                continue
            
            last_processing_time = current_time
            
            if with_detection:
                # Детекция объектов (HD качество улучшает распознавание номеров)
                detections = cv_service.detect_objects(frame)
                
                # Получаем сглаженные значения для стабильности
                smoothed_counts = cv_service.get_smoothed_counts()
                
                result_frame = cv_service.draw_detections(frame, detections)
                
                # Используем сглаженные значения для отображения
                display_counts = smoothed_counts
            else:
                result_frame = frame
                display_counts = {"people": 0, "buses": 0}
            
            # Кодируем кадр с высоким качеством для HD потоков
            # Используем качество 90 для лучшей детализации (важно для распознавания номеров)
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
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения снимка: {str(e)}")


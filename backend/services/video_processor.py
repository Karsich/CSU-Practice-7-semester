"""
Сервис обработки видеопотоков
"""
import cv2
import asyncio
from typing import Optional, Callable, Dict
from datetime import datetime
import numpy as np

from services.cv_service import cv_service
from core.config import settings


class VideoProcessor:
    """Сервис для обработки видеопотоков с камер"""
    
    def __init__(self):
        self.frame_skip = settings.FRAME_SKIP
        self.max_fps = settings.MAX_FRAMES_PER_SECOND
        self.is_processing = False
    
    async def process_stream(
        self,
        stream_url: str,
        stop_zone: Optional[tuple] = None,
        callback: Optional[Callable] = None
    ):
        """
        Асинхронная обработка видеопотока
        
        Args:
            stream_url: URL видеопотока или путь к файлу
            stop_zone: координаты зоны остановки (x1, y1, x2, y2)
            callback: функция обратного вызова для обработки результатов
        """
        cap = cv2.VideoCapture(stream_url)
        
        if not cap.isOpened():
            raise ValueError(f"Не удалось открыть видеопоток: {stream_url}")
        
        self.is_processing = True
        frame_count = 0
        
        try:
            while self.is_processing:
                ret, frame = cap.read()
                
                if not ret:
                    break
                
                # Пропуск кадров для оптимизации
                if frame_count % self.frame_skip != 0:
                    frame_count += 1
                    continue
                
                # Обработка кадра
                results = cv_service.process_video_frame(frame, stop_zone)
                
                if callback:
                    await callback(results)
                
                # Ограничение FPS
                await asyncio.sleep(1.0 / self.max_fps)
                frame_count += 1
                
        finally:
            cap.release()
            self.is_processing = False
    
    def process_frame(self, frame: np.ndarray, stop_zone: Optional[tuple] = None) -> Dict:
        """
        Синхронная обработка одного кадра
        
        Args:
            frame: кадр изображения
            stop_zone: координаты зоны остановки
            
        Returns:
            Результаты обработки
        """
        return cv_service.process_video_frame(frame, stop_zone)
    
    def stop_processing(self):
        """Остановка обработки видеопотока"""
        self.is_processing = False


# Глобальный экземпляр процессора
video_processor = VideoProcessor()


"""
Сервис компьютерного зрения на базе YOLO
Обеспечивает детекцию людей, автобусов и распознавание номеров маршрутов
"""
import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from ultralytics import YOLO
import torch

from core.config import settings


class CVService:
    """Сервис для обработки видеокадров с помощью YOLO"""
    
    def __init__(self):
        """Инициализация моделей YOLO"""
        self.model = YOLO(settings.YOLO_MODEL_PATH)
        self.confidence_threshold = settings.CONFIDENCE_THRESHOLD
        
        # COCO классы YOLO: 0 - person, 2 - car, 5 - bus, 7 - truck
        self.person_class = 0
        self.bus_class = 5
        self.car_class = 2
        self.truck_class = 7
        
        # Для трекинга объектов между кадрами
        self.tracker = None
        
    def detect_objects(self, frame: np.ndarray) -> Dict:
        """
        Детекция объектов на кадре
        
        Args:
            frame: numpy array изображения в формате BGR
            
        Returns:
            Словарь с результатами детекции
        """
        # Запуск детекции
        results = self.model(frame, conf=self.confidence_threshold, verbose=False)
        
        detections = {
            'people': [],
            'buses': [],
            'cars': [],
            'timestamp': datetime.now(),
            'frame_shape': frame.shape
        }
        
        if len(results) > 0:
            result = results[0]
            
            # Извлечение боксов, классов и уверенностей
            boxes = result.boxes
            if boxes is not None:
                for box in boxes:
                    cls = int(box.cls[0])
                    conf = float(box.conf[0])
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    
                    detection = {
                        'bbox': [float(x1), float(y1), float(x2), float(y2)],
                        'confidence': conf,
                        'class_id': cls
                    }
                    
                    if cls == self.person_class:
                        detections['people'].append(detection)
                    elif cls == self.bus_class:
                        detections['buses'].append(detection)
                    elif cls in [self.car_class, self.truck_class]:
                        detections['cars'].append(detection)
        
        return detections
    
    def count_people_in_zone(self, frame: np.ndarray, zone: Optional[Tuple[int, int, int, int]] = None) -> int:
        """
        Подсчет людей в заданной зоне
        
        Args:
            frame: кадр изображения
            zone: координаты зоны (x1, y1, x2, y2) или None для всего кадра
            
        Returns:
            Количество людей
        """
        detections = self.detect_objects(frame)
        
        if zone is None:
            return len(detections['people'])
        
        x1_zone, y1_zone, x2_zone, y2_zone = zone
        count = 0
        
        for person in detections['people']:
            x1, y1, x2, y2 = person['bbox']
            # Проверка пересечения с зоной
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2
            
            if (x1_zone <= center_x <= x2_zone and y1_zone <= center_y <= y2_zone):
                count += 1
        
        return count
    
    def detect_buses(self, frame: np.ndarray) -> List[Dict]:
        """
        Детекция автобусов на кадре
        
        Args:
            frame: кадр изображения
            
        Returns:
            Список детекций автобусов
        """
        detections = self.detect_objects(frame)
        return detections['buses']
    
    def recognize_route_number(self, frame: np.ndarray, bus_bbox: Tuple[int, int, int, int]) -> Optional[str]:
        """
        Распознавание номера маршрута на автобусе
        
        Args:
            frame: кадр изображения
            bus_bbox: координаты автобуса (x1, y1, x2, y2)
            
        Returns:
            Распознанный номер маршрута или None
        """
        x1, y1, x2, y2 = map(int, bus_bbox)
        
        # Извлечение области автобуса
        bus_roi = frame[y1:y2, x1:x2]
        
        if bus_roi.size == 0:
            return None
        
        # Увеличение контрастности для лучшего распознавания
        gray = cv2.cvtColor(bus_roi, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        # Здесь можно добавить OCR (например, Tesseract или EasyOCR)
        # Для демонстрации возвращаем None
        # В реальной системе здесь бы была интеграция с OCR
        
        # Пример: можно использовать дополнительную YOLO модель для детекции номеров
        # или OCR библиотеку типа pytesseract
        
        return None
    
    def process_video_frame(self, frame: np.ndarray, stop_zone: Optional[Tuple] = None) -> Dict:
        """
        Обработка кадра видеопотока
        
        Args:
            frame: кадр изображения
            stop_zone: координаты зоны остановки для подсчета людей
            
        Returns:
            Результаты обработки
        """
        detections = self.detect_objects(frame)
        
        # Подсчет людей в зоне остановки
        people_in_stop = self.count_people_in_zone(frame, stop_zone) if stop_zone else len(detections['people'])
        
        # Обработка автобусов
        buses_info = []
        for bus_det in detections['buses']:
            route_number = self.recognize_route_number(frame, bus_det['bbox'])
            buses_info.append({
                'bbox': bus_det['bbox'],
                'confidence': bus_det['confidence'],
                'route_number': route_number
            })
        
        return {
            'timestamp': datetime.now(),
            'people_count': people_in_stop,
            'people_detections': detections['people'],
            'buses': buses_info,
            'total_detections': len(detections['people']) + len(detections['buses'])
        }
    
    def draw_detections(self, frame: np.ndarray, detections: Dict) -> np.ndarray:
        """
        Отрисовка детекций на кадре (для визуализации)
        
        Args:
            frame: исходный кадр
            detections: результаты детекции
            
        Returns:
            Кадр с отрисованными детекциями
        """
        result_frame = frame.copy()
        
        # Отрисовка людей (зеленый)
        for person in detections.get('people', []):
            x1, y1, x2, y2 = map(int, person['bbox'])
            cv2.rectangle(result_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(result_frame, f"Person {person['confidence']:.2f}", 
                       (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # Отрисовка автобусов (синий)
        for bus in detections.get('buses', []):
            x1, y1, x2, y2 = map(int, bus['bbox'])
            cv2.rectangle(result_frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
            label = f"Bus {bus['confidence']:.2f}"
            if bus.get('route_number'):
                label += f" Route: {bus['route_number']}"
            cv2.putText(result_frame, label, (x1, y1 - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
        
        return result_frame


# Глобальный экземпляр сервиса
cv_service = CVService()


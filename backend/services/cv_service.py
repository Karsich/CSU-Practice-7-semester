"""
Сервис компьютерного зрения на базе YOLO
Обеспечивает детекцию людей, автобусов и распознавание номеров автобусов
"""
import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from ultralytics import YOLO
import torch
import re

from core.config import settings
from collections import deque

# Попытка импорта OCR библиотек
try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False


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
        
        # Инициализация OCR для распознавания номеров автобусов
        self.ocr_reader = None
        if EASYOCR_AVAILABLE:
            try:
                self.ocr_reader = easyocr.Reader(['en', 'ru'], gpu=False)
            except Exception as e:
                print(f"Не удалось инициализировать EasyOCR: {e}")
        
        # Для трекинга объектов между кадрами
        self.tracker = None
        
        # Для сглаживания результатов детекции (стабильность)
        self.detection_history = {
            'people': deque(maxlen=5),  # История последних 5 детекций
            'buses': deque(maxlen=5)
        }
        
    def detect_objects(self, frame: np.ndarray) -> Dict:
        """
        Детекция объектов на кадре
        Оптимизировано для работы с HD кадрами
        
        Args:
            frame: numpy array изображения в формате BGR
            
        Returns:
            Словарь с результатами детекции
        """
        # Для HD кадров используем большее разрешение для детекции
        # Для маленьких объектов (15x8 пикселей на 2688x1520) нужна максимальная детализация
        h, w = frame.shape[:2]
        
        # Для больших разрешений используем максимальный размер для детекции
        # Это критично для детекции маленьких объектов
        if h > 1500 or w > 2500:
            # Для очень больших разрешений используем максимальный размер
            imgsz = 1920  # Максимальный размер для лучшей детекции маленьких объектов
        elif h > 720:
            imgsz = 1280  # HD разрешение
        else:
            imgsz = 640  # Стандартное разрешение
        
        # Для маленьких объектов снижаем порог уверенности и увеличиваем детализацию
        # Используем более агрессивные настройки для детекции людей
        # Для людей используем еще более низкий порог (0.05) для детекции маленьких объектов
        results = self.model(
            frame, 
            conf=0.05,  # Очень низкий порог для детекции маленьких людей (15x8 пикселей)
            imgsz=imgsz, 
            verbose=False,
            agnostic_nms=False,  # Не объединять объекты разных классов
            max_det=500,  # Увеличиваем максимальное количество детекций для маленьких объектов
            iou=0.45  # Более строгий IoU для лучшего разделения близких объектов
        )
        
        detections = {
            'people': [],
            'buses': [],
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
                    
                    # Фильтрация по размеру для улучшения детекции маленьких объектов
                    box_width = x2 - x1
                    box_height = y2 - y1
                    box_area = box_width * box_height
                    frame_area = h * w
                    
                    detection = {
                        'bbox': [float(x1), float(y1), float(x2), float(y2)],
                        'confidence': conf,
                        'class_id': cls,
                        'area': box_area
                    }
                    
                    # Детекция только людей и автобусов (машины исключены)
                    if cls == self.person_class:
                        # Для людей используем очень низкий порог для маленьких объектов
                        # Принимаем людей даже если они очень маленькие, но с достаточной уверенностью
                        min_person_area = frame_area * 0.00005  # 0.005% от площади кадра (для людей 15x8 пикселей)
                        if box_area >= min_person_area or conf > 0.25:
                            # Дополнительная проверка: соотношение сторон должно быть разумным для человека
                            aspect_ratio = box_height / box_width if box_width > 0 else 0
                            if aspect_ratio > 0.3 and aspect_ratio < 3.0:  # Люди обычно выше, чем шире
                                detections['people'].append(detection)
                    elif cls == self.bus_class:
                        # Для автобусов минимальный размер больше
                        min_bus_area = frame_area * 0.0005  # 0.05% от площади кадра
                        if box_area >= min_bus_area or conf > 0.4:
                            detections['buses'].append(detection)
        
        # Сохраняем в историю для сглаживания
        self.detection_history['people'].append(len(detections['people']))
        self.detection_history['buses'].append(len(detections['buses']))
        
        return detections
    
    def get_smoothed_counts(self) -> Dict[str, int]:
        """
        Получение сглаженных (стабильных) значений счетчиков
        Использует медианное значение для устранения выбросов
        
        Returns:
            Словарь со сглаженными значениями
        """
        def get_median(values):
            if not values:
                return 0
            sorted_values = sorted(values)
            n = len(sorted_values)
            if n % 2 == 0:
                return int((sorted_values[n//2 - 1] + sorted_values[n//2]) / 2)
            else:
                return int(sorted_values[n//2])
        
        return {
            'people': get_median(list(self.detection_history['people'])),
            'buses': get_median(list(self.detection_history['buses']))
        }
    
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
    
    def recognize_bus_number(self, frame: np.ndarray, bus_bbox: Tuple[int, int, int, int]) -> Optional[str]:
        """
        Распознавание номера автобуса
        Оптимизировано для работы с HD кадрами - лучшее качество распознавания
        
        Args:
            frame: кадр изображения (HD качество)
            bus_bbox: координаты автобуса (x1, y1, x2, y2)
            
        Returns:
            Распознанный номер автобуса или None
        """
        x1, y1, x2, y2 = map(int, bus_bbox)
        
        # Извлечение области автобуса с небольшим отступом для лучшего распознавания
        padding = 10
        x1 = max(0, x1 - padding)
        y1 = max(0, y1 - padding)
        x2 = min(frame.shape[1], x2 + padding)
        y2 = min(frame.shape[0], y2 + padding)
        
        bus_roi = frame[y1:y2, x1:x2]
        
        if bus_roi.size == 0:
            return None
        
        # Для HD кадров можно увеличить размер области для лучшего распознавания
        h, w = bus_roi.shape[:2]
        if h < 50 or w < 50:
            # Увеличиваем маленькие области
            scale = max(2.0, 100.0 / max(h, w))
            new_h, new_w = int(h * scale), int(w * scale)
            bus_roi = cv2.resize(bus_roi, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
        
        # Увеличение контрастности для лучшего распознавания
        gray = cv2.cvtColor(bus_roi, cv2.COLOR_BGR2GRAY)
        
        # Улучшение изображения с более агрессивными настройками для HD
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        # Дополнительное улучшение резкости для HD кадров
        kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
        sharpened = cv2.filter2D(enhanced, -1, kernel)
        
        # Бинаризация для лучшего распознавания текста
        _, binary = cv2.threshold(sharpened, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Попытка распознавания через EasyOCR
        # Для HD кадров используем более высокий порог уверенности
        if self.ocr_reader is not None:
            try:
                # Используем оба варианта: бинарное и улучшенное изображение
                results_binary = self.ocr_reader.readtext(binary)
                results_enhanced = self.ocr_reader.readtext(enhanced)
                
                # Объединяем результаты
                all_results = results_binary + results_enhanced
                
                for (bbox, text, confidence) in all_results:
                    # Для HD кадров можно использовать более высокий порог
                    if confidence > 0.6:  # Повышенный порог для HD
                        # Очистка текста от лишних символов
                        cleaned_text = re.sub(r'[^0-9А-ЯA-Z]', '', text.upper())
                        if len(cleaned_text) >= 2:  # Номер должен быть минимум 2 символа
                            return cleaned_text
            except Exception as e:
                print(f"Ошибка EasyOCR: {e}")
        
        # Попытка распознавания через Tesseract
        if TESSERACT_AVAILABLE:
            try:
                text = pytesseract.image_to_string(binary, config='--psm 7 -c tessedit_char_whitelist=0123456789АБВГДЕЖЗИКЛМНОПРСТУФХЦЧШЩЭЮЯ')
                cleaned_text = re.sub(r'[^0-9А-ЯA-Z]', '', text.upper())
                if len(cleaned_text) >= 2:
                    return cleaned_text
            except Exception as e:
                print(f"Ошибка Tesseract: {e}")
        
        return None
    
    def detect_stop_zone(self, frame: np.ndarray, stop_zone_coords: Optional[List[List[float]]] = None) -> Optional[Tuple[int, int, int, int]]:
        """
        Определение зоны остановки на кадре
        
        Args:
            frame: кадр изображения
            stop_zone_coords: координаты зоны остановки в формате [[x1,y1], [x2,y2], ...]
            
        Returns:
            Координаты зоны остановки (x1, y1, x2, y2) или None
        """
        if stop_zone_coords is None or len(stop_zone_coords) < 2:
            # Если координаты не заданы, используем весь кадр
            h, w = frame.shape[:2]
            return (0, 0, w, h)
        
        # Преобразуем координаты в прямоугольник
        # Берем минимальные и максимальные значения
        x_coords = [coord[0] for coord in stop_zone_coords]
        y_coords = [coord[1] for coord in stop_zone_coords]
        
        x1 = int(min(x_coords))
        y1 = int(min(y_coords))
        x2 = int(max(x_coords))
        y2 = int(max(y_coords))
        
        return (x1, y1, x2, y2)
    
    def process_video_frame(self, frame: np.ndarray, stop_zone_coords: Optional[List[List[float]]] = None) -> Dict:
        """
        Обработка кадра видеопотока
        
        Args:
            frame: кадр изображения
            stop_zone_coords: координаты зоны остановки для подсчета людей
            
        Returns:
            Результаты обработки
        """
        detections = self.detect_objects(frame)
        
        # Определение зоны остановки
        stop_zone = self.detect_stop_zone(frame, stop_zone_coords)
        
        # Подсчет людей в зоне остановки
        people_in_stop = self.count_people_in_zone(frame, stop_zone) if stop_zone else len(detections['people'])
        
        # Обработка автобусов - распознавание номеров
        buses_info = []
        for bus_det in detections['buses']:
            bus_number = self.recognize_bus_number(frame, bus_det['bbox'])
            buses_info.append({
                'bbox': bus_det['bbox'],
                'confidence': bus_det['confidence'],
                'bus_number': bus_number
            })
        
        return {
            'timestamp': datetime.now(),
            'people_count': people_in_stop,
            'people_detections': detections['people'],
            'buses': buses_info,
            'buses_count': len(buses_info),
            'stop_zone': stop_zone,
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
                       (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        # Отрисовка автобусов (синий)
        for bus in detections.get('buses', []):
            x1, y1, x2, y2 = map(int, bus['bbox'])
            cv2.rectangle(result_frame, (x1, y1), (x2, y2), (255, 0, 0), 3)
            label = f"Bus {bus['confidence']:.2f}"
            if bus.get('bus_number'):
                label += f" №{bus['bus_number']}"
            cv2.putText(result_frame, label, (x1, y1 - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
        
        # Отрисовка зоны остановки (если задана)
        if detections.get('stop_zone'):
            x1, y1, x2, y2 = detections['stop_zone']
            cv2.rectangle(result_frame, (x1, y1), (x2, y2), (255, 255, 0), 2)
            cv2.putText(result_frame, "Stop Zone", (x1, y1 - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        
        # Добавляем статистику в левый верхний угол
        stats_y = 30
        cv2.putText(result_frame, f"People: {len(detections.get('people', []))}", 
                   (10, stats_y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(result_frame, f"Buses: {len(detections.get('buses', []))}", 
                   (10, stats_y + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
        
        return result_frame


# Глобальный экземпляр сервиса
cv_service = CVService()


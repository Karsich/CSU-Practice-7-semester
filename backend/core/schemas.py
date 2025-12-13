"""
Pydantic схемы для валидации данных
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime


# Схемы Route удалены - остановки больше не привязаны к маршрутам


class StopBase(BaseModel):
    name: str
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    camera_id: Optional[str] = None  # ID камеры (camera1, camera2, camera3)
    camera_url: Optional[str] = None  # URL видеопотока с камеры (опционально)
    yandex_map_url: Optional[str] = None  # Ссылка на Яндекс.Карты для отслеживания автобусов
    stop_zone_coords: Optional[List[List[float]]] = None  # Координаты зоны остановки на кадре
    original_resolution: Optional[Dict[str, int]] = None  # Оригинальное разрешение камеры
    is_active: bool = True


class StopCreate(StopBase):
    pass


class Stop(StopBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class BusDetectionBase(BaseModel):
    stop_id: int
    bus_number: Optional[str] = None  # Распознанный номер автобуса
    confidence: Optional[float] = None
    bus_bbox: Optional[List[float]] = None  # [x1, y1, x2, y2]
    detection_data: Optional[dict] = None


class BusDetectionCreate(BusDetectionBase):
    pass


class BusDetection(BusDetectionBase):
    id: int
    detected_at: datetime
    
    class Config:
        from_attributes = True


class LoadDataBase(BaseModel):
    stop_id: int
    timestamp: datetime
    people_count: int = 0
    buses_detected: int = 0
    detection_data: Optional[dict] = None


class LoadDataCreate(LoadDataBase):
    pass


class LoadData(LoadDataBase):
    id: int
    
    class Config:
        from_attributes = True


class CurrentLoadResponse(BaseModel):
    stop_id: int
    stop_name: str
    people_count: int
    buses_detected: int
    load_status: str  # "free", "medium", "crowded"
    updated_at: datetime
    recent_buses: List[dict] = []  # Недавно обнаруженные автобусы


class ForecastResponse(BaseModel):
    stop_id: int
    forecast_time: datetime
    predicted_people_count: float
    confidence_interval_lower: Optional[float] = None
    confidence_interval_upper: Optional[float] = None


class DetectionResult(BaseModel):
    """Результат детекции объектов на кадре"""
    frame_number: int
    timestamp: datetime
    people_count: int
    buses: List[dict] = []
    detections: List[dict] = []


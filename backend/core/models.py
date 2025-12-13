"""
Модели базы данных
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from core.database import Base


# Модель Route удалена - остановки больше не привязаны к маршрутам


class Stop(Base):
    """Модель остановки"""
    __tablename__ = "stops"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    camera_id = Column(String(100))  # ID камеры (например, camera1, camera2, camera3)
    camera_url = Column(String(500))  # URL видеопотока с камеры (опционально)
    yandex_map_url = Column(String(500))  # Ссылка на Яндекс.Карты для отслеживания автобусов
    stop_zone_coords = Column(JSON)  # Координаты зоны остановки на кадре [(x1,y1), (x2,y2), ...]
    original_resolution = Column(JSON)  # Оригинальное разрешение камеры {"width": 2688, "height": 1520}
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    load_data = relationship("LoadData", back_populates="stop")
    bus_detections = relationship("BusDetection", back_populates="stop")


class BusDetection(Base):
    """Детекции автобусов с камер на остановках"""
    __tablename__ = "bus_detections"
    
    id = Column(Integer, primary_key=True, index=True)
    stop_id = Column(Integer, ForeignKey("stops.id"), nullable=False)
    bus_number = Column(String(50))  # Распознанный номер автобуса
    detected_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    confidence = Column(Float)  # Уверенность детекции автобуса
    bus_bbox = Column(JSON)  # Координаты автобуса на кадре [x1, y1, x2, y2]
    detection_data = Column(JSON)  # Дополнительные данные детекции
    
    stop = relationship("Stop", back_populates="bus_detections")




class LoadData(Base):
    """Данные о загруженности (пассажиропоток)"""
    __tablename__ = "load_data"
    
    id = Column(Integer, primary_key=True, index=True)
    stop_id = Column(Integer, ForeignKey("stops.id"), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    people_count = Column(Integer, default=0)  # Количество людей на остановке
    buses_detected = Column(Integer, default=0)  # Количество автобусов, обнаруженных на остановке
    detection_data = Column(JSON)  # Дополнительные данные детекции
    
    stop = relationship("Stop", back_populates="load_data")


class Forecast(Base):
    """Прогнозы загруженности"""
    __tablename__ = "forecasts"
    
    id = Column(Integer, primary_key=True, index=True)
    stop_id = Column(Integer, ForeignKey("stops.id"), nullable=False)
    forecast_time = Column(DateTime(timezone=True), nullable=False, index=True)
    predicted_people_count = Column(Float, nullable=False)  # Прогнозируемое количество людей
    confidence_interval_lower = Column(Float)
    confidence_interval_upper = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    stop = relationship("Stop")


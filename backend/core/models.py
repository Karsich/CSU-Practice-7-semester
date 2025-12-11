"""
Модели базы данных
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from core.database import Base


class Route(Base):
    """Модель маршрута"""
    __tablename__ = "routes"
    
    id = Column(Integer, primary_key=True, index=True)
    number = Column(String(10), unique=True, nullable=False, index=True)
    name = Column(String(200))
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    stops = relationship("Stop", back_populates="route")
    buses = relationship("Bus", back_populates="route")
    load_data = relationship("LoadData", back_populates="route")


class Stop(Base):
    """Модель остановки"""
    __tablename__ = "stops"
    
    id = Column(Integer, primary_key=True, index=True)
    route_id = Column(Integer, ForeignKey("routes.id"), nullable=False)
    name = Column(String(200), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    camera_url = Column(String(500))  # URL видеопотока с камеры
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    route = relationship("Route", back_populates="stops")
    load_data = relationship("LoadData", back_populates="stop")


class Bus(Base):
    """Модель автобуса"""
    __tablename__ = "buses"
    
    id = Column(Integer, primary_key=True, index=True)
    route_id = Column(Integer, ForeignKey("routes.id"), nullable=False)
    vehicle_number = Column(String(50), unique=True, nullable=False)  # Номер автобуса
    license_plate = Column(String(20))  # Государственный номер
    current_load = Column(Integer, default=0)  # Текущее количество пассажиров
    max_capacity = Column(Integer, default=50)  # Максимальная вместимость
    is_active = Column(Boolean, default=True)
    last_seen = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    route = relationship("Route", back_populates="buses")
    detections = relationship("BusDetection", back_populates="bus")


class BusDetection(Base):
    """Детекции автобусов с камер"""
    __tablename__ = "bus_detections"
    
    id = Column(Integer, primary_key=True, index=True)
    bus_id = Column(Integer, ForeignKey("buses.id"), nullable=False)
    stop_id = Column(Integer, ForeignKey("stops.id"))
    detected_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    confidence = Column(Float)
    route_number = Column(String(10))  # Распознанный номер маршрута
    detection_data = Column(JSON)  # Дополнительные данные детекции
    
    bus = relationship("Bus", back_populates="detections")
    stop = relationship("Stop")


class LoadData(Base):
    """Данные о загруженности (пассажиропоток)"""
    __tablename__ = "load_data"
    
    id = Column(Integer, primary_key=True, index=True)
    route_id = Column(Integer, ForeignKey("routes.id"), nullable=False)
    stop_id = Column(Integer, ForeignKey("stops.id"), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    people_count = Column(Integer, default=0)  # Количество людей на остановке
    boarding_count = Column(Integer, default=0)  # Количество посадок
    alighting_count = Column(Integer, default=0)  # Количество высадок
    bus_load = Column(Integer, default=0)  # Загруженность автобуса
    load_percentage = Column(Float, default=0.0)  # Процент загрузки (0-100)
    
    route = relationship("Route", back_populates="load_data")
    stop = relationship("Stop", back_populates="load_data")


class Forecast(Base):
    """Прогнозы загруженности"""
    __tablename__ = "forecasts"
    
    id = Column(Integer, primary_key=True, index=True)
    route_id = Column(Integer, ForeignKey("routes.id"), nullable=False)
    stop_id = Column(Integer, ForeignKey("stops.id"))
    forecast_time = Column(DateTime(timezone=True), nullable=False, index=True)
    predicted_load = Column(Float, nullable=False)
    confidence_interval_lower = Column(Float)
    confidence_interval_upper = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    route = relationship("Route")


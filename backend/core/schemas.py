"""
Pydantic схемы для валидации данных
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class RouteBase(BaseModel):
    number: str
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: bool = True


class RouteCreate(RouteBase):
    pass


class Route(RouteBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class StopBase(BaseModel):
    route_id: int
    name: str
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    camera_url: Optional[str] = None
    is_active: bool = True


class StopCreate(StopBase):
    pass


class Stop(StopBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class BusBase(BaseModel):
    route_id: int
    vehicle_number: str
    license_plate: Optional[str] = None
    max_capacity: int = 50
    is_active: bool = True


class BusCreate(BusBase):
    pass


class Bus(BusBase):
    id: int
    current_load: int
    last_seen: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class LoadDataBase(BaseModel):
    route_id: int
    stop_id: int
    timestamp: datetime
    people_count: int = 0
    boarding_count: int = 0
    alighting_count: int = 0
    bus_load: int = 0
    load_percentage: float = 0.0


class LoadDataCreate(LoadDataBase):
    pass


class LoadData(LoadDataBase):
    id: int
    
    class Config:
        from_attributes = True


class CurrentLoadResponse(BaseModel):
    route_id: int
    route_number: str
    stop_id: int
    stop_name: str
    current_load: int
    load_percentage: float
    load_status: str  # "free", "medium", "full"
    updated_at: datetime
    next_buses: List[dict] = []


class ForecastResponse(BaseModel):
    route_id: int
    stop_id: Optional[int] = None
    forecast_time: datetime
    predicted_load: float
    confidence_interval_lower: Optional[float] = None
    confidence_interval_upper: Optional[float] = None


class DetectionResult(BaseModel):
    """Результат детекции объектов на кадре"""
    frame_number: int
    timestamp: datetime
    people_count: int
    buses: List[dict] = []
    detections: List[dict] = []


"""
Конфигурация приложения
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/transport_db"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]
    
    # YOLO Model
    YOLO_MODEL_PATH: str = "yolov8s.pt"  # Будет использоваться предобученная модель
    CONFIDENCE_THRESHOLD: float = 0.2
    
    # Video Processing
    FRAME_SKIP: int = 5  # Обрабатывать каждый 5-й кадр
    MAX_FRAMES_PER_SECOND: int = 2
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()


"""
API Gateway - единая точка входа для всех сервисов системы
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api import routes as routes_module
from api import passengers, analytics, admin, cv, yandex_maps
from core.config import settings
from core.database import engine, Base

# Создание таблиц базы данных
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Transport Load Monitoring System",
    description="Система мониторинга и прогнозирования загруженности общественного транспорта",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутов
app.include_router(routes_module.router, prefix="/api/v1", tags=["System"])
app.include_router(passengers.router, prefix="/api/v1/passengers", tags=["Passengers"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])
app.include_router(cv.router, prefix="/api/v1/cv", tags=["Computer Vision"])
app.include_router(yandex_maps.router, prefix="/api/v1/yandex", tags=["Yandex Maps"])


@app.get("/")
async def root():
    return {"message": "Transport Load Monitoring System API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


"""
Скрипт для инициализации базы данных и создания тестовых данных
"""
from sqlalchemy.orm import Session
from core.database import engine, Base, SessionLocal
from core.models import Stop
from datetime import datetime


def init_database():
    """Создание таблиц в базе данных"""
    Base.metadata.create_all(bind=engine)
    print("Таблицы базы данных созданы успешно!")


def create_test_data():
    """Создание тестовых данных"""
    db = SessionLocal()
    
    try:
        # Проверка существования данных
        existing_stops = db.query(Stop).count()
        if existing_stops > 0:
            print("Тестовые данные уже существуют")
            return
        
        # Создание остановок с привязкой к камерам
        stops_data = [
            {
                "name": "250-летия Челябинска - Академика Макеева",
                "latitude": 55.1644,
                "longitude": 61.4368,
                "camera_id": "camera1",
                "camera_url": "rtsp://cdn.cams.is74.ru:8554?uuid=ab7346d3-b64c-4754-a02a-96f01fd2a2fa&quality=main",
                "stop_zone_coords": [[100, 200], [500, 200], [500, 600], [100, 600]],  # Пример координат зоны остановки
                "is_active": True,
            },
            {
                "name": "250-летия Челябинска - Салавата Юлаева",
                "latitude": 55.1544,
                "longitude": 61.4468,
                "camera_id": "camera2",
                "camera_url": "rtsp://cdn.cams.is74.ru:8554?uuid=0cff55c4-ba25-4976-bd39-276fcbdb054a&quality=main",
                "stop_zone_coords": [[150, 250], [550, 250], [550, 650], [150, 650]],
                "is_active": True,
            },
            {
                "name": "Академика Королёва - Университетская Набережная",
                "latitude": 55.1744,
                "longitude": 61.4268,
                "camera_id": "camera3",
                "camera_url": "rtsp://cdn.cams.is74.ru:8554?uuid=57164ea3-c4fa-45ae-b315-79544770eb36&quality=main",
                "stop_zone_coords": [[200, 300], [600, 300], [600, 700], [200, 700]],
                "is_active": True,
            },
        ]
        
        created_stops = []
        for stop_data in stops_data:
            stop = Stop(**stop_data)
            db.add(stop)
            created_stops.append(stop)
        
        db.commit()
        print("Тестовые данные созданы успешно!")
        print(f"Создано остановок: {len(created_stops)}")
        for stop in created_stops:
            print(f"  - {stop.name} (ID: {stop.id}, Камера: {stop.camera_id})")
        
    except Exception as e:
        db.rollback()
        print(f"Ошибка при создании тестовых данных: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    print("Инициализация базы данных...")
    init_database()
    print("\nСоздание тестовых данных...")
    create_test_data()
    print("\nГотово!")


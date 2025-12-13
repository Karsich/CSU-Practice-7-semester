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
        
        # Создание остановок с привязкой к камерам (выбранные рабочие камеры)
        stops_data = [
            {
                "name": "Чичерина - Братьев Кашириных",
                "latitude": 55.1644,
                "longitude": 61.4368,
                "camera_id": "camera1",
                "camera_url": "rtsp://cdn.cams.is74.ru:8554/stream?uuid=1f3563e8-d978-4caf-a0bc-b1932aa99ba4&quality=hd",
                "stop_zone_coords": [[100, 200], [500, 200], [500, 600], [100, 600]],
                "is_active": True,
            },
            {
                "name": "Академика Королёва - Университетская Набережная",
                "latitude": 55.1744,
                "longitude": 61.4268,
                "camera_id": "camera2",
                "camera_url": "rtsp://cdn.cams.is74.ru:8554/stream?uuid=57164ea3-c4fa-45ae-b315-79544770eb36&quality=hd",
                "stop_zone_coords": [[200, 300], [600, 300], [600, 700], [200, 700]],
                "is_active": True,
            },
            {
                "name": "250-летия Челябинска - Салавата Юлаева",
                "latitude": 55.1544,
                "longitude": 61.4468,
                "camera_id": "camera3",
                "camera_url": "rtsp://cdn.cams.is74.ru:8554/stream?uuid=0cff55c4-ba25-4976-bd39-276fcbdb054a&quality=hd",
                "stop_zone_coords": [[150, 250], [550, 250], [550, 650], [150, 650]],
                "is_active": True,
            },
            {
                "name": "Бейвеля - Скульптора Головницкого",
                "latitude": 55.1444,
                "longitude": 61.4568,
                "camera_id": "camera4",
                "camera_url": "rtsp://cdn.cams.is74.ru:8554/stream?uuid=30bb3006-25af-44be-9a27-3e3ec3e178f2&quality=hd",
                "stop_zone_coords": [[100, 150], [500, 150], [500, 550], [100, 550]],
                "is_active": True,
            },
            {
                "name": "Комсомольский - Красного Урала",
                "latitude": 55.1844,
                "longitude": 61.4168,
                "camera_id": "camera5",
                "camera_url": "rtsp://cdn.cams.is74.ru:8554/stream?uuid=5ee19d52-94b2-4bb7-94a0-14bbc7e4f181&quality=hd",
                "stop_zone_coords": [[250, 350], [650, 350], [650, 750], [250, 750]],
                "is_active": True,
            },
            {
                "name": "Копейское ш. - Енисейская",
                "latitude": 55.1344,
                "longitude": 61.4668,
                "camera_id": "camera6",
                "camera_url": "rtsp://cdn.cams.is74.ru:8554/stream?uuid=7f3d95d0-39c4-4ff4-ac5a-07649eeca6e6&quality=hd",
                "stop_zone_coords": [[150, 200], [550, 200], [550, 600], [150, 600]],
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


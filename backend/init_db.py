"""
Скрипт для инициализации базы данных и создания тестовых данных
"""
from sqlalchemy.orm import Session
from core.database import engine, Base, SessionLocal
from core.models import Route, Stop, Bus
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
        existing_routes = db.query(Route).count()
        if existing_routes > 0:
            print("Тестовые данные уже существуют")
            return
        
        # Создание маршрутов
        routes_data = [
            {"number": "1", "name": "Маршрут №1", "description": "Тестовый маршрут 1"},
            {"number": "2", "name": "Маршрут №2", "description": "Тестовый маршрут 2"},
            {"number": "3", "name": "Маршрут №3", "description": "Тестовый маршрут 3"},
        ]
        
        created_routes = []
        for route_data in routes_data:
            route = Route(**route_data)
            db.add(route)
            created_routes.append(route)
        
        db.commit()
        
        # Создание остановок для первого маршрута
        if created_routes:
            route1 = created_routes[0]
            stops_data = [
                {
                    "route_id": route1.id,
                    "name": "Центральная остановка",
                    "latitude": 55.1644,
                    "longitude": 61.4368,
                    "camera_url": None,
                },
                {
                    "route_id": route1.id,
                    "name": "Остановка у вокзала",
                    "latitude": 55.1544,
                    "longitude": 61.4468,
                    "camera_url": None,
                },
                {
                    "route_id": route1.id,
                    "name": "Конечная остановка",
                    "latitude": 55.1744,
                    "longitude": 61.4268,
                    "camera_url": None,
                },
            ]
            
            for stop_data in stops_data:
                stop = Stop(**stop_data)
                db.add(stop)
            
            # Создание тестовых автобусов
            buses_data = [
                {
                    "route_id": route1.id,
                    "vehicle_number": "А123",
                    "license_plate": "М123АБ 74",
                    "max_capacity": 50,
                },
                {
                    "route_id": route1.id,
                    "vehicle_number": "А124",
                    "license_plate": "М124АБ 74",
                    "max_capacity": 50,
                },
            ]
            
            for bus_data in buses_data:
                bus = Bus(**bus_data)
                db.add(bus)
        
        db.commit()
        print("Тестовые данные созданы успешно!")
        print(f"Создано маршрутов: {len(created_routes)}")
        
    except Exception as e:
        db.rollback()
        print(f"Ошибка при создании тестовых данных: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    print("Инициализация базы данных...")
    init_database()
    print("\nСоздание тестовых данных...")
    create_test_data()
    print("\nГотово!")


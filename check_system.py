"""
Скрипт для проверки работоспособности системы
"""
import sys
import os

# Добавляем backend в путь
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def check_imports():
    """Проверка импортов"""
    print("Проверка импортов...")
    try:
        from main import app
        print("✓ Импорт main.py успешен")
        
        from core.models import Stop, BusDetection, LoadData, Forecast
        print("✓ Импорт моделей успешен")
        
        from services.cv_service import cv_service
        print("✓ Импорт CV сервиса успешен")
        
        from api import admin, passengers, analytics, cv, routes
        print("✓ Импорт API роутеров успешен")
        
        return True
    except Exception as e:
        print(f"✗ Ошибка импорта: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_models():
    """Проверка моделей"""
    print("\nПроверка моделей...")
    try:
        from core.models import Stop, BusDetection, LoadData, Forecast
        from core.database import Base
        
        # Проверяем, что модели определены
        assert hasattr(Stop, '__tablename__'), "Stop должна иметь __tablename__"
        assert hasattr(BusDetection, '__tablename__'), "BusDetection должна иметь __tablename__"
        assert hasattr(LoadData, '__tablename__'), "LoadData должна иметь __tablename__"
        assert hasattr(Forecast, '__tablename__'), "Forecast должна иметь __tablename__"
        
        print("✓ Все модели определены корректно")
        
        # Проверяем, что Stop не имеет route_id
        from sqlalchemy.inspection import inspect
        stop_columns = [col.name for col in inspect(Stop).columns]
        assert 'route_id' not in stop_columns, "Stop не должна иметь route_id"
        assert 'camera_id' in stop_columns, "Stop должна иметь camera_id"
        assert 'stop_zone_coords' in stop_columns, "Stop должна иметь stop_zone_coords"
        
        print("✓ Структура модели Stop корректна")
        
        # Проверяем LoadData
        load_columns = [col.name for col in inspect(LoadData).columns]
        assert 'route_id' not in load_columns, "LoadData не должна иметь route_id"
        assert 'people_count' in load_columns, "LoadData должна иметь people_count"
        assert 'buses_detected' in load_columns, "LoadData должна иметь buses_detected"
        
        print("✓ Структура модели LoadData корректна")
        
        return True
    except Exception as e:
        print(f"✗ Ошибка проверки моделей: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_api_routes():
    """Проверка API роутов"""
    print("\nПроверка API роутов...")
    try:
        from main import app
        
        # Получаем все роуты
        routes = []
        for route in app.routes:
            if hasattr(route, 'path') and hasattr(route, 'methods'):
                routes.append((route.path, route.methods))
        
        # Проверяем наличие ключевых роутов
        route_paths = [r[0] for r in routes]
        
        required_routes = [
            '/api/v1/admin/stops',
            '/api/v1/passengers/stops',
            '/api/v1/passengers/current-load/{stop_id}',
            '/api/v1/cv/cameras',
        ]
        
        for required in required_routes:
            found = any(required in path for path in route_paths)
            if found:
                print(f"✓ Роут {required} найден")
            else:
                print(f"✗ Роут {required} не найден")
        
        # Проверяем, что нет старых роутов с маршрутами
        old_routes = [
            '/api/v1/routes',
            '/api/v1/admin/routes',
        ]
        
        for old_route in old_routes:
            found = any(old_route in path for path in route_paths)
            if not found:
                print(f"✓ Старый роут {old_route} удален (правильно)")
            else:
                print(f"✗ Старый роут {old_route} все еще существует")
        
        return True
    except Exception as e:
        print(f"✗ Ошибка проверки роутов: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_cv_service():
    """Проверка CV сервиса"""
    print("\nПроверка CV сервиса...")
    try:
        from services.cv_service import cv_service
        
        # Проверяем наличие методов
        assert hasattr(cv_service, 'recognize_bus_number'), "CV сервис должен иметь метод recognize_bus_number"
        assert hasattr(cv_service, 'detect_stop_zone'), "CV сервис должен иметь метод detect_stop_zone"
        assert hasattr(cv_service, 'process_video_frame'), "CV сервис должен иметь метод process_video_frame"
        
        print("✓ Все методы CV сервиса присутствуют")
        
        # Проверяем, что старый метод удален
        assert not hasattr(cv_service, 'recognize_route_number'), "Старый метод recognize_route_number должен быть удален"
        
        print("✓ Старые методы удалены")
        
        return True
    except Exception as e:
        print(f"✗ Ошибка проверки CV сервиса: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("=" * 60)
    print("Проверка работоспособности системы")
    print("=" * 60)
    print()
    
    results = []
    
    results.append(("Импорты", check_imports()))
    results.append(("Модели", check_models()))
    results.append(("API роуты", check_api_routes()))
    results.append(("CV сервис", check_cv_service()))
    
    print("\n" + "=" * 60)
    print("Результаты проверки:")
    print("=" * 60)
    
    all_passed = True
    for name, result in results:
        status = "✓ ПРОЙДЕНО" if result else "✗ ОШИБКА"
        print(f"{name}: {status}")
        if not result:
            all_passed = False
    
    print("=" * 60)
    if all_passed:
        print("Все проверки пройдены успешно!")
        print("\nСистема готова к запуску.")
        print("Для запуска используйте: docker-compose up")
    else:
        print("Обнаружены ошибки. Пожалуйста, исправьте их перед запуском.")
    print("=" * 60)


if __name__ == "__main__":
    main()





"""
Скрипт для тестирования API системы
"""
import requests
import json

API_BASE = "http://localhost:8000/api/v1"


def test_health():
    """Проверка здоровья системы"""
    print("1. Проверка здоровья системы...")
    response = requests.get("http://localhost:8000/health")
    print(f"   Статус: {response.status_code}")
    print(f"   Ответ: {response.json()}\n")


def test_routes():
    """Тест получения маршрутов"""
    print("2. Получение списка маршрутов...")
    response = requests.get(f"{API_BASE}/routes")
    print(f"   Статус: {response.status_code}")
    routes = response.json()
    print(f"   Найдено маршрутов: {len(routes)}")
    if routes:
        print(f"   Первый маршрут: {routes[0]}\n")
    else:
        print("   Маршруты не найдены. Запустите init_db.py для создания тестовых данных.\n")


def test_create_route():
    """Тест создания маршрута"""
    print("3. Создание тестового маршрута...")
    route_data = {
        "number": "TEST",
        "name": "Тестовый маршрут",
        "description": "Маршрут для тестирования",
        "is_active": True
    }
    response = requests.post(f"{API_BASE}/admin/routes", json=route_data)
    print(f"   Статус: {response.status_code}")
    if response.status_code == 200:
        route = response.json()
        print(f"   Создан маршрут: {route['number']}\n")
        return route['id']
    else:
        print(f"   Ошибка: {response.text}\n")
        return None


def test_cv_detection():
    """Тест детекции объектов (требует изображение)"""
    print("4. Тест детекции объектов...")
    print("   Для полного теста загрузите изображение через /api/v1/cv/detect")
    print("   Используйте Swagger UI: http://localhost:8000/docs\n")


def main():
    print("=" * 50)
    print("Тестирование API системы мониторинга транспорта")
    print("=" * 50)
    print()
    
    try:
        test_health()
        test_routes()
        route_id = test_create_route()
        test_cv_detection()
        
        if route_id:
            print(f"5. Получение информации о маршруте {route_id}...")
            response = requests.get(f"{API_BASE}/routes/{route_id}")
            if response.status_code == 200:
                print(f"   Маршрут: {response.json()}\n")
        
        print("=" * 50)
        print("Тестирование завершено!")
        print("Для более подробного тестирования используйте Swagger UI:")
        print("http://localhost:8000/docs")
        print("=" * 50)
        
    except requests.exceptions.ConnectionError:
        print("Ошибка: Не удалось подключиться к API.")
        print("Убедитесь, что сервер запущен: docker-compose up")
    except Exception as e:
        print(f"Ошибка: {e}")


if __name__ == "__main__":
    main()


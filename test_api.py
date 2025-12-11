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


def test_stops():
    """Тест получения остановок"""
    print("2. Получение списка остановок...")
    response = requests.get(f"{API_BASE}/passengers/stops")
    print(f"   Статус: {response.status_code}")
    if response.status_code == 200:
        stops = response.json()
        print(f"   Найдено остановок: {len(stops)}")
        if stops:
            print(f"   Первая остановка: {stops[0]['name']} (ID: {stops[0]['id']})\n")
            return stops[0]['id']
        else:
            print("   Остановки не найдены. Запустите init_db.py для создания тестовых данных.\n")
    else:
        print(f"   Ошибка: {response.text}\n")
    return None


def test_create_stop():
    """Тест создания остановки"""
    print("3. Создание тестовой остановки...")
    stop_data = {
        "name": "Тестовая остановка",
        "latitude": 55.1644,
        "longitude": 61.4368,
        "camera_id": "camera1",
        "is_active": True
    }
    response = requests.post(f"{API_BASE}/admin/stops", json=stop_data)
    print(f"   Статус: {response.status_code}")
    if response.status_code == 200:
        stop = response.json()
        print(f"   Создана остановка: {stop['name']} (ID: {stop['id']})\n")
        return stop['id']
    else:
        print(f"   Ошибка: {response.text}\n")
        return None


def test_get_stop(stop_id):
    """Тест получения информации об остановке"""
    print(f"4. Получение информации об остановке {stop_id}...")
    response = requests.get(f"{API_BASE}/stops/{stop_id}")
    print(f"   Статус: {response.status_code}")
    if response.status_code == 200:
        stop = response.json()
        print(f"   Остановка: {stop['name']}")
        print(f"   Координаты: {stop['latitude']}, {stop['longitude']}")
        print(f"   Камера: {stop.get('camera_id', 'не указана')}\n")
    else:
        print(f"   Ошибка: {response.text}\n")


def test_current_load(stop_id):
    """Тест получения текущей загруженности"""
    print(f"5. Получение текущей загруженности остановки {stop_id}...")
    response = requests.get(f"{API_BASE}/passengers/current-load/{stop_id}")
    print(f"   Статус: {response.status_code}")
    if response.status_code == 200:
        load = response.json()
        print(f"   Остановка: {load['stop_name']}")
        print(f"   Людей: {load['people_count']}")
        print(f"   Автобусов: {load['buses_detected']}")
        print(f"   Статус: {load['load_status']}\n")
    else:
        print(f"   Ошибка: {response.text}\n")


def test_cameras():
    """Тест получения списка камер"""
    print("6. Получение списка камер...")
    response = requests.get(f"{API_BASE}/cv/cameras")
    print(f"   Статус: {response.status_code}")
    if response.status_code == 200:
        cameras = response.json()
        print(f"   Найдено камер: {len(cameras.get('cameras', []))}")
        for cam in cameras.get('cameras', []):
            print(f"   - {cam['name']} (ID: {cam['id']})\n")
    else:
        print(f"   Ошибка: {response.text}\n")


def test_cv_detection():
    """Тест детекции объектов (требует изображение)"""
    print("7. Тест детекции объектов...")
    print("   Для полного теста загрузите изображение через /api/v1/cv/detect")
    print("   Используйте Swagger UI: http://localhost:8000/docs\n")


def main():
    print("=" * 50)
    print("Тестирование API системы мониторинга транспорта")
    print("=" * 50)
    print()
    
    try:
        test_health()
        stop_id = test_stops()
        
        if not stop_id:
            stop_id = test_create_stop()
        
        if stop_id:
            test_get_stop(stop_id)
            test_current_load(stop_id)
        
        test_cameras()
        test_cv_detection()
        
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
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()


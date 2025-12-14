#!/usr/bin/env python
"""
Полный тест мониторинга: запуск задачи и проверка сохранения данных
"""
import sys
import requests
from datetime import datetime, timedelta
from core.database import SessionLocal
from core.models import LoadData, Stop

API_BASE = "http://localhost:8000/api/v1"

def test_via_api(stop_id: int):
    """Тест через API endpoint"""
    print(f"\n=== ТЕСТ ЧЕРЕЗ API (stop_id={stop_id}) ===")
    
    try:
        response = requests.post(f"{API_BASE}/admin/trigger-monitoring/{stop_id}", timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            print("[SUCCESS] Задача выполнена успешно!")
            print(f"  Stop: {data['stop_name']}")
            print(f"  People: {data['saved_data']['people_count']}")
            print(f"  Buses: {data['saved_data']['buses_detected']}")
            print(f"  Saved ID: {data['saved_data']['id']}")
            return True
        else:
            print(f"[ERROR] HTTP {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"[ERROR] Ошибка при вызове API: {e}")
        return False

def test_direct(stop_id: int):
    """Прямой тест (без API)"""
    print(f"\n=== ПРЯМОЙ ТЕСТ (stop_id={stop_id}) ===")
    
    try:
        from tasks.monitoring_tasks import monitor_stop_passive_task
        
        before_time = datetime.now()
        result = monitor_stop_passive_task(stop_id)
        after_time = datetime.now()
        
        if "error" in result:
            print(f"[ERROR] Задача вернула ошибку: {result['error']}")
            return False
        
        # Проверяем сохранение
        db = SessionLocal()
        saved_data = db.query(LoadData).filter(
            LoadData.stop_id == stop_id,
            LoadData.timestamp >= before_time,
            LoadData.timestamp <= after_time
        ).order_by(LoadData.timestamp.desc()).first()
        
        if not saved_data:
            print("[ERROR] Данные не сохранены в БД!")
            db.close()
            return False
        
        # Проверяем, что не тестовые
        is_test = saved_data.detection_data and isinstance(saved_data.detection_data, dict) and saved_data.detection_data.get('test_data')
        if is_test:
            print("[ERROR] Сохранена тестовая запись!")
            db.close()
            return False
        
        print("[SUCCESS] Данные сохранены правильно!")
        print(f"  ID={saved_data.id}")
        print(f"  Time={saved_data.timestamp}")
        print(f"  People={saved_data.people_count}")
        print(f"  Buses={saved_data.buses_detected}")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] Ошибка при выполнении: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_before_after(stop_id: int):
    """Проверка данных до и после"""
    db = SessionLocal()
    
    before_time = datetime.now()
    before_count = db.query(LoadData).filter(
        LoadData.stop_id == stop_id,
        LoadData.timestamp < before_time
    ).count()
    
    print(f"\nЗаписей до теста: {before_count}")
    
    # Ждем немного
    import time
    time.sleep(2)
    
    after_time = datetime.now()
    after_count = db.query(LoadData).filter(
        LoadData.stop_id == stop_id,
        LoadData.timestamp >= before_time,
        LoadData.timestamp <= after_time
    ).count()
    
    print(f"Новых записей после теста: {after_count}")
    
    if after_count > 0:
        new_records = db.query(LoadData).filter(
            LoadData.stop_id == stop_id,
            LoadData.timestamp >= before_time,
            LoadData.timestamp <= after_time
        ).all()
        
        actual_new = [r for r in new_records if not (r.detection_data and isinstance(r.detection_data, dict) and r.detection_data.get('test_data'))]
        print(f"  Из них актуальных: {len(actual_new)}")
        
        if actual_new:
            print("\n[SUCCESS] Актуальные данные сохранены!")
            for rec in actual_new:
                print(f"  ID={rec.id}, time={rec.timestamp}, people={rec.people_count}")
        else:
            print("\n[WARNING] Все новые записи - тестовые!")
    
    db.close()

if __name__ == "__main__":
    stop_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    
    print("=" * 60)
    print("ПОЛНЫЙ ТЕСТ МОНИТОРИНГА")
    print("=" * 60)
    
    # Проверяем остановку
    db = SessionLocal()
    stop = db.query(Stop).filter(Stop.id == stop_id).first()
    if not stop:
        print(f"[ERROR] Остановка {stop_id} не найдена!")
        exit(1)
    
    print(f"\nОстановка: {stop.name} (ID={stop_id})")
    print(f"  Active: {stop.is_active}")
    print(f"  Camera: {stop.camera_id}")
    print(f"  Zone: {stop.stop_zone_coords is not None}")
    db.close()
    
    # Тест 1: Через API
    api_success = test_via_api(stop_id)
    
    # Проверяем результат
    check_before_after(stop_id)
    
    # Тест 2: Прямой (если API не сработал)
    if not api_success:
        print("\nПробуем прямой запуск...")
        direct_success = test_direct(stop_id)
        if direct_success:
            check_before_after(stop_id)
    
    print("\n" + "=" * 60)
    print("ТЕСТ ЗАВЕРШЕН")
    print("=" * 60)


#!/usr/bin/env python
"""Прямой тест задачи мониторинга (без Celery) для проверки сохранения данных"""
from datetime import datetime, timedelta
from core.database import SessionLocal
from core.models import LoadData, Stop
from tasks.monitoring_tasks import monitor_stop_passive_task

STOP_ID = 1  # Тестируем остановку с ID=1

def print_recent_load_data(stop_id: int, count: int = 5):
    """Вывод последних записей"""
    db = SessionLocal()
    print(f"\n=== Последние {count} записей для stop_id={stop_id} ===")
    records = db.query(LoadData).filter(
        LoadData.stop_id == stop_id
    ).order_by(LoadData.timestamp.desc()).limit(count).all()
    
    for rec in records:
        is_test = rec.detection_data and isinstance(rec.detection_data, dict) and rec.detection_data.get('test_data')
        test_mark = "[TEST]" if is_test else "[ACTUAL]"
        print(f"  {test_mark} ID={rec.id}, time={rec.timestamp}, people={rec.people_count}, buses={rec.buses_detected}")
    db.close()

def check_stop_config(stop_id: int):
    """Проверка конфигурации остановки"""
    db = SessionLocal()
    stop = db.query(Stop).filter(Stop.id == stop_id).first()
    
    if not stop:
        print(f"[ERROR] Остановка {stop_id} не найдена!")
        db.close()
        return False
    
    print(f"\n=== Конфигурация остановки ID={stop_id} ===")
    print(f"  Название: {stop.name}")
    print(f"  Активна: {stop.is_active}")
    print(f"  Camera ID: {stop.camera_id}")
    print(f"  Есть зона остановки: {stop.stop_zone_coords is not None}")
    
    if not stop.is_active:
        print(f"[ERROR] Остановка не активна!")
        db.close()
        return False
    
    if not stop.camera_id:
        print(f"[ERROR] Camera ID не настроен!")
        db.close()
        return False
    
    if not stop.stop_zone_coords:
        print(f"[ERROR] Зона остановки не настроена!")
        db.close()
        return False
    
    db.close()
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("ПРЯМОЙ ТЕСТ ЗАДАЧИ МОНИТОРИНГА")
    print("=" * 60)
    
    # Проверяем конфигурацию
    if not check_stop_config(STOP_ID):
        print("\n[ERROR] Остановка не настроена правильно. Исправьте конфигурацию.")
        exit(1)
    
    # Показываем данные ДО
    print("\n=== ДО запуска задачи ===")
    print_recent_load_data(STOP_ID)
    
    # Запускаем задачу
    print(f"\n>>> Запуск задачи monitor_stop_passive_task для stop_id={STOP_ID}...")
    print("=" * 60)
    
    try:
        result = monitor_stop_passive_task(STOP_ID)
        print("=" * 60)
        print(f"\nРезультат выполнения:")
        print(result)
        
        if "error" in result:
            print(f"\n[ERROR] Задача завершилась с ошибкой: {result['error']}")
            exit(1)
        
        # Показываем данные ПОСЛЕ
        print("\n=== ПОСЛЕ запуска задачи ===")
        print_recent_load_data(STOP_ID)
        
        # Проверяем, что появилась новая запись
        db = SessionLocal()
        one_minute_ago = datetime.now() - timedelta(minutes=1)
        new_records = db.query(LoadData).filter(
            LoadData.stop_id == STOP_ID,
            LoadData.timestamp >= one_minute_ago
        ).all()
        
        actual_new = [r for r in new_records if not (r.detection_data and isinstance(r.detection_data, dict) and r.detection_data.get('test_data'))]
        
        if actual_new:
            print(f"\n[SUCCESS] Создана новая актуальная запись!")
            for rec in actual_new:
                print(f"  ID={rec.id}, time={rec.timestamp}, people={rec.people_count}, buses={rec.buses_detected}")
        else:
            print(f"\n[WARNING] Новая актуальная запись не найдена!")
            print(f"  Всего новых записей: {len(new_records)}")
            if new_records:
                print("  Но они все тестовые или не соответствуют критериям")
        
        db.close()
        
    except Exception as e:
        print(f"\n[CRITICAL ERROR] Исключение при выполнении задачи:")
        import traceback
        traceback.print_exc()
        exit(1)


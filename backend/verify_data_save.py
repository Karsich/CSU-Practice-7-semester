#!/usr/bin/env python
"""Проверка сохранения данных после выполнения задачи"""
from datetime import datetime, timedelta
from core.database import SessionLocal
from core.models import LoadData

def verify_last_save(stop_id: int):
    """Проверка последней сохраненной записи"""
    db = SessionLocal()
    
    # Получаем последнюю запись для этой остановки
    last_record = db.query(LoadData).filter(
        LoadData.stop_id == stop_id
    ).order_by(LoadData.timestamp.desc()).first()
    
    if not last_record:
        print(f"[ERROR] Нет записей для stop_id={stop_id}")
        db.close()
        return False
    
    # Проверяем, что это не тестовая запись
    is_test = last_record.detection_data and isinstance(last_record.detection_data, dict) and last_record.detection_data.get('test_data')
    
    if is_test:
        print(f"[ERROR] Последняя запись - тестовая (имеет test_data=True)")
        print(f"  ID={last_record.id}, time={last_record.timestamp}")
        db.close()
        return False
    
    # Проверяем, что запись свежая (за последние 5 минут)
    five_min_ago = datetime.now() - timedelta(minutes=5)
    if last_record.timestamp < five_min_ago:
        print(f"[WARNING] Последняя запись старая: {last_record.timestamp}")
        print(f"  Текущее время: {datetime.now()}")
        db.close()
        return False
    
    print(f"[SUCCESS] Найдена актуальная запись:")
    print(f"  ID={last_record.id}")
    print(f"  Stop ID={last_record.stop_id}")
    print(f"  Time={last_record.timestamp}")
    print(f"  People={last_record.people_count}")
    print(f"  Buses={last_record.buses_detected}")
    print(f"  Detection data keys: {list(last_record.detection_data.keys()) if last_record.detection_data else 'None'}")
    
    db.close()
    return True

if __name__ == "__main__":
    import sys
    stop_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    verify_last_save(stop_id)


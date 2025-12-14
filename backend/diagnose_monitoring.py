#!/usr/bin/env python
"""Диагностический скрипт для проверки системы мониторинга"""
from datetime import datetime, timedelta
from core.database import SessionLocal
from core.models import LoadData, Stop
import sys

def check_database():
    """Проверка данных в БД"""
    print("=== ПРОВЕРКА БАЗЫ ДАННЫХ ===\n")
    db = SessionLocal()
    
    try:
        # Проверяем остановки
        stops = db.query(Stop).filter(Stop.is_active == True).all()
        print(f"Активных остановок: {len(stops)}")
        
        stops_with_camera = db.query(Stop).filter(
            Stop.is_active == True,
            Stop.camera_id.isnot(None),
            Stop.stop_zone_coords.isnot(None)
        ).all()
        print(f"Остановок с камерой и зоной: {len(stops_with_camera)}")
        
        # Проверяем последние записи (за последний час)
        one_hour_ago = datetime.now() - timedelta(hours=1)
        recent_data = db.query(LoadData).filter(
            LoadData.timestamp >= one_hour_ago
        ).order_by(LoadData.timestamp.desc()).all()
        
        print(f"\nЗаписей за последний час: {len(recent_data)}")
        
        # Проверяем тестовые данные (с флагом test_data)
        all_data = db.query(LoadData).all()
        test_data = 0
        actual_data = 0
        for ld in all_data:
            if ld.detection_data and isinstance(ld.detection_data, dict) and ld.detection_data.get('test_data'):
                test_data += 1
            else:
                actual_data += 1
        
        print(f"Тестовых записей (с test_data=true): {test_data}")
        print(f"Актуальных записей (без test_data): {actual_data}")
        
        # Последние 5 записей
        last_5 = db.query(LoadData).order_by(LoadData.timestamp.desc()).limit(5).all()
        print(f"\nПоследние 5 записей:")
        for ld in last_5:
            is_test = ld.detection_data and ld.detection_data.get('test_data', False)
            test_mark = "[TEST]" if is_test else "[ACTUAL]"
            print(f"  {test_mark} ID={ld.id}, stop_id={ld.stop_id}, time={ld.timestamp}, people={ld.people_count}, buses={ld.buses_detected}")
        
        # Проверяем записи за последние 10 минут
        ten_min_ago = datetime.now() - timedelta(minutes=10)
        very_recent = db.query(LoadData).filter(
            LoadData.timestamp >= ten_min_ago
        ).count()
        print(f"\nЗаписей за последние 10 минут: {very_recent}")
        
        if very_recent == 0:
            print("  [WARNING] Нет записей за последние 10 минут! Задачи мониторинга могут не работать.")
        
    finally:
        db.close()

def check_celery_connection():
    """Проверка подключения к Celery"""
    print("\n=== ПРОВЕРКА ПОДКЛЮЧЕНИЯ К CELERY ===\n")
    
    print("[INFO] Для проверки Celery используйте команды:")
    print("  celery -A tasks.celery_app inspect active")
    print("  celery -A tasks.celery_app inspect registered")
    print("\n[INFO] Или проверьте логи Celery worker и beat")

def check_imports():
    """Проверка импортов задач"""
    print("\n=== ПРОВЕРКА ИМПОРТОВ ===\n")
    
    # Пропускаем проверку импортов, так как они требуют cv2
    print("[INFO] Пропущена проверка импортов (требуется cv2)")
    print("[INFO] Проверьте, что в окружении с Celery установлены все зависимости")

if __name__ == "__main__":
    print("=" * 60)
    print("ДИАГНОСТИКА СИСТЕМЫ МОНИТОРИНГА")
    print("=" * 60)
    print()
    
    check_imports()
    check_database()
    check_celery_connection()
    
    print("\n" + "=" * 60)
    print("РЕКОМЕНДАЦИИ:")
    print("=" * 60)
    print("1. Если Celery workers не найдены, запустите:")
    print("   celery -A tasks.celery_app worker --loglevel=info")
    print()
    print("2. Если нет записей за последние 10 минут, проверьте:")
    print("   - Запущен ли Celery Beat: celery -A tasks.celery_app beat --loglevel=info")
    print("   - Работает ли Redis: redis-cli ping")
    print("   - Есть ли ошибки в логах Celery")
    print()
    print("3. Для ручного запуска задачи используйте:")
    print("   python test_monitor.py")
    print("   или API endpoint: POST /api/v1/admin/trigger-monitoring/{stop_id}")


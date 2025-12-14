#!/usr/bin/env python
"""Проверка актуальных данных (не тестовых) в БД"""
from datetime import datetime, timedelta
from core.database import SessionLocal
from core.models import LoadData

db = SessionLocal()

print("=== ПРОВЕРКА АКТУАЛЬНЫХ ДАННЫХ ===\n")

# Проверяем записи за последний час
one_hour_ago = datetime.now() - timedelta(hours=1)
recent = db.query(LoadData).filter(
    LoadData.timestamp >= one_hour_ago
).order_by(LoadData.timestamp.desc()).all()

print(f"Записей за последний час: {len(recent)}")

# Разделяем на тестовые и актуальные
test_records = []
actual_records = []

for rec in recent:
    is_test = rec.detection_data and isinstance(rec.detection_data, dict) and rec.detection_data.get('test_data')
    if is_test:
        test_records.append(rec)
    else:
        actual_records.append(rec)

print(f"  - Тестовых: {len(test_records)}")
print(f"  - Актуальных: {len(actual_records)}")

if actual_records:
    print("\nПоследние 10 актуальных записей:")
    for rec in actual_records[:10]:
        print(f"  ID={rec.id}, stop_id={rec.stop_id}, time={rec.timestamp}, people={rec.people_count}, buses={rec.buses_detected}")
else:
    print("\n[WARNING] Нет актуальных записей за последний час!")
    print("  Задачи мониторинга могут не работать или падать с ошибками.")
    print("  Проверьте логи Celery worker:")

# Проверяем записи за последние 10 минут
ten_min_ago = datetime.now() - timedelta(minutes=10)
very_recent = db.query(LoadData).filter(
    LoadData.timestamp >= ten_min_ago
).all()

actual_very_recent = [r for r in very_recent if not (r.detection_data and isinstance(r.detection_data, dict) and r.detection_data.get('test_data'))]

print(f"\nАктуальных записей за последние 10 минут: {len(actual_very_recent)}")

if actual_very_recent:
    print("Последние записи:")
    for rec in actual_very_recent[:5]:
        print(f"  ID={rec.id}, stop_id={rec.stop_id}, time={rec.timestamp}, people={rec.people_count}")

db.close()


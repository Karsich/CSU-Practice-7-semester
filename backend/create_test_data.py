#!/usr/bin/env python
"""Скрипт для создания тестовых данных LoadData"""
from datetime import datetime, timedelta
import random
from core.database import SessionLocal
from core.models import Stop, LoadData

db = SessionLocal()

print("=== СОЗДАНИЕ ТЕСТОВЫХ ДАННЫХ ===")

# Получаем все активные остановки
stops = db.query(Stop).filter(Stop.is_active == True).all()
print(f"Найдено активных остановок: {len(stops)}")

if not stops:
    print("Нет активных остановок! Создайте остановки сначала.")
    db.close()
    exit(1)

# Создаем данные за последние 7 дней
days_back = 7
records_per_day = 24  # По одной записи в час

total_created = 0
for stop in stops:
    print(f"\nСоздание данных для остановки ID={stop.id} ({stop.name})...")
    
    # Удаляем старые тестовые данные для этой остановки (опционально)
    # db.query(LoadData).filter(LoadData.stop_id == stop.id).delete()
    
    for day in range(days_back):
        for hour in range(24):
            # Создаем timestamp для этого часа
            timestamp = datetime.now() - timedelta(days=day, hours=23-hour)
            
            # Генерируем случайные данные (симулируем реальные данные)
            # Утром и вечером больше людей (часы пик)
            if hour in [7, 8, 9, 17, 18, 19]:
                people_count = random.randint(15, 30)
                buses_detected = random.randint(1, 3)
            elif hour in [10, 11, 12, 13, 14, 15, 16]:
                people_count = random.randint(5, 15)
                buses_detected = random.randint(0, 2)
            else:
                people_count = random.randint(0, 5)
                buses_detected = random.randint(0, 1)
            
            load_data = LoadData(
                stop_id=stop.id,
                timestamp=timestamp,
                people_count=people_count,
                buses_detected=buses_detected,
                detection_data={
                    'test_data': True,
                    'generated_at': datetime.now().isoformat()
                }
            )
            db.add(load_data)
            total_created += 1
    
    print(f"  Создано {days_back * records_per_day} записей")

try:
    db.commit()
    print(f"\n[OK] Успешно создано {total_created} записей LoadData")
    
    # Проверяем результат
    total_count = db.query(LoadData).count()
    print(f"Всего записей в БД: {total_count}")
    
except Exception as e:
    db.rollback()
    print(f"\n[ERROR] Ошибка при сохранении: {e}")
    raise
finally:
    db.close()


"""
Скрипт для пересоздания таблиц базы данных
"""
from core.database import engine, Base

print("Пересоздание таблиц базы данных...")
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
print("Таблицы пересозданы успешно!")




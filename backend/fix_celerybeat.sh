#!/bin/sh
# Скрипт для исправления проблемы с celerybeat-schedule
# Удаляет поврежденный файл и перезапускает beat

echo "Удаление поврежденного файла celerybeat-schedule..."
rm -f celerybeat-schedule*
rm -f celerybeat-schedule.db
rm -f celerybeat-schedule.dat
rm -f celerybeat-schedule.dir

echo "Файлы удалены. Теперь можно запустить:"
echo "celery -A tasks.celery_app beat --loglevel=info"


# Исправление проблемы с Celery Beat

## Проблема

Celery Beat не может запуститься из-за ошибки:
```
_gdbm.error: [Errno 11] Resource temporarily unavailable: 'celerybeat-schedule'
```

## Причины

1. Файл `celerybeat-schedule` поврежден или заблокирован другим процессом
2. Несколько экземпляров Celery Beat пытаются использовать один файл
3. Файл был создан в другой среде или с другими правами доступа

## Решения

### Решение 1: Удалить поврежденный файл (рекомендуется)

В контейнере Docker:
```bash
# Войдите в контейнер celery_beat
docker exec -it transport_celery_beat sh

# Удалите файл
rm -f celerybeat-schedule*

# Или используйте скрипт
sh /app/fix_celerybeat.sh

# Перезапустите контейнер
exit
docker-compose restart celery_beat
```

Или из хост-системы:
```bash
cd backend
rm -f celerybeat-schedule*
docker-compose restart celery_beat
```

### Решение 2: Использовать другой путь для schedule файла

Измените команду в docker-compose.yml:
```yaml
command: celery -A tasks.celery_app beat --loglevel=info --schedule=/tmp/celerybeat-schedule
```

### Решение 3: Использовать Redis для хранения schedule (лучше для production)

Измените конфигурацию в `backend/tasks/celery_app.py`:
```python
celery_app.conf.beat_schedule_filename = None  # Не использовать файл
# Или используйте Redis scheduler
```

### Решение 4: Автоматическое удаление при запуске (уже добавлено в docker-compose.yml)

Команда в docker-compose.yml теперь автоматически удаляет старый файл:
```yaml
command: sh -c "rm -f /app/celerybeat-schedule* && celery -A tasks.celery_app beat --loglevel=info"
```

## Проверка работы

После исправления проверьте:

1. **Логи Celery Beat:**
   ```bash
   docker logs transport_celery_beat
   ```

2. **Активные задачи:**
   ```bash
   docker exec -it transport_celery_beat celery -A tasks.celery_app inspect scheduled
   ```

3. **Статус мониторинга:**
   ```bash
   curl http://localhost:8000/api/v1/admin/monitoring-status
   ```

## Важно

- Убедитесь, что запущен только один экземпляр Celery Beat
- Если используете несколько контейнеров, каждый должен иметь свой schedule файл
- В production лучше использовать Redis для хранения schedule


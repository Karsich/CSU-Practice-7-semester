# Диагностика проблемы с мониторингом

## Результаты диагностики

### Проблема
Актуальная информация о людях на остановках не собирается и не сохраняется в БД.

### Найденные проблемы:

1. **В БД только тестовые данные**
   - Тестовых записей: 2520
   - Актуальных записей: 0
   - Записей за последние 10 минут: 0

2. **Задачи мониторинга не выполняются автоматически**
   - Celery Beat должен запускать `monitor_all_stops_passive` каждую минуту
   - Но записи в БД не появляются

## Возможные причины:

1. **Celery Worker не запущен**
   - Задачи не могут выполняться без активного worker
   - Проверка: `celery -A tasks.celery_app inspect active`

2. **Celery Beat не запущен**
   - Периодические задачи не запускаются без beat
   - Проверка: проверьте логи beat или процесс

3. **Redis не запущен или недоступен**
   - Celery требует Redis для брокера сообщений
   - Проверка: `redis-cli ping`

4. **Ошибки при выполнении задач**
   - Задачи могут падать с ошибками
   - Проверка: логи Celery worker

5. **Проблемы с доступом к камерам**
   - Задачи могут не получать snapshot с камер
   - Проверка: логи задач мониторинга

## Решения:

### 1. Проверка статуса системы

Запустите диагностический скрипт:
```bash
cd backend
python diagnose_monitoring.py
```

### 2. Ручной запуск задачи мониторинга

#### Через API:
```bash
# Для конкретной остановки
curl -X POST http://localhost:8000/api/v1/admin/trigger-monitoring/1

# Для всех остановок
curl -X POST http://localhost:8000/api/v1/admin/trigger-monitoring-all
```

#### Через Python скрипт:
```bash
cd backend
python test_monitor.py
```

### 3. Проверка статуса мониторинга через API

```bash
curl http://localhost:8000/api/v1/admin/monitoring-status
```

### 4. Запуск Celery Worker и Beat

Если используете Docker:
```bash
docker-compose up -d celery_worker celery_beat
```

Если запускаете вручную:
```bash
# Terminal 1: Worker
celery -A tasks.celery_app worker --loglevel=info

# Terminal 2: Beat
celery -A tasks.celery_app beat --loglevel=info
```

### 5. Проверка логов

Проверьте логи Celery worker на наличие ошибок:
- Ошибки подключения к камерам
- Ошибки обработки изображений
- Ошибки сохранения в БД

## Новые API endpoints:

1. `POST /api/v1/admin/trigger-monitoring/{stop_id}` - ручной запуск мониторинга для остановки
2. `POST /api/v1/admin/trigger-monitoring-all` - ручной запуск мониторинга для всех остановок
3. `GET /api/v1/admin/monitoring-status` - статус мониторинга (последние записи, активность)

## Следующие шаги:

1. ✅ Создан диагностический скрипт
2. ✅ Добавлены API endpoints для ручного запуска
3. ⏳ Проверить, запущены ли Celery worker и beat
4. ⏳ Проверить логи на наличие ошибок
5. ⏳ Протестировать ручной запуск через API


# Быстрый тест сохранения данных

## Запуск теста

```bash
# Вариант 1: Через API (самый простой)
curl -X POST http://localhost:8000/api/v1/admin/trigger-monitoring/1

# Вариант 2: Через скрипт в контейнере
docker exec -it transport_celery_worker python /app/run_monitoring_test.py 1

# Вариант 3: Прямой запуск задачи
docker exec -it transport_celery_worker python /app/test_monitoring_direct.py
```

## Проверка результата

```bash
# Проверка статуса
curl http://localhost:8000/api/v1/admin/monitoring-status

# Проверка актуальных данных
docker exec -it transport_celery_worker python /app/check_recent_data.py
```

## Ожидаемый результат

После успешного выполнения вы должны увидеть:
- `"success": true` в ответе API
- Информацию о сохраненной записи (`saved_data`)
- Новые актуальные записи в БД (без флага `test_data`)

## Если не работает

1. Проверьте логи: `docker logs transport_celery_worker --tail 50`
2. Проверьте конфигурацию остановки: должна быть активна, иметь camera_id и stop_zone_coords
3. Проверьте доступность камеры


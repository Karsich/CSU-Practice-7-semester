# Устранение проблем с Celery и мониторингом

## Текущая ситуация

Из ваших логов видно:
1. ✅ **Celery Worker работает** - задачи выполняются
2. ❌ **Celery Beat не запускается** - ошибка с файлом `celerybeat-schedule`
3. ❓ **Задачи выполняются, но данные не сохраняются** - нужно проверить логи

## Проблема 1: Celery Beat не запускается

### Ошибка:
```
_gdbm.error: [Errno 11] Resource temporarily unavailable: 'celerybeat-schedule'
```

### Решение:

**Вариант 1: Удалить файл вручную (быстро)**
```bash
# В контейнере
docker exec -it transport_celery_beat sh
rm -f celerybeat-schedule*
exit

# Перезапустить
docker-compose restart celery_beat
```

**Вариант 2: Использовать обновленный docker-compose.yml**
Я уже обновил `docker-compose.yml` - теперь файл автоматически удаляется при запуске.

Перезапустите контейнер:
```bash
docker-compose restart celery_beat
```

**Вариант 3: Использовать скрипт**
```bash
docker exec -it transport_celery_beat sh /app/fix_celerybeat.sh
docker-compose restart celery_beat
```

## Проблема 2: Задачи выполняются, но данные не сохраняются

### Диагностика:

1. **Проверьте актуальные данные:**
   ```bash
   docker exec -it transport_celery_worker python /app/check_recent_data.py
   ```

2. **Проверьте логи worker на ошибки:**
   ```bash
   docker logs transport_celery_worker --tail 100
   ```

3. **Проверьте, завершаются ли задачи успешно:**
   ```bash
   docker exec -it transport_celery_worker celery -A tasks.celery_app inspect active
   ```

### Возможные причины:

1. **Ошибки при получении snapshot с камер**
   - Проверьте доступность камер: `https://cdn.cams.is74.ru/snapshot?uuid=...`
   - Проверьте логи на сообщения `[ERROR] Stop X - Failed to get snapshot`

2. **Ошибки обработки изображений**
   - Проверьте, установлен ли cv2 и все зависимости
   - Проверьте логи на ошибки `cv2` или `cv_service`

3. **Ошибки сохранения в БД**
   - Проверьте подключение к БД
   - Проверьте логи на `[ERROR][DB COMMIT]`

4. **Задачи падают с исключениями**
   - Проверьте логи на `[CRITICAL ERROR]`
   - Все ошибки должны логироваться

### Решение:

Если задачи падают с ошибками, проверьте логи:
```bash
# Последние 50 строк логов
docker logs transport_celery_worker --tail 50

# Логи в реальном времени
docker logs -f transport_celery_worker
```

## Проверка работы после исправлений

1. **Перезапустите Celery Beat:**
   ```bash
   docker-compose restart celery_beat
   ```

2. **Проверьте логи Beat:**
   ```bash
   docker logs transport_celery_beat
   ```
   Должно быть: `beat: Starting...` без ошибок

3. **Проверьте, что задачи запускаются:**
   ```bash
   docker exec -it transport_celery_beat celery -A tasks.celery_app inspect scheduled
   ```

4. **Подождите 1-2 минуты и проверьте данные:**
   ```bash
   docker exec -it transport_celery_worker python /app/check_recent_data.py
   ```

5. **Или через API:**
   ```bash
   curl http://localhost:8000/api/v1/admin/monitoring-status
   ```

## Ручной запуск для тестирования

Если автоматический мониторинг не работает, можно запустить вручную:

```bash
# Через API
curl -X POST http://localhost:8000/api/v1/admin/trigger-monitoring/1

# Или для всех остановок
curl -X POST http://localhost:8000/api/v1/admin/trigger-monitoring-all
```

## Следующие шаги

1. ✅ Исправлен docker-compose.yml для автоматического удаления поврежденного файла
2. ⏳ Перезапустите celery_beat: `docker-compose restart celery_beat`
3. ⏳ Проверьте логи worker на наличие ошибок
4. ⏳ Проверьте актуальные данные через 2-3 минуты после перезапуска


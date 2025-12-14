# Инструкция по тестированию мониторинга

## Проблема
Настоящие данные не записываются в БД, используются только тестовые.

## Решение

Я создал несколько скриптов для проверки и исправления проблемы:

### 1. Быстрый тест через API (рекомендуется)

```bash
# В контейнере или локально
curl -X POST http://localhost:8000/api/v1/admin/trigger-monitoring/1
```

API endpoint теперь:
- ✅ Проверяет конфигурацию остановки
- ✅ Запускает задачу мониторинга
- ✅ Проверяет, что данные сохранились
- ✅ Проверяет, что данные НЕ тестовые
- ✅ Возвращает информацию о сохраненной записи

### 2. Полный тест через скрипт

```bash
# В контейнере
docker exec -it transport_celery_worker python /app/run_monitoring_test.py 1

# Или локально
cd backend
python run_monitoring_test.py 1
```

Этот скрипт:
- Проверяет конфигурацию остановки
- Запускает задачу через API
- Проверяет сохранение данных
- Показывает результат

### 3. Прямой тест задачи

```bash
# В контейнере
docker exec -it transport_celery_worker python /app/test_monitoring_direct.py

# Или локально
cd backend
python test_monitoring_direct.py
```

### 4. Проверка сохраненных данных

```bash
# Проверка последних актуальных данных
docker exec -it transport_celery_worker python /app/check_recent_data.py

# Проверка конкретной записи
docker exec -it transport_celery_worker python /app/verify_data_save.py 1
```

## Что было исправлено

1. **API endpoint улучшен** (`backend/api/admin.py`):
   - Добавлена проверка конфигурации остановки
   - Добавлена проверка сохранения данных
   - Добавлена проверка, что данные не тестовые
   - Возвращается информация о сохраненной записи

2. **Созданы тестовые скрипты**:
   - `run_monitoring_test.py` - полный тест через API и напрямую
   - `test_monitoring_direct.py` - прямой запуск задачи
   - `verify_data_save.py` - проверка сохраненных данных
   - `check_recent_data.py` - проверка актуальных данных

## Проверка результата

После запуска теста проверьте:

1. **Через API:**
   ```bash
   curl http://localhost:8000/api/v1/admin/monitoring-status
   ```

2. **Через скрипт:**
   ```bash
   docker exec -it transport_celery_worker python /app/check_recent_data.py
   ```

3. **Прямой запрос к БД:**
   ```bash
   docker exec -it transport_celery_worker python /app/verify_data_save.py 1
   ```

## Ожидаемый результат

После успешного выполнения:
- ✅ Задача выполняется без ошибок
- ✅ Данные сохраняются в БД
- ✅ Данные НЕ имеют флаг `test_data`
- ✅ В ответе API есть информация о сохраненной записи

## Если данные не сохраняются

Проверьте логи на наличие ошибок:

```bash
# Логи worker
docker logs transport_celery_worker --tail 100 | grep -i error

# Логи API
docker logs transport_api_gateway --tail 100 | grep -i error
```

Возможные проблемы:
1. Ошибки получения snapshot с камеры
2. Ошибки обработки изображений
3. Ошибки сохранения в БД
4. Проблемы с конфигурацией остановки

## Следующие шаги

1. ✅ Запустите тест: `curl -X POST http://localhost:8000/api/v1/admin/trigger-monitoring/1`
2. ✅ Проверьте результат: `curl http://localhost:8000/api/v1/admin/monitoring-status`
3. ✅ Если работает - проверьте автоматический запуск через Celery Beat


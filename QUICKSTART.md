# Быстрый старт

## Запуск через Docker Compose (рекомендуется)

1. Убедитесь, что Docker и Docker Compose установлены

2. Запустите все сервисы:
```bash
docker-compose up -d
```

3. Подождите несколько минут пока загрузятся модели YOLO (при первом запуске)

4. Инициализируйте базу данных с тестовыми данными (в другом терминале):
```bash
docker-compose exec api_gateway python init_db.py
```

5. Откройте в браузере:
   - Frontend: http://localhost
   - API документация: http://localhost:8000/docs
   - API: http://localhost:8000

## Проверка работы

### 1. Проверка API
```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/routes
```

### 2. Тестирование детекции объектов

Откройте http://localhost:8000/docs и используйте endpoint:
- `POST /api/v1/cv/detect` - загрузите изображение с людьми или автобусами
- `POST /api/v1/cv/detect-with-visualization` - получите изображение с отрисованными детекциями

### 3. Работа с фронтендом

1. Откройте http://localhost
2. Выберите маршрут из списка
3. Выберите остановку
4. Просмотрите текущую загруженность и прогноз

## Локальная разработка

### Установка зависимостей
```bash
pip install -r requirements.txt
```

### Настройка окружения
Скопируйте `.env.example` в `.env` и настройте переменные окружения.

### Запуск PostgreSQL и Redis
```bash
docker-compose up -d postgres redis
```

### Инициализация БД
```bash
cd backend
python init_db.py
```

### Запуск API
```bash
cd backend
uvicorn main:app --reload
```

### Запуск Celery worker
```bash
cd backend
celery -A tasks.celery_app worker --loglevel=info
```

## Структура проекта

```
.
├── backend/              # Backend код
│   ├── api/             # API роуты
│   ├── core/            # Основные настройки (БД, конфиг)
│   ├── services/        # Сервисы (CV, прогнозирование)
│   ├── tasks/           # Celery задачи
│   ├── main.py          # Точка входа API
│   └── init_db.py       # Инициализация БД
├── frontend/            # Frontend код
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── nginx/               # Конфигурация Nginx
├── docker-compose.yml   # Docker Compose конфигурация
└── requirements.txt     # Python зависимости
```

## Добавление тестовых данных

### Через API (http://localhost:8000/docs)

1. Создайте маршрут:
```json
POST /api/v1/admin/routes
{
  "number": "5",
  "name": "Маршрут №5",
  "description": "Описание",
  "is_active": true
}
```

2. Создайте остановку:
```json
POST /api/v1/admin/stops
{
  "route_id": 1,
  "name": "Новая остановка",
  "latitude": 55.1644,
  "longitude": 61.4368,
  "camera_url": "rtsp://example.com/stream",
  "is_active": true
}
```

3. Добавьте автобус:
```json
POST /api/v1/admin/buses
{
  "route_id": 1,
  "vehicle_number": "А999",
  "license_plate": "М999АБ 74",
  "max_capacity": 50,
  "is_active": true
}
```

## Работа с видеопотоками

Для обработки реальных видеопотоков нужно:
1. Настроить камеры и получить URL потоков (RTSP/HTTP)
2. Обновить поле `camera_url` в базе данных для остановок
3. Настроить автоматическую обработку потоков (можно добавить cron задачу или отдельный сервис)

## Важные замечания

1. При первом запуске YOLO модель автоматически загрузится из интернета (около 6MB)
2. Для обработки видеопотоков в продакшене рекомендуется использовать GPU
3. Прогнозирование требует достаточного количества исторических данных (минимум 24 часа)
4. Для распознавания номеров маршрутов требуется дополнительная настройка OCR (например, EasyOCR или Tesseract)





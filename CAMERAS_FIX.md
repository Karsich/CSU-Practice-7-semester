# Исправление конфигурации камер

## Выбранные рабочие камеры

Обновлена конфигурация с 6 рабочими камерами:

1. **Чичерина - Братьев Кашириных** (camera1)
   - UUID: `1f3563e8-d978-4caf-a0bc-b1932aa99ba4`
   - RTSP: `rtsp://cdn.cams.is74.ru:8554?uuid=1f3563e8-d978-4caf-a0bc-b1932aa99ba4&quality=hd`

2. **Академика Королёва - Университетская Набережная** (camera2)
   - UUID: `57164ea3-c4fa-45ae-b315-79544770eb36`
   - RTSP: `rtsp://cdn.cams.is74.ru:8554?uuid=57164ea3-c4fa-45ae-b315-79544770eb36&quality=hd`

3. **250-летия Челябинска - Салавата Юлаева** (camera3)
   - UUID: `0cff55c4-ba25-4976-bd39-276fcbdb054a`
   - RTSP: `rtsp://cdn.cams.is74.ru:8554?uuid=0cff55c4-ba25-4976-bd39-276fcbdb054a&quality=hd`

4. **Бейвеля - Скульптора Головницкого** (camera4)
   - UUID: `30bb3006-25af-44be-9a27-3e3ec3e178f2`
   - RTSP: `rtsp://cdn.cams.is74.ru:8554?uuid=30bb3006-25af-44be-9a27-3e3ec3e178f2&quality=hd`

5. **Комсомольский - Красного Урала** (camera5)
   - UUID: `5ee19d52-94b2-4bb7-94a0-14bbc7e4f181` (Бульвар Славы)
   - RTSP: `rtsp://cdn.cams.is74.ru:8554?uuid=5ee19d52-94b2-4bb7-94a0-14bbc7e4f181&quality=hd`

6. **Копейское ш. - Енисейская** (camera6)
   - UUID: `7f3d95d0-39c4-4ff4-ac5a-07649eeca6e6` (Гагарина - Руставели)
   - RTSP: `rtsp://cdn.cams.is74.ru:8554?uuid=7f3d95d0-39c4-4ff4-ac5a-07649eeca6e6&quality=hd`

## Исправления

### 1. Формат RTSP URL
- **Правильный формат**: `rtsp://cdn.cams.is74.ru:8554?uuid=UUID&quality=hd` (БЕЗ `/stream`)
- Все камеры обновлены с правильным форматом

### 2. Функция snapshot
- Добавлены несколько вариантов URL для snapshot
- Улучшена обработка ошибок
- Добавлен параметр `&lossy=1`

### 3. База данных
- Проблема: колонка `camera_id` не существует в таблице `stops`
- Решение: нужно пересоздать таблицы через `Base.metadata.drop_all()` и `Base.metadata.create_all()`

### 4. init_db.py
- Обновлен с правильными камерами
- Добавлены все 6 выбранных камер

## Проверка подключения

Для проверки подключения к камерам используйте:
```bash
# Проверка snapshot
curl "https://cdn.cams.is74.ru/snapshot?uuid=UUID&lossy=1"

# Проверка RTSP (требует специального клиента)
rtsp://cdn.cams.is74.ru:8554?uuid=UUID&quality=hd
```

## Следующие шаги

1. Пересоздать таблицы БД (удалить и создать заново)
2. Запустить `init_db.py` для создания тестовых данных
3. Проверить подключение к камерам через WebSocket
4. Проверить работу snapshot в админской панели



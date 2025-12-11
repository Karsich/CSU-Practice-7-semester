# Руководство по работе с камерами stream.is74.ru

## Интегрированные камеры

Система интегрирована с общедоступными камерами с сайта [stream.is74.ru](https://stream.is74.ru). Доступны следующие камеры:

1. **camera1** - "250-летия Челябинска - Академика Макеева"
2. **camera2** - "250-летия Челябинска - Салавата Юлаева"  
3. **camera3** - "Академика Королёва - Университетская Набережная"

## API Endpoints

### 1. Получение списка камер

**GET** `/api/v1/cv/cameras`

Возвращает список всех доступных камер.

**Пример ответа:**
```json
{
  "cameras": [
    {
      "id": "camera1",
      "name": "250-летия Челябинска - Академика Макеева",
      "uuid": "ab7346d3-b64c-4754-a02a-96f01fd2a2fa"
    },
    ...
  ]
}
```

### 2. Получение информации о потоке камеры

**GET** `/api/v1/cv/camera/{camera_id}/stream?with_detection=false`

Возвращает информацию о видеопотоке камеры (RTSP и HLS ссылки).

**Параметры:**
- `camera_id` - ID камеры (camera1, camera2, camera3)
- `with_detection` - Включить детекцию (по умолчанию false)

**Пример запроса:**
```bash
curl http://localhost:8000/api/v1/cv/camera/camera1/stream?with_detection=false
```

**Пример ответа:**
```json
{
  "camera_id": "camera1",
  "camera_name": "250-летия Челябинска - Академика Макеева",
  "rtsp_url": "rtsp://cdn.cams.is74.ru:8554?uuid=...",
  "hls_url": "https://cdn.cams.is74.ru/hls/playlists/multivariant.m3u8?uuid=...",
  "detection_enabled": false
}
```

### 3. Получение снимка с камеры

**GET** `/api/v1/cv/camera/{camera_id}/snapshot?with_detection=false`

Возвращает текущий снимок с камеры (JPEG изображение).

**Параметры:**
- `camera_id` - ID камеры
- `with_detection` - Включить детекцию объектов на снимке

**Пример запроса:**
```bash
# Снимок без детекции
curl http://localhost:8000/api/v1/cv/camera/camera1/snapshot -o snapshot.jpg

# Снимок с детекцией
curl http://localhost:8000/api/v1/cv/camera/camera1/snapshot?with_detection=true -o snapshot_detected.jpg
```

### 4. WebSocket поток в реальном времени

**WebSocket** `/api/v1/cv/camera/{camera_id}/stream-ws?with_detection=true`

Потоковое видео с камеры в реальном времени через WebSocket.

**Параметры:**
- `camera_id` - ID камеры
- `with_detection` - Включить детекцию объектов (по умолчанию true)

**Протокол:**
- Сервер отправляет кадры как JPEG изображения (bytes)
- После каждого кадра отправляет метаданные в формате JSON (если включена детекция)

**Пример использования через JavaScript:**
```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/cv/camera/camera1/stream-ws?with_detection=true');

ws.onmessage = async (event) => {
    if (event.data instanceof Blob) {
        // Это изображение - отобразить на canvas
        const img = new Image();
        img.src = URL.createObjectURL(event.data);
        ctx.drawImage(img, 0, 0);
    } else {
        // Это метаданные (JSON)
        const data = JSON.parse(event.data);
        console.log('Люди:', data.people_count);
        console.log('Автобусы:', data.buses_count);
        console.log('Автомобили:', data.cars_count);
    }
};
```

## Веб-интерфейс

Откройте в браузере: `http://localhost/cameras.html`

Возможности:
- Просмотр всех доступных камер
- Запуск потока с детекцией или без
- Отображение статистики в реальном времени
- Остановка потоков

## Использование

### Через веб-интерфейс:

1. Откройте `http://localhost/cameras.html`
2. Выберите камеру
3. Нажмите "С детекцией" для просмотра с распознаванием объектов
4. Или "Без детекции" для обычного просмотра
5. Нажмите "Стоп" для остановки потока

### Через API:

```bash
# Получить список камер
curl http://localhost:8000/api/v1/cv/cameras

# Получить снимок с детекцией
curl http://localhost:8000/api/v1/cv/camera/camera1/snapshot?with_detection=true -o snapshot.jpg

# Получить информацию о потоке
curl http://localhost:8000/api/v1/cv/camera/camera1/stream
```

### Через Swagger UI:

1. Откройте `http://localhost:8000/docs`
2. Найдите эндпоинты в разделе "Computer Vision"
3. Протестируйте эндпоинты прямо в браузере

## Технические детали

- **RTSP потоки**: Используются для обработки через OpenCV
- **HLS потоки**: Доступны для прямого просмотра в браузере
- **Частота обработки**: ~10 FPS (каждый 3-й кадр обрабатывается)
- **Формат кадров**: JPEG, качество 85%
- **Детекция**: YOLOv8n для распознавания людей, автобусов и автомобилей

## Примечания

- Камеры предоставляются компанией "Интерсвязь" и доступны публично
- RTSP потоки могут требовать некоторое время для подключения
- При высокой нагрузке рекомендуется использовать HLS потоки для просмотра
- WebSocket потоки автоматически переподключаются при обрыве соединения


# Руководство по обработке видео

## Новые возможности

### 1. Эндпоинт для обработки видеофайлов

**POST** `/api/v1/cv/process-video`

Позволяет загрузить видеофайл и получить обработанное видео с визуализацией детекций.

**Параметры:**
- `file` (обязательно): видеофайл
- `save_output` (опционально, boolean): если `true`, возвращает обработанное видео

**Пример использования через curl:**
```bash
curl -X POST "http://localhost:8000/api/v1/cv/process-video?save_output=true" \
  -F "file=@video.mp4" \
  --output processed_video.mp4
```

**Пример использования через Python:**
```python
import requests

with open('video.mp4', 'rb') as f:
    files = {'file': ('video.mp4', f, 'video/mp4')}
    params = {'save_output': 'true'}
    response = requests.post(
        'http://localhost:8000/api/v1/cv/process-video',
        files=files,
        params=params
    )
    
    if response.headers.get('content-type') == 'video/mp4':
        with open('processed_video.mp4', 'wb') as out:
            out.write(response.content)
```

### 2. WebSocket эндпоинт для обработки в реальном времени

**WebSocket** `/api/v1/cv/process-video-stream`

Позволяет отправлять кадры видео в реальном времени и получать обработанные кадры с визуализацией.

**Протокол:**
- Клиент отправляет кадры как JPEG изображения (bytes)
- Сервер возвращает обработанные кадры (bytes) и метаданные (JSON)

**Пример использования через JavaScript:**
```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/cv/process-video-stream');

ws.onopen = () => {
    // Отправка кадра (canvas.toBlob результат)
    canvas.toBlob(blob => {
        blob.arrayBuffer().then(buffer => {
            ws.send(buffer);
        });
    }, 'image/jpeg');
};

ws.onmessage = async (event) => {
    if (event.data instanceof Blob) {
        // Обработанное изображение
        const img = new Image();
        img.src = URL.createObjectURL(event.data);
        ctx.drawImage(img, 0, 0);
    } else {
        // Метаданные (JSON)
        const data = JSON.parse(event.data);
        console.log('Люди:', data.people_count);
        console.log('Автобусы:', data.buses_count);
        console.log('Автомобили:', data.cars_count);
    }
};
```

### 3. Веб-интерфейс для обработки видео

Откройте в браузере: `http://localhost/video_player.html`

Возможности:
- Загрузка видеофайла
- Обработка видео с сохранением результата
- Стриминг видео в реальном времени через WebSocket
- Отображение статистики (люди, автобусы, автомобили, FPS)

## Исправления визуализации

Теперь эндпоинт `/api/v1/cv/detect-with-visualization` отображает:
- ✅ Людей (зеленые рамки)
- ✅ Автобусы (синие рамки)
- ✅ Автомобили (желтые рамки)
- ✅ Статистику в левом верхнем углу

## Использование

### Быстрая обработка видеофайла:

1. **Через веб-интерфейс:**
   - Откройте `http://localhost/video_player.html`
   - Выберите видеофайл
   - Нажмите "Обработать видео"
   - Дождитесь обработки и скачайте результат

2. **Через API:**
```bash
curl -X POST "http://localhost:8000/api/v1/cv/process-video?save_output=true" \
  -F "file=@your_video.mp4" \
  --output processed.mp4
```

3. **Стриминг в реальном времени:**
   - Откройте `http://localhost/video_player.html`
   - Выберите видеофайл
   - Нажмите "Запустить стрим"
   - Наблюдайте обработку в реальном времени

## Примечания

- Обработка видео может занять время в зависимости от размера файла
- Для реального времени рекомендуется использовать WebSocket стриминг
- Качество JPEG для WebSocket: 90%
- Поддерживаемые форматы: MP4, AVI, MOV и другие форматы, поддерживаемые OpenCV




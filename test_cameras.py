"""
Скрипт для проверки подключения к камерам
"""
import requests
import cv2
import numpy as np

# Тестируемые камеры
CAMERAS_TO_TEST = {
    "Чичерина - Братьев Кашириных": "1f3563e8-d978-4caf-a0bc-b1932aa99ba4",
    "Академика Королёва - Университетская Набережная": "57164ea3-c4fa-45ae-b315-79544770eb36",
    "250-летия Челябинска - Салавата Юлаева": "0cff55c4-ba25-4976-bd39-276fcbdb054a",
    "Бейвеля - Скульптора Головницкого": "30bb3006-25af-44be-9a27-3e3ec3e178f2",
    "Комсомольский - Красного Урала (Бульвар Славы)": "5ee19d52-94b2-4bb7-94a0-14bbc7e4f181",
    "Копейское ш. - Енисейская (Гагарина - Руставели)": "7f3d95d0-39c4-4ff4-ac5a-07649eeca6e6",
}

print("Проверка подключения к камерам...")
print("=" * 60)

for name, uuid in CAMERAS_TO_TEST.items():
    print(f"\nКамера: {name}")
    print(f"UUID: {uuid}")
    
    # Тест snapshot
    snapshot_url = f"https://cdn.cams.is74.ru/snapshot?uuid={uuid}&lossy=1"
    try:
        response = requests.get(snapshot_url, timeout=5)
        if response.status_code == 200:
            nparr = np.frombuffer(response.content, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if frame is not None:
                h, w = frame.shape[:2]
                print(f"✓ Snapshot работает: {w}x{h}")
            else:
                print("✗ Snapshot: не удалось декодировать изображение")
        else:
            print(f"✗ Snapshot: HTTP {response.status_code}")
    except Exception as e:
        print(f"✗ Snapshot ошибка: {e}")
    
    # Тест RTSP (только проверка URL, не подключение)
    rtsp_url = f"rtsp://cdn.cams.is74.ru:8554?uuid={uuid}&quality=hd"
    print(f"RTSP URL: {rtsp_url}")

print("\n" + "=" * 60)
print("Проверка завершена!")



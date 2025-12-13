"""
Конфигурация камер с сайта stream.is74.ru
Используется HD качество для лучшего распознавания номеров автобусов
Правильный формат RTSP: rtsp://cdn.cams.is74.ru:8554/stream?uuid=UUID&quality=hd (С /stream)
"""
IS74_CAMERAS = {
    "camera1": {
        "name": "Чичерина - Братьев Кашириных",
        "rtsp": "rtsp://cdn.cams.is74.ru:8554/stream?uuid=1f3563e8-d978-4caf-a0bc-b1932aa99ba4&quality=hd",
        "rtsp_main": "rtsp://cdn.cams.is74.ru:8554/stream?uuid=1f3563e8-d978-4caf-a0bc-b1932aa99ba4&quality=main",
        "hls": "https://cdn.cams.is74.ru/hls/playlists/multivariant.m3u8?uuid=1f3563e8-d978-4caf-a0bc-b1932aa99ba4",
        "uuid": "1f3563e8-d978-4caf-a0bc-b1932aa99ba4"
    },
    "camera2": {
        "name": "Академика Королёва - Университетская Набережная",
        "rtsp": "rtsp://cdn.cams.is74.ru:8554/stream?uuid=57164ea3-c4fa-45ae-b315-79544770eb36&quality=hd",
        "rtsp_main": "rtsp://cdn.cams.is74.ru:8554/stream?uuid=57164ea3-c4fa-45ae-b315-79544770eb36&quality=main",
        "hls": "https://cdn.cams.is74.ru/hls/playlists/multivariant.m3u8?uuid=57164ea3-c4fa-45ae-b315-79544770eb36",
        "uuid": "57164ea3-c4fa-45ae-b315-79544770eb36"
    },
    "camera3": {
        "name": "250-летия Челябинска - Салавата Юлаева",
        "rtsp": "rtsp://cdn.cams.is74.ru:8554/stream?uuid=0cff55c4-ba25-4976-bd39-276fcbdb054a&quality=hd",
        "rtsp_main": "rtsp://cdn.cams.is74.ru:8554/stream?uuid=0cff55c4-ba25-4976-bd39-276fcbdb054a&quality=main",
        "hls": "https://cdn.cams.is74.ru/hls/playlists/multivariant.m3u8?uuid=0cff55c4-ba25-4976-bd39-276fcbdb054a",
        "uuid": "0cff55c4-ba25-4976-bd39-276fcbdb054a"
    },
    "camera4": {
        "name": "Бейвеля - Скульптора Головницкого",
        "rtsp": "rtsp://cdn.cams.is74.ru:8554/stream?uuid=30bb3006-25af-44be-9a27-3e3ec3e178f2&quality=hd",
        "rtsp_main": "rtsp://cdn.cams.is74.ru:8554/stream?uuid=30bb3006-25af-44be-9a27-3e3ec3e178f2&quality=main",
        "hls": "https://cdn.cams.is74.ru/hls/playlists/multivariant.m3u8?uuid=30bb3006-25af-44be-9a27-3e3ec3e178f2",
        "uuid": "30bb3006-25af-44be-9a27-3e3ec3e178f2"
    },
    "camera5": {
        "name": "Комсомольский - Красного Урала",
        "rtsp": "rtsp://cdn.cams.is74.ru:8554/stream?uuid=5ee19d52-94b2-4bb7-94a0-14bbc7e4f181&quality=hd",
        "rtsp_main": "rtsp://cdn.cams.is74.ru:8554/stream?uuid=5ee19d52-94b2-4bb7-94a0-14bbc7e4f181&quality=main",
        "hls": "https://cdn.cams.is74.ru/hls/playlists/multivariant.m3u8?uuid=5ee19d52-94b2-4bb7-94a0-14bbc7e4f181",
        "uuid": "5ee19d52-94b2-4bb7-94a0-14bbc7e4f181"
    },
    "camera6": {
        "name": "Копейское ш. - Енисейская",
        "rtsp": "rtsp://cdn.cams.is74.ru:8554/stream?uuid=7f3d95d0-39c4-4ff4-ac5a-07649eeca6e6&quality=hd",
        "rtsp_main": "rtsp://cdn.cams.is74.ru:8554/stream?uuid=7f3d95d0-39c4-4ff4-ac5a-07649eeca6e6&quality=main",
        "hls": "https://cdn.cams.is74.ru/hls/playlists/multivariant.m3u8?uuid=7f3d95d0-39c4-4ff4-ac5a-07649eeca6e6",
        "uuid": "7f3d95d0-39c4-4ff4-ac5a-07649eeca6e6"
    }
}



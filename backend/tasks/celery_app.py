"""
Celery приложение для асинхронных задач
"""
from celery import Celery
from celery.schedules import crontab
from core.config import settings

celery_app = Celery(
    "transport_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    beat_schedule={
        'monitor-all-stops-every-minute': {
            'task': 'monitor_all_stops_passive',
            'schedule': 60.0,  # Каждую минуту
        },
    },
)

# Импортируем задачи для их регистрации в Celery
# Это гарантирует, что задачи будут доступны при запуске worker
try:
    from tasks import monitoring_tasks  # noqa: F401
    from tasks import video_tasks  # noqa: F401
except ImportError as e:
    # Если зависимости не установлены, задачи не будут работать
    # но это не должно ломать инициализацию Celery
    import warnings
    warnings.warn(f"Не удалось импортировать задачи: {e}")




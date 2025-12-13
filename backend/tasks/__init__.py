"""
Импорт всех задач для автоматической регистрации в Celery
"""
from tasks import video_tasks
from tasks import monitoring_tasks

__all__ = ['video_tasks', 'monitoring_tasks']

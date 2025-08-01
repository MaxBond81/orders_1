import os
from celery import Celery

# Установка переменной окружения для celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'netology_pd_diplom.settings')

# Создание экземпляра Celery
app = Celery('netology_pd_diplom')

# Загрузка конфигурации из settings.py
app.config_from_object('django.conf:settings', namespace='CELERY')

# Автоматическая регистрация задач
app.autodiscover_tasks()
import os
import sys

from celery import Celery

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.settings")
from django.conf import settings

# Create a Celery instance and configure it using the settings from settings.py
project_name = os.getenv("PROJECT_NAME", "server")
app = Celery(project_name)
app.conf.update(
    task_serializer="json",
    accept_content=["json"],  # Ignore other content
    result_serializer="json",
    timezone="Asia/Tehran",
    enable_utc=True,
    worker_concurrency=1 if settings.DEBUG else 2**2,
    broker_connection_retry_on_startup=True,
)

app.conf.beat_schedule = {
    # "check-timeout-tasks": {
    #     "task": "apps.service.functions.check_timeout_tasks",  # Replace with your actual task path
    #     "schedule": datetime.timedelta(minutes=1 if settings.DEBUG else 10),
    # },
}

# Load task modules from all registered Django app configs.
app.config_from_object("django.conf:settings", namespace="CELERY")

# This will make sure that the app is loaded when Django starts.
app.autodiscover_tasks()

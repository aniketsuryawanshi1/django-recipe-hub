import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

# Celery Beat schedule for periodic tasks
app.conf.beat_schedule = {
    'send-daily-email': {
        'task': 'recipes.tasks.send_daily_email',
        'schedule': {
            'hour': 6,
            'minute': 0,
        },
        'options': {'timezone': settings.TIME_ZONE}
    },
    'export-user-data-weekly': {
        'task': 'recipes.tasks.export_user_data_weekly',
        'schedule': {
            'hour': 2,
            'minute': 0,
            'day_of_week': 0,  # Sunday
        },
        'options': {'timezone': settings.TIME_ZONE}
    },
    'cleanup-old-exports': {
        'task': 'recipes.tasks.cleanup_old_exports',
        'schedule': {
            'hour': 3,
            'minute': 0,
            'day_of_week': 0,  # Sunday
        },
        'options': {'timezone': settings.TIME_ZONE}
    },
}

app.conf.timezone = settings.TIME_ZONE

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
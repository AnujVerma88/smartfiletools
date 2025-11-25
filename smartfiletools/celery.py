import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smartfiletools.settings')

app = Celery('smartfiletools')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery Beat Schedule for periodic tasks
app.conf.beat_schedule = {
    'cleanup-old-files-every-hour': {
        'task': 'apps.tools.tasks.cleanup_old_files',
        'schedule': crontab(minute=0),  # Run every hour
    },
    'cleanup-old-logs-daily': {
        'task': 'apps.tools.tasks.cleanup_old_logs',
        'schedule': crontab(hour=2, minute=0),  # Run daily at 2 AM
    },
    'reset-daily-usage-midnight': {
        'task': 'apps.accounts.tasks.reset_daily_usage',
        'schedule': crontab(hour=0, minute=0),  # Run daily at midnight UTC
    },
    # API Management Tasks
    'reset-monthly-api-usage': {
        'task': 'apps.api.tasks.reset_monthly_usage_counters',
        'schedule': crontab(day_of_month=1, hour=0, minute=0),  # First day of month at midnight
    },
    'cleanup-old-api-logs': {
        'task': 'apps.api.tasks.cleanup_old_usage_logs',
        'schedule': crontab(day_of_week=0, hour=3, minute=0),  # Weekly on Sunday at 3 AM
    },
    'check-quota-warnings': {
        'task': 'apps.api.tasks.check_quota_warnings',
        'schedule': crontab(hour=9, minute=0),  # Daily at 9 AM
    },
    'send-usage-alerts': {
        'task': 'apps.api.tasks.send_usage_alerts',
        'schedule': crontab(hour=10, minute=0),  # Daily at 10 AM
    },
    'generate-usage-reports': {
        'task': 'apps.api.tasks.generate_usage_reports',
        'schedule': crontab(day_of_month=1, hour=1, minute=0),  # First day of month at 1 AM
    },
    'retry-failed-webhooks': {
        'task': 'apps.api.webhooks.retry_failed_webhooks',
        'schedule': crontab(minute='*/15'),  # Every 15 minutes
    },
}

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

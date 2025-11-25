"""
Celery tasks for user account management.
"""
import logging
from celery import shared_task
from django.utils import timezone
from .models import User

logger = logging.getLogger('apps.accounts')


@shared_task
def reset_daily_usage():
    """
    Celery scheduled task to reset daily usage counters for all users.
    Runs daily at midnight UTC.
    """
    logger.info("Starting daily usage reset task")
    
    today = timezone.now().date()
    
    # Find users whose last reset was not today
    users_to_reset = User.objects.exclude(last_reset_date=today)
    
    reset_count = 0
    for user in users_to_reset:
        user.daily_usage_count = 0
        user.last_reset_date = today
        user.save(update_fields=['daily_usage_count', 'last_reset_date'])
        reset_count += 1
    
    logger.info(f"Daily usage reset completed: {reset_count} users reset")
    
    return {
        'reset_count': reset_count,
        'date': str(today),
    }

"""
Signal handlers for authentication events.
Logs user login, logout, and failed login attempts.
"""
import logging
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver

logger = logging.getLogger('apps.accounts')


def get_client_ip(request):
    """
    Extract client IP address from request headers.
    """
    if request is None:
        return 'Unknown'
    
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', 'Unknown')
    return ip


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """
    Log successful user login events.
    """
    ip = get_client_ip(request)
    logger.info(f"LOGIN SUCCESS | User: {user.username} | Email: {user.email} | IP: {ip}")


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    """
    Log user logout events.
    """
    if user:
        logger.info(f"LOGOUT | User: {user.username} | Email: {user.email}")


@receiver(user_login_failed)
def log_user_login_failed(sender, credentials, request, **kwargs):
    """
    Log failed login attempts for security monitoring.
    """
    ip = get_client_ip(request)
    username = credentials.get('username', 'Unknown')
    logger.warning(f"LOGIN FAILED | Username: {username} | IP: {ip}")

"""
Signal handlers for authentication events.
Logs user login, logout, and failed login attempts.
Handles OAuth social authentication events.
"""
import logging
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver
from allauth.socialaccount.signals import pre_social_login, social_account_added
from allauth.account.models import EmailAddress

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


# OAuth Social Authentication Signal Handlers

@receiver(pre_social_login)
def handle_pre_social_login(sender, request, sociallogin, **kwargs):
    """
    Handle pre-social login events for account linking.
    
    This signal is triggered before a social login completes. It's used to:
    - Log OAuth authentication attempts
    - Handle account linking for existing users
    - Track authentication flow progress
    
    Args:
        sender: The signal sender
        request: The HTTP request object
        sociallogin: The SocialLogin object containing OAuth data
        **kwargs: Additional keyword arguments
    
    Validates: Requirements 7.1
    """
    email = sociallogin.email_addresses[0].email if sociallogin.email_addresses else 'Unknown'
    provider = sociallogin.account.provider
    ip = get_client_ip(request)
    
    logger.info(
        f"OAUTH ATTEMPT | Provider: {provider} | Email: {email} | IP: {ip}"
    )


@receiver(social_account_added)
def handle_social_account_added(sender, request, sociallogin, **kwargs):
    """
    Handle social account added events for profile population.
    
    This signal is triggered after a social account is successfully added.
    It's used to:
    - Log successful OAuth authentication
    - Populate user profile with social data
    - Track new account creation
    
    Args:
        sender: The signal sender
        request: The HTTP request object
        sociallogin: The SocialLogin object containing OAuth data
        **kwargs: Additional keyword arguments
    
    Validates: Requirements 7.2, 7.4
    """
    user = sociallogin.user
    provider = sociallogin.account.provider
    email = user.email
    ip = get_client_ip(request)
    
    # Check if this is a new user (account creation)
    is_new_user = False
    if user.date_joined and user.last_login:
        # If date_joined and last_login are very close, it's a new user
        is_new_user = abs((user.date_joined - user.last_login).total_seconds()) < 5
    elif user.date_joined and not user.last_login:
        # If no last_login, it's likely a new user
        is_new_user = True
    
    if is_new_user:
        logger.info(
            f"OAUTH ACCOUNT CREATED | Provider: {provider} | User: {user.username} | "
            f"Email: {email} | IP: {ip}"
        )
    else:
        logger.info(
            f"OAUTH SUCCESS | Provider: {provider} | User: {user.username} | "
            f"Email: {email} | IP: {ip}"
        )
    
    # Ensure email is marked as verified for social accounts
    if email:
        EmailAddress.objects.filter(
            user=user,
            email=email
        ).update(verified=True, primary=True)
        
        logger.info(
            f"OAUTH EMAIL VERIFIED | User: {user.username} | Email: {email}"
        )


# Note: OAuth failures are handled by the adapter and logged there
# See apps.accounts.adapters.SmartToolPDFSocialAccountAdapter

"""
Utility functions for user account management and usage tracking.
"""
from functools import wraps
from django.utils import timezone
from django.shortcuts import redirect
from django.contrib import messages
import logging

logger = logging.getLogger('apps.accounts')


def check_and_update_daily_usage(user):
    """
    Check and update daily usage count for a user.
    Resets counter if last reset was not today.
    
    Args:
        user: User instance
        
    Returns:
        bool: True if user has remaining conversions, False otherwise
    """
    today = timezone.now().date()
    
    # Reset daily usage if last reset was not today
    if user.last_reset_date != today:
        user.daily_usage_count = 0
        user.last_reset_date = today
        user.save(update_fields=['daily_usage_count', 'last_reset_date'])
        logger.info(f"Daily usage reset for user: {user.username}")
    
    # Check if user has remaining conversions
    if user.is_premium:
        # Premium users have unlimited conversions
        return True
    
    # Free users have daily limit
    from django.conf import settings
    daily_limit = settings.DAILY_CONVERSION_LIMIT_FREE
    if user.daily_usage_count >= daily_limit:
        logger.warning(
            f"User {user.username} reached daily limit: "
            f"{user.daily_usage_count}/{daily_limit}"
        )
        return False
    
    return True


def increment_daily_usage(user):
    """
    Increment daily usage count for a user.
    
    Args:
        user: User instance
    """
    user.daily_usage_count += 1
    user.save(update_fields=['daily_usage_count'])
    logger.debug(f"Usage incremented for {user.username}: {user.daily_usage_count}")


def get_remaining_conversions(user):
    """
    Get remaining conversions for a user.
    
    Args:
        user: User instance
        
    Returns:
        int or str: Number of remaining conversions or 'Unlimited' for premium users
    """
    if user.is_premium:
        return 'Unlimited'
    
    from django.conf import settings
    daily_limit = settings.DAILY_CONVERSION_LIMIT_FREE
    remaining = max(0, daily_limit - user.daily_usage_count)
    return remaining


def check_credit_decorator(view_func):
    """
    Decorator to check user credits before allowing conversion.
    Enforces free user limits (10 conversions per day).
    Allows unlimited for premium users.
    
    Usage:
        @check_credit_decorator
        def my_conversion_view(request):
            # View logic here
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Check if user is authenticated
        if not request.user.is_authenticated:
            messages.warning(request, 'Please log in to use conversion tools.')
            return redirect('accounts:login')
        
        user = request.user
        
        # Check and update daily usage
        if not check_and_update_daily_usage(user):
            remaining = get_remaining_conversions(user)
            messages.error(
                request,
                f'You have reached your daily conversion limit. '
                f'Upgrade to premium for unlimited conversions!'
            )
            return redirect('accounts:profile')
        
        # Increment usage count
        increment_daily_usage(user)
        
        # Call the original view
        return view_func(request, *args, **kwargs)
    
    return wrapper


def require_premium(view_func):
    """
    Decorator to require premium subscription for a view.
    
    Usage:
        @require_premium
        def premium_feature_view(request):
            # View logic here
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, 'Please log in to access this feature.')
            return redirect('accounts:login')
        
        if not request.user.is_premium:
            messages.error(
                request,
                'This feature is only available for premium users. '
                'Please upgrade your account.'
            )
            return redirect('accounts:profile')
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


class UsageTracker:
    """
    Context manager for tracking usage with automatic rollback on error.
    
    Usage:
        with UsageTracker(user) as tracker:
            # Perform conversion
            result = perform_conversion()
            tracker.success()  # Mark as successful
    """
    
    def __init__(self, user):
        self.user = user
        self.initial_count = user.daily_usage_count
        self.success_flag = False
    
    def __enter__(self):
        """Increment usage on enter."""
        increment_daily_usage(self.user)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Rollback usage if not marked as successful."""
        if not self.success_flag and exc_type is not None:
            # Rollback usage count on error
            self.user.daily_usage_count = self.initial_count
            self.user.save(update_fields=['daily_usage_count'])
            logger.warning(
                f"Usage rolled back for {self.user.username} due to error: {exc_val}"
            )
        return False  # Don't suppress exceptions
    
    def success(self):
        """Mark the operation as successful."""
        self.success_flag = True

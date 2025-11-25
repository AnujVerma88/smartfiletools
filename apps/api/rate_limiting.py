"""
API Rate Limiting System.
Implements per-minute and per-month rate limiting based on merchant plans.
"""
from functools import wraps
from django.http import JsonResponse
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger('apps.api')


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded."""
    def __init__(self, limit_type, limit, reset_time):
        self.limit_type = limit_type
        self.limit = limit
        self.reset_time = reset_time
        super().__init__(f"{limit_type} rate limit exceeded")


def get_rate_limits(merchant):
    """
    Get rate limits for a merchant based on their plan.
    
    Returns:
        dict: Rate limits with 'per_minute' and 'per_month' keys
    """
    rate_limits = {
        'free': {
            'per_minute': 10,
            'per_month': 1000,
        },
        'starter': {
            'per_minute': 50,
            'per_month': 10000,
        },
        'professional': {
            'per_minute': 200,
            'per_month': 100000,
        },
        'enterprise': {
            'per_minute': 1000,
            'per_month': None,  # Unlimited
        },
    }
    
    # Check for custom rate limit override on API key
    if hasattr(merchant, 'api_key') and merchant.api_key.rate_limit_override:
        limits = rate_limits.get(merchant.plan, rate_limits['free']).copy()
        limits['per_minute'] = merchant.api_key.rate_limit_override
        return limits
    
    return rate_limits.get(merchant.plan, rate_limits['free'])


def check_rate_limit_per_minute(merchant, api_key=None):
    """
    Check if merchant has exceeded per-minute rate limit.
    Uses Redis/cache for tracking.
    
    Args:
        merchant: APIMerchant instance
        api_key: APIKey instance (optional, for custom limits)
    
    Returns:
        tuple: (allowed: bool, current_count: int, limit: int, reset_time: datetime)
    """
    # Get rate limit for this merchant
    limits = get_rate_limits(merchant)
    per_minute_limit = limits['per_minute']
    
    # Check for custom override on specific API key
    if api_key and api_key.rate_limit_override:
        per_minute_limit = api_key.rate_limit_override
    
    # Create cache key
    cache_key = f"rate_limit:minute:{merchant.id}"
    
    # Get current count from cache
    current_count = cache.get(cache_key, 0)
    
    # Calculate reset time (next minute)
    now = timezone.now()
    reset_time = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
    
    # Check if limit exceeded
    if current_count >= per_minute_limit:
        logger.warning(
            f"Per-minute rate limit exceeded for merchant {merchant.company_name}: "
            f"{current_count}/{per_minute_limit}"
        )
        return False, current_count, per_minute_limit, reset_time
    
    # Increment counter
    if current_count == 0:
        # First request in this minute, set with 60 second expiry
        cache.set(cache_key, 1, 60)
    else:
        # Increment existing counter
        cache.incr(cache_key)
    
    return True, current_count + 1, per_minute_limit, reset_time


def check_rate_limit_per_month(merchant):
    """
    Check if merchant has exceeded per-month rate limit.
    Uses database for tracking.
    
    Args:
        merchant: APIMerchant instance
    
    Returns:
        tuple: (allowed: bool, current_count: int, limit: int, reset_time: datetime)
    """
    # Get rate limit for this merchant
    limits = get_rate_limits(merchant)
    per_month_limit = limits['per_month']
    
    # Enterprise plan has unlimited requests
    if per_month_limit is None:
        return True, merchant.current_month_usage, None, None
    
    # Check current usage
    current_usage = merchant.current_month_usage
    
    # Calculate reset time (first day of next month)
    now = timezone.now()
    if now.month == 12:
        reset_time = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        reset_time = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Check if limit exceeded
    if current_usage >= per_month_limit:
        logger.warning(
            f"Per-month rate limit exceeded for merchant {merchant.company_name}: "
            f"{current_usage}/{per_month_limit}"
        )
        return False, current_usage, per_month_limit, reset_time
    
    return True, current_usage, per_month_limit, reset_time


def rate_limit(func):
    """
    Decorator to apply rate limiting to API views.
    Checks both per-minute and per-month limits.
    
    Usage:
        @rate_limit
        def my_api_view(request):
            ...
    """
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        # Only apply to authenticated API requests
        if not hasattr(request, 'api_merchant'):
            return func(request, *args, **kwargs)
        
        merchant = request.api_merchant
        api_key = getattr(request, 'api_key', None)
        
        # Check per-minute rate limit
        minute_allowed, minute_count, minute_limit, minute_reset = check_rate_limit_per_minute(
            merchant, api_key
        )
        
        if not minute_allowed:
            logger.warning(
                f"Rate limit exceeded (per-minute) for {merchant.company_name}: "
                f"{minute_count}/{minute_limit}"
            )
            return JsonResponse(
                {
                    'success': False,
                    'data': None,
                    'message': 'Rate limit exceeded',
                    'errors': {
                        'code': 'RATE_LIMIT_EXCEEDED',
                        'details': f'You have exceeded the rate limit of {minute_limit} requests per minute. '
                                 f'Please try again after {minute_reset.strftime("%H:%M:%S")}.',
                        'limit_type': 'per_minute',
                        'limit': minute_limit,
                        'current': minute_count,
                        'reset_at': minute_reset.isoformat(),
                    }
                },
                status=429,
                headers={
                    'X-RateLimit-Limit': str(minute_limit),
                    'X-RateLimit-Remaining': '0',
                    'X-RateLimit-Reset': str(int(minute_reset.timestamp())),
                    'Retry-After': str(int((minute_reset - timezone.now()).total_seconds())),
                }
            )
        
        # Check per-month rate limit
        month_allowed, month_count, month_limit, month_reset = check_rate_limit_per_month(merchant)
        
        if not month_allowed:
            logger.warning(
                f"Rate limit exceeded (per-month) for {merchant.company_name}: "
                f"{month_count}/{month_limit}"
            )
            return JsonResponse(
                {
                    'success': False,
                    'data': None,
                    'message': 'Monthly quota exceeded',
                    'errors': {
                        'code': 'MONTHLY_QUOTA_EXCEEDED',
                        'details': f'You have exceeded your monthly quota of {month_limit} requests. '
                                 f'Your quota will reset on {month_reset.strftime("%B %d, %Y")}. '
                                 f'Please upgrade your plan for more requests.',
                        'limit_type': 'per_month',
                        'limit': month_limit,
                        'current': month_count,
                        'reset_at': month_reset.isoformat() if month_reset else None,
                    }
                },
                status=429,
                headers={
                    'X-RateLimit-Limit-Month': str(month_limit) if month_limit else 'unlimited',
                    'X-RateLimit-Remaining-Month': str(max(0, month_limit - month_count)) if month_limit else 'unlimited',
                    'X-RateLimit-Reset-Month': str(int(month_reset.timestamp())) if month_reset else '',
                }
            )
        
        # Add rate limit headers to response
        response = func(request, *args, **kwargs)
        
        # Add headers if response supports it
        if hasattr(response, '__setitem__'):
            response['X-RateLimit-Limit'] = str(minute_limit)
            response['X-RateLimit-Remaining'] = str(max(0, minute_limit - minute_count))
            response['X-RateLimit-Reset'] = str(int(minute_reset.timestamp()))
            
            if month_limit:
                response['X-RateLimit-Limit-Month'] = str(month_limit)
                response['X-RateLimit-Remaining-Month'] = str(max(0, month_limit - month_count))
                if month_reset:
                    response['X-RateLimit-Reset-Month'] = str(int(month_reset.timestamp()))
        
        return response
    
    return wrapper


def get_rate_limit_status(merchant, api_key=None):
    """
    Get current rate limit status for a merchant.
    Useful for displaying in dashboard or API responses.
    
    Args:
        merchant: APIMerchant instance
        api_key: APIKey instance (optional)
    
    Returns:
        dict: Rate limit status information
    """
    limits = get_rate_limits(merchant)
    
    # Get per-minute status
    cache_key = f"rate_limit:minute:{merchant.id}"
    minute_count = cache.get(cache_key, 0)
    minute_limit = limits['per_minute']
    if api_key and api_key.rate_limit_override:
        minute_limit = api_key.rate_limit_override
    
    now = timezone.now()
    minute_reset = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
    
    # Get per-month status
    month_count = merchant.current_month_usage
    month_limit = limits['per_month']
    
    if now.month == 12:
        month_reset = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        month_reset = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
    
    return {
        'per_minute': {
            'limit': minute_limit,
            'current': minute_count,
            'remaining': max(0, minute_limit - minute_count),
            'reset_at': minute_reset.isoformat(),
        },
        'per_month': {
            'limit': month_limit,
            'current': month_count,
            'remaining': max(0, month_limit - month_count) if month_limit else None,
            'reset_at': month_reset.isoformat(),
        },
        'plan': merchant.plan,
    }

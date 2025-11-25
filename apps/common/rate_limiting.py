"""
Web Rate Limiting System.
Implements rate limiting for web endpoints to prevent abuse.
"""
from functools import wraps
from django.http import HttpResponse
from django.core.cache import cache
from django.utils import timezone
from django.contrib import messages
from django.shortcuts import redirect
from datetime import timedelta
import logging

logger = logging.getLogger('apps.common')


def get_client_ip(request):
    """
    Extract client IP address from request.
    
    Args:
        request: Django request object
        
    Returns:
        str: Client IP address
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '')
    return ip


def rate_limit_web(max_requests=50, window_seconds=60, block_duration=30):
    """
    Decorator to apply rate limiting to web views.
    Uses IP address for tracking.
    
    Args:
        max_requests: Maximum number of requests allowed in the time window
        window_seconds: Time window in seconds (default: 300 = 5 minutes)
        block_duration: How long to block after exceeding limit (default: 900 = 15 minutes)
    
    Usage:
        @rate_limit_web(max_requests=5, window_seconds=300)
        def login_view(request):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            # Check if rate limiting is enabled
            from django.conf import settings
            if not getattr(settings, 'RATE_LIMITING_ENABLED', True):
                logger.debug(f"Rate limiting disabled - allowing request to {func.__name__}")
                return func(request, *args, **kwargs)
            
            # Get client IP
            client_ip = get_client_ip(request)
            
            # Create cache keys
            cache_key = f"rate_limit:web:{func.__name__}:{client_ip}"
            block_key = f"rate_limit:block:{func.__name__}:{client_ip}"
            
            # Check if IP is currently blocked
            if cache.get(block_key):
                logger.warning(
                    f"Blocked request from {client_ip} to {func.__name__} "
                    f"(rate limit exceeded)"
                )
                
                # Calculate remaining block time
                block_ttl = cache.ttl(block_key)
                minutes_remaining = max(1, block_ttl // 60)
                
                messages.error(
                    request,
                    f'Too many requests. Please try again in {minutes_remaining} minutes.'
                )
                
                # Return 429 response
                response = HttpResponse(
                    f'<h1>429 Too Many Requests</h1>'
                    f'<p>You have been temporarily blocked due to too many requests.</p>'
                    f'<p>Please try again in {minutes_remaining} minutes.</p>',
                    status=429
                )
                response['Retry-After'] = str(block_ttl)
                return response
            
            # Get current request count
            request_data = cache.get(cache_key, {'count': 0, 'first_request': timezone.now()})
            
            # Check if we're in a new time window
            time_elapsed = (timezone.now() - request_data['first_request']).total_seconds()
            if time_elapsed > window_seconds:
                # Reset counter for new window
                request_data = {'count': 0, 'first_request': timezone.now()}
            
            # Increment counter
            request_data['count'] += 1
            
            # Check if limit exceeded
            if request_data['count'] > max_requests:
                logger.warning(
                    f"Rate limit exceeded for {client_ip} on {func.__name__}: "
                    f"{request_data['count']}/{max_requests} in {window_seconds}s"
                )
                
                # Block the IP
                cache.set(block_key, True, block_duration)
                
                # Log security event
                logger.error(
                    f"SECURITY: IP {client_ip} blocked for {block_duration}s "
                    f"due to rate limit violation on {func.__name__}"
                )
                
                messages.error(
                    request,
                    f'Too many requests. You have been temporarily blocked. '
                    f'Please try again in {block_duration // 60} minutes.'
                )
                
                response = HttpResponse(
                    f'<h1>429 Too Many Requests</h1>'
                    f'<p>You have exceeded the rate limit and have been temporarily blocked.</p>'
                    f'<p>Please try again in {block_duration // 60} minutes.</p>',
                    status=429
                )
                response['Retry-After'] = str(block_duration)
                return response
            
            # Update cache
            cache.set(cache_key, request_data, window_seconds)
            
            # Log request
            logger.debug(
                f"Rate limit check passed for {client_ip} on {func.__name__}: "
                f"{request_data['count']}/{max_requests}"
            )
            
            # Call the original function
            return func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def rate_limit_login(func):
    """
    Specialized rate limiter for login endpoints.
    More restrictive to prevent brute force attacks.
    
    Limits:
    - 5 attempts per 5 minutes
    - 15 minute block after exceeding limit
    
    Usage:
        @rate_limit_login
        def login_view(request):
            ...
    """
    return rate_limit_web(max_requests=5, window_seconds=300, block_duration=900)(func)


def rate_limit_api_request(func):
    """
    Rate limiter for API request endpoints (non-authenticated).
    
    Limits:
    - 10 requests per minute
    - 5 minute block after exceeding limit
    
    Usage:
        @rate_limit_api_request
        def api_access_request_view(request):
            ...
    """
    return rate_limit_web(max_requests=10, window_seconds=60, block_duration=300)(func)


def rate_limit_password_reset(func):
    """
    Rate limiter for password reset endpoints.
    
    Limits:
    - 3 attempts per 10 minutes
    - 30 minute block after exceeding limit
    
    Usage:
        @rate_limit_password_reset
        def password_reset_view(request):
            ...
    """
    return rate_limit_web(max_requests=3, window_seconds=600, block_duration=1800)(func)


def check_rate_limit_status(request, view_name):
    """
    Check current rate limit status for a request.
    
    Args:
        request: Django request object
        view_name: Name of the view to check
        
    Returns:
        dict: Rate limit status
    """
    client_ip = get_client_ip(request)
    cache_key = f"rate_limit:web:{view_name}:{client_ip}"
    block_key = f"rate_limit:block:{view_name}:{client_ip}"
    
    # Check if blocked
    is_blocked = cache.get(block_key, False)
    block_ttl = cache.ttl(block_key) if is_blocked else 0
    
    # Get request count
    request_data = cache.get(cache_key, {'count': 0, 'first_request': timezone.now()})
    
    return {
        'is_blocked': is_blocked,
        'block_remaining_seconds': block_ttl,
        'request_count': request_data['count'],
        'client_ip': client_ip,
    }


def clear_rate_limit(request, view_name):
    """
    Clear rate limit for a specific IP and view.
    Useful for admin actions or testing.
    
    Args:
        request: Django request object
        view_name: Name of the view to clear
        
    Returns:
        bool: True if cleared successfully
    """
    client_ip = get_client_ip(request)
    cache_key = f"rate_limit:web:{view_name}:{client_ip}"
    block_key = f"rate_limit:block:{view_name}:{client_ip}"
    
    cache.delete(cache_key)
    cache.delete(block_key)
    
    logger.info(f"Rate limit cleared for {client_ip} on {view_name}")
    return True

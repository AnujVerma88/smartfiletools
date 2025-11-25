"""
Utility functions for API key generation and management.
"""
import secrets
import string
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
import logging

logger = logging.getLogger('apps.api')


def generate_api_key(environment='production'):
    """
    Generate a secure API key with proper prefix.
    
    Args:
        environment: 'production' or 'sandbox'
    
    Returns:
        str: Generated API key (e.g., 'stpdf_live_abc123xyz789...')
    """
    # Determine prefix based on environment
    env_prefix = 'live' if environment == 'production' else 'test'
    
    # Generate random part (32 bytes = 43 characters in base64)
    random_part = secrets.token_urlsafe(32)
    
    # Construct full key
    api_key = f"stpdf_{env_prefix}_{random_part}"
    
    logger.info(f"Generated new API key with prefix: stpdf_{env_prefix}_...")
    
    return api_key


def generate_api_secret():
    """
    Generate a secure API secret.
    
    Returns:
        str: Generated API secret (48 bytes = 64 characters in base64)
    """
    secret = secrets.token_urlsafe(48)
    logger.info("Generated new API secret")
    return secret


def hash_api_credential(credential):
    """
    Hash an API key or secret for secure storage.
    
    Args:
        credential: Plain text API key or secret
    
    Returns:
        str: Hashed credential
    """
    return make_password(credential)


def verify_api_credential(plain_credential, hashed_credential):
    """
    Verify a plain text credential against its hash.
    
    Args:
        plain_credential: Plain text credential to verify
        hashed_credential: Hashed credential from database
    
    Returns:
        bool: True if credential matches, False otherwise
    """
    return check_password(plain_credential, hashed_credential)


def extract_key_prefix(api_key, length=8):
    """
    Extract the display prefix from an API key.
    
    Args:
        api_key: Full API key
        length: Number of characters to extract (default: 8)
    
    Returns:
        str: Key prefix for display purposes
    """
    return api_key[:length] if api_key else ''


def mask_api_key(api_key, visible_chars=8):
    """
    Mask an API key for display, showing only the prefix.
    
    Args:
        api_key: Full API key
        visible_chars: Number of characters to show (default: 8)
    
    Returns:
        str: Masked key (e.g., 'stpdf_li...')
    """
    if not api_key:
        return ''
    
    if len(api_key) <= visible_chars:
        return api_key
    
    return api_key[:visible_chars] + '...'


def is_key_expired(expires_at):
    """
    Check if an API key has expired.
    
    Args:
        expires_at: Expiration datetime (can be None)
    
    Returns:
        bool: True if expired, False otherwise
    """
    if not expires_at:
        return False
    
    return timezone.now() > expires_at


def generate_webhook_secret():
    """
    Generate a secure webhook secret for HMAC signing.
    
    Returns:
        str: Generated webhook secret (32 bytes)
    """
    secret = secrets.token_urlsafe(32)
    logger.info("Generated new webhook secret")
    return secret


def validate_api_key_format(api_key):
    """
    Validate that an API key has the correct format.
    
    Args:
        api_key: API key to validate
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not api_key:
        return False, "API key is required"
    
    # Check if it starts with the correct prefix
    if not api_key.startswith('stpdf_'):
        return False, "API key must start with 'stpdf_'"
    
    # Check if it has the environment prefix
    parts = api_key.split('_')
    if len(parts) < 3:
        return False, "Invalid API key format"
    
    env_prefix = parts[1]
    if env_prefix not in ['live', 'test']:
        return False, "Invalid environment prefix (must be 'live' or 'test')"
    
    # Check minimum length
    if len(api_key) < 40:
        return False, "API key is too short"
    
    return True, None


def get_rate_limit_for_plan(plan):
    """
    Get rate limit configuration for a subscription plan.
    
    Args:
        plan: Plan name ('free', 'starter', 'professional', 'enterprise')
    
    Returns:
        dict: Rate limit configuration with 'per_minute' and 'per_month'
    """
    rate_limits = {
        'free': {
            'per_minute': 10,
            'per_month': 1000,
            'max_file_size_mb': 10,
        },
        'starter': {
            'per_minute': 50,
            'per_month': 10000,
            'max_file_size_mb': 50,
        },
        'professional': {
            'per_minute': 200,
            'per_month': 100000,
            'max_file_size_mb': 100,
        },
        'enterprise': {
            'per_minute': 1000,
            'per_month': None,  # Unlimited
            'max_file_size_mb': 500,
        },
    }
    
    return rate_limits.get(plan, rate_limits['free'])


def calculate_usage_cost(plan, request_count):
    """
    Calculate the cost for API usage based on plan and request count.
    
    Args:
        plan: Plan name
        request_count: Number of requests
    
    Returns:
        float: Cost in dollars
    """
    # Cost per request by plan
    costs_per_request = {
        'free': 0.0,
        'starter': 0.0029,  # $29/10,000 = $0.0029 per request
        'professional': 0.00199,  # $199/100,000 = $0.00199 per request
        'enterprise': 0.0,  # Custom pricing
    }
    
    cost_per_request = costs_per_request.get(plan, 0.0)
    return request_count * cost_per_request


def format_api_key_for_display(api_key_obj):
    """
    Format an APIKey object for display in UI.
    
    Args:
        api_key_obj: APIKey model instance
    
    Returns:
        dict: Formatted key information
    """
    return {
        'id': api_key_obj.id,
        'name': api_key_obj.name,
        'key_prefix': api_key_obj.key_prefix,
        'masked_key': mask_api_key(api_key_obj.key_prefix + '...'),
        'environment': api_key_obj.environment,
        'is_active': api_key_obj.is_active,
        'is_expired': api_key_obj.is_expired(),
        'last_used_at': api_key_obj.last_used_at,
        'created_at': api_key_obj.created_at,
        'expires_at': api_key_obj.expires_at,
    }


def sanitize_ip_address(ip_address):
    """
    Sanitize and validate an IP address.
    
    Args:
        ip_address: IP address string
    
    Returns:
        str: Sanitized IP address or None if invalid
    """
    import ipaddress
    
    try:
        # This will validate and normalize the IP address
        ip_obj = ipaddress.ip_address(ip_address)
        return str(ip_obj)
    except ValueError:
        logger.warning(f"Invalid IP address: {ip_address}")
        return None


def get_client_ip(request):
    """
    Extract client IP address from request, handling proxies.
    
    Args:
        request: Django request object
    
    Returns:
        str: Client IP address
    """
    # Check X-Forwarded-For header (set by proxies)
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # Take the first IP in the list
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        # Fall back to REMOTE_ADDR
        ip = request.META.get('REMOTE_ADDR')
    
    # Sanitize the IP
    sanitized_ip = sanitize_ip_address(ip)
    return sanitized_ip or '0.0.0.0'

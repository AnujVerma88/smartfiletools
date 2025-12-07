"""
API Authentication Middleware.
Validates API keys and attaches merchant information to requests.
"""
from django.http import JsonResponse
from django.utils import timezone
from .models import APIKey
from .utils import get_client_ip
import logging

logger = logging.getLogger('apps.api')


class APIKeyAuthenticationMiddleware:
    """
    Middleware to authenticate API requests using API keys.
    
    Supports two authentication methods:
    1. Authorization: Bearer <api_key>
    2. X-API-Key: <api_key>
    
    Only applies to /api/v1/ endpoints.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Only apply to API v1 endpoints (not web views or admin)
        if request.path.startswith('/api/v1/'):
            # Skip authentication endpoints
            if self._is_public_endpoint(request.path):
                return self.get_response(request)
            
            # Skip API key check if user is authenticated via session (web interface)
            if request.user.is_authenticated:
                return self.get_response(request)
            
            # Extract API key from request
            api_key = self._extract_api_key(request)
            
            if not api_key:
                return self._error_response(
                    'API key required',
                    'Please provide an API key in the Authorization header or X-API-Key header.',
                    401
                )
            
            # Validate API key
            validation_result = self._validate_api_key(api_key, request)
            
            if validation_result['error']:
                return self._error_response(
                    validation_result['error'],
                    validation_result['details'],
                    validation_result['status_code']
                )
            
            # Attach merchant and API key to request
            request.api_merchant = validation_result['merchant']
            request.api_key = validation_result['api_key_obj']
            
            # Update last used timestamp
            self._update_last_used(validation_result['api_key_obj'])
        
        # Process request
        response = self.get_response(request)
        
        # Add rate limit headers if merchant is attached
        if hasattr(request, 'api_merchant'):
            response = self._add_rate_limit_headers(response, request.api_merchant)
        
        return response
    
    def _is_public_endpoint(self, path):
        """Check if endpoint is public (doesn't require authentication)."""
        public_endpoints = [
            '/api/v1/auth/register/',
            '/api/v1/auth/login/',
            '/api/v1/auth/token/refresh/',
            '/api/v1/tools/',  # Public tool listing
        ]
        
        for endpoint in public_endpoints:
            if path.startswith(endpoint):
                return True
        
        return False
    
    def _extract_api_key(self, request):
        """
        Extract API key from request headers.
        
        Supports:
        1. Authorization: Bearer <api_key>
        2. X-API-Key: <api_key>
        """
        # Check Authorization header (Bearer token)
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Bearer '):
            return auth_header[7:].strip()
        
        # Check X-API-Key header
        api_key = request.META.get('HTTP_X_API_KEY', '')
        if api_key:
            return api_key.strip()
        
        return None
    
    def _validate_api_key(self, api_key, request):
        """
        Validate API key and return merchant information.
        
        Returns dict with:
        - error: Error message (None if valid)
        - details: Error details
        - status_code: HTTP status code
        - merchant: APIMerchant object (if valid)
        - api_key_obj: APIKey object (if valid)
        """
        try:
            # Find API key by prefix (first 8 characters)
            key_prefix = api_key[:8] if len(api_key) >= 8 else api_key
            
            # Query for matching keys
            api_key_obj = APIKey.objects.select_related('merchant').filter(
                key_prefix=key_prefix,
                is_active=True
            ).first()
            
            if not api_key_obj:
                logger.warning(f"Invalid API key attempted: {key_prefix}...")
                return {
                    'error': 'Invalid API key',
                    'details': 'The provided API key is invalid or has been revoked.',
                    'status_code': 401,
                    'merchant': None,
                    'api_key_obj': None,
                }
            
            # Verify the full key (hashed comparison)
            if not api_key_obj.verify_key(api_key):
                logger.warning(f"API key verification failed for prefix: {key_prefix}...")
                return {
                    'error': 'Invalid API key',
                    'details': 'The provided API key is invalid.',
                    'status_code': 401,
                    'merchant': None,
                    'api_key_obj': None,
                }
            
            # Check if key is expired
            if api_key_obj.is_expired():
                logger.warning(f"Expired API key used: {key_prefix}...")
                return {
                    'error': 'API key expired',
                    'details': f'This API key expired on {api_key_obj.expires_at}.',
                    'status_code': 401,
                    'merchant': None,
                    'api_key_obj': None,
                }
            
            # Check if merchant is active
            merchant = api_key_obj.merchant
            if not merchant.is_active:
                logger.warning(f"Inactive merchant attempted access: {merchant.company_name}")
                return {
                    'error': 'Merchant account inactive',
                    'details': 'Your merchant account has been deactivated. Please contact support.',
                    'status_code': 403,
                    'merchant': None,
                    'api_key_obj': None,
                }
            
            # Check quota
            if not merchant.has_quota_remaining():
                logger.warning(f"Quota exceeded for merchant: {merchant.company_name}")
                return {
                    'error': 'API quota exceeded',
                    'details': f'You have reached your monthly limit of {merchant.monthly_request_limit} requests.',
                    'status_code': 429,
                    'merchant': None,
                    'api_key_obj': None,
                }
            
            # Check IP whitelist (if configured)
            if api_key_obj.allowed_ips:
                from .ip_whitelist import is_ip_in_whitelist
                
                client_ip = get_client_ip(request)
                
                if not is_ip_in_whitelist(client_ip, api_key_obj.allowed_ips):
                    logger.warning(
                        f"IP not whitelisted for merchant {merchant.company_name}: {client_ip}. "
                        f"Allowed IPs: {', '.join(api_key_obj.allowed_ips)}"
                    )
                    return {
                        'error': 'IP not whitelisted',
                        'details': f'Your IP address ({client_ip}) is not authorized to use this API key. '
                                 f'Please add your IP to the whitelist in your merchant dashboard.',
                        'status_code': 403,
                        'merchant': None,
                        'api_key_obj': None,
                    }
            
            # All checks passed
            logger.info(f"API key validated for merchant: {merchant.company_name}")
            return {
                'error': None,
                'details': None,
                'status_code': 200,
                'merchant': merchant,
                'api_key_obj': api_key_obj,
            }
            
        except Exception as e:
            logger.error(f"Error validating API key: {str(e)}")
            return {
                'error': 'Authentication error',
                'details': 'An error occurred while validating your API key.',
                'status_code': 500,
                'merchant': None,
                'api_key_obj': None,
            }
    
    def _update_last_used(self, api_key_obj):
        """Update the last used timestamp for the API key."""
        try:
            api_key_obj.last_used_at = timezone.now()
            api_key_obj.save(update_fields=['last_used_at'])
        except Exception as e:
            logger.error(f"Failed to update last_used_at for API key {api_key_obj.id}: {str(e)}")
    
    def _add_rate_limit_headers(self, response, merchant):
        """Add rate limit headers to response."""
        try:
            response['X-RateLimit-Limit'] = str(merchant.monthly_request_limit)
            response['X-RateLimit-Remaining'] = str(
                max(0, merchant.monthly_request_limit - merchant.current_month_usage)
            )
            
            # Calculate reset time (1st of next month)
            now = timezone.now()
            if now.month == 12:
                next_month = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            else:
                next_month = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
            
            response['X-RateLimit-Reset'] = str(int(next_month.timestamp()))
        except Exception as e:
            logger.error(f"Failed to add rate limit headers: {str(e)}")
        
        return response
    
    def _error_response(self, message, details, status_code):
        """Return a JSON error response."""
        return JsonResponse(
            {
                'success': False,
                'data': None,
                'message': message,
                'errors': {
                    'code': message.upper().replace(' ', '_'),
                    'details': details,
                }
            },
            status=status_code
        )


class APIUsageLoggingMiddleware:
    """
    Middleware to log all API requests for tracking and billing.
    Should be placed after APIKeyAuthenticationMiddleware.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Only log API v1 endpoints
        if not request.path.startswith('/api/v1/'):
            return self.get_response(request)
        
        # Skip public endpoints
        if self._is_public_endpoint(request.path):
            return self.get_response(request)
        
        # Record start time
        import time
        start_time = time.time()
        
        # Get request size
        request_size = 0
        try:
            content_length = request.META.get('CONTENT_LENGTH')
            if content_length:
                request_size = int(content_length)
        except (ValueError, TypeError):
            request_size = 0
        
        # Process request
        response = self.get_response(request)
        
        # Calculate response time
        response_time = float(time.time() - start_time)
        
        # Get response size
        response_size = len(response.content) if hasattr(response, 'content') else 0
        
        # Log the request if merchant is attached
        if hasattr(request, 'api_merchant'):
            self._log_api_request(
                request,
                response,
                request_size,
                response_size,
                response_time
            )
        
        return response
    
    def _is_public_endpoint(self, path):
        """Check if endpoint is public."""
        public_endpoints = [
            '/api/v1/auth/register/',
            '/api/v1/auth/login/',
            '/api/v1/auth/token/refresh/',
            '/api/v1/tools/',
        ]
        
        for endpoint in public_endpoints:
            if path.startswith(endpoint):
                return True
        
        return False
    
    def _log_api_request(self, request, response, request_size, response_size, response_time):
        """Log API request to database with detailed tracking."""
        try:
            from .models import APIUsageLog
            from .utils import calculate_usage_cost
            
            merchant = request.api_merchant
            
            # Determine if request is billable
            billable = response.status_code < 500  # Don't charge for server errors
            
            # Calculate cost based on merchant plan
            cost = 0.0
            if billable and response.status_code < 400:
                cost = calculate_usage_cost(merchant.plan, 1)
            
            # Determine tool type from endpoint
            tool_type = ''
            if '/convert/' in request.path:
                # Extract tool type from path like /api/v1/convert/pdf-to-docx/
                parts = request.path.strip('/').split('/')
                if 'convert' in parts:
                    try:
                        idx = parts.index('convert')
                        if idx + 1 < len(parts):
                            tool_type = parts[idx + 1].replace('-', '_')
                    except ValueError:
                        pass
            elif '/esign/' in request.path:
                tool_type = 'esign'
            
            # Try to link to conversion if available
            conversion_id = None
            if hasattr(request, 'conversion_id'):
                conversion_id = request.conversion_id
            elif hasattr(response, 'data') and isinstance(response.data, dict):
                conversion_id = response.data.get('conversion_id')
            
            # Get error message if request failed
            error_message = None
            if response.status_code >= 400:
                try:
                    if hasattr(response, 'data'):
                        error_message = str(response.data.get('message', ''))[:500]
                    elif hasattr(response, 'content'):
                        import json
                        data = json.loads(response.content)
                        error_message = str(data.get('message', ''))[:500]
                except:
                    pass
            
            # Create usage log
            log = APIUsageLog.objects.create(
                merchant=merchant,
                api_key=request.api_key if hasattr(request, 'api_key') else None,
                endpoint=request.path,
                method=request.method,
                status_code=response.status_code,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                request_size=request_size,
                response_size=response_size,
                response_time=response_time,
                tool_type=tool_type,
                conversion_id=conversion_id,
                billable=billable,
                cost=cost,
                error_message=error_message or '',
            )
            
            # Increment merchant usage counter (only for successful billable requests)
            if billable and response.status_code < 400:
                merchant.increment_usage()
            
            logger.info(
                f"API Request Logged for Merchant: {merchant.company_name} (ID: {merchant.id}) - "
                f"{request.method} {request.path} - Status: {response.status_code} - "
                f"Tool: {tool_type or 'General'} - Time: {response_time:.3f}s"
            )
            
        except Exception as e:
            error_logger = logging.getLogger('apps.api')
            error_logger.error(f"Failed to log API request: {str(e)}", exc_info=True)

"""
Custom middleware for request logging and tracking.
"""
import time
import logging
from django.utils.deprecation import MiddlewareMixin
from .models import RequestLog

logger = logging.getLogger('apps.common')


class RequestLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log all HTTP requests and responses.
    Logs user, method, path, status code, IP address, and response time.
    Saves detailed request/response data to the database.
    """

    def process_request(self, request):
        """
        Called before the view is executed.
        Store the start time for calculating response time.
        """
        request._start_time = time.time()
        return None

    def process_response(self, request, response):
        """
        Called after the view is executed.
        Log the request and response details.
        """
        # Calculate response time
        if hasattr(request, '_start_time'):
            response_time = time.time() - request._start_time
        else:
            response_time = 0

        # Get user information
        user = request.user if request.user.is_authenticated else None
        user_str = request.user.username if request.user.is_authenticated else 'Anonymous'

        # Get client IP address
        ip_address = self.get_client_ip(request)

        # Log to console
        logger.info(
            f"User: {user_str} | Method: {request.method} | "
            f"Path: {request.path} | Status: {response.status_code} | "
            f"IP: {ip_address} | Duration: {response_time:.3f}s"
        )

        # Save to database (async to avoid slowing down response)
        try:
            # Only log certain paths (exclude static files, admin media, etc.)
            if self.should_log_request(request.path):
                RequestLog.objects.create(
                    user=user,
                    method=request.method,
                    path=request.path[:500],  # Truncate long paths
                    status_code=response.status_code,
                    ip_address=ip_address,
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:1000],  # Truncate long user agents
                    request_body=self.get_request_body(request),
                    response_body=self.get_response_body(response),
                    response_time=response_time
                )
        except Exception as e:
            # Don't let logging errors break the request
            logger.error(f"Error saving request log: {str(e)}")

        return response

    def get_client_ip(self, request):
        """
        Extract client IP address from request headers.
        Handles proxy headers like X-Forwarded-For.
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # Get the first IP in the chain
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip

    def get_request_body(self, request):
        """
        Get request body for POST/PUT requests.
        Truncate large bodies and exclude sensitive data.
        """
        if request.method in ['POST', 'PUT', 'PATCH']:
            try:
                # Don't log file uploads or very large bodies
                if request.content_type and 'multipart' in request.content_type:
                    return '[File Upload]'
                
                body = request.body.decode('utf-8', errors='ignore')
                
                # Truncate large bodies
                if len(body) > 5000:
                    return body[:5000] + '... [truncated]'
                
                return body
            except Exception:
                return '[Unable to decode body]'
        return None

    def get_response_body(self, response):
        """
        Get response body for logging.
        Only log for certain content types and truncate large responses.
        """
        try:
            content_type = response.get('Content-Type', '')
            
            # Only log JSON and HTML responses
            if 'json' in content_type or 'html' in content_type:
                if hasattr(response, 'content'):
                    content = response.content.decode('utf-8', errors='ignore')
                    
                    # Truncate large responses
                    if len(content) > 5000:
                        return content[:5000] + '... [truncated]'
                    
                    return content
        except Exception:
            pass
        
        return None

    def should_log_request(self, path):
        """
        Determine if a request should be logged.
        Exclude static files, admin media, and other non-essential paths.
        """
        excluded_prefixes = [
            '/static/',
            '/media/',
            '/favicon.ico',
            '/robots.txt',
            '/__debug__/',
        ]
        
        for prefix in excluded_prefixes:
            if path.startswith(prefix):
                return False
        
        return True

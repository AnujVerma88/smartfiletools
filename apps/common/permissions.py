"""
Access Control and Permission Utilities.
Implements permission checks for various resources and features.
"""
from functools import wraps
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import redirect
from django.contrib import messages
from django.core.exceptions import PermissionDenied
import logging

logger = logging.getLogger('apps.common')


def user_owns_conversion(user, conversion):
    """
    Check if user owns a conversion record.
    
    Args:
        user: User object
        conversion: ConversionHistory object
        
    Returns:
        bool: True if user owns the conversion
    """
    if not user.is_authenticated:
        return False
    
    # Check if conversion belongs to user
    if conversion.user_id != user.id:
        logger.warning(
            f"Access denied: User {user.username} attempted to access "
            f"conversion {conversion.id} owned by user {conversion.user_id}"
        )
        return False
    
    return True


def user_owns_api_key(user, api_key):
    """
    Check if user owns an API key.
    
    Args:
        user: User object
        api_key: APIKey object
        
    Returns:
        bool: True if user owns the API key
    """
    if not user.is_authenticated:
        return False
    
    # Check if API key belongs to user's merchant account
    if not hasattr(user, 'api_merchant'):
        return False
    
    if api_key.merchant_id != user.api_merchant.id:
        logger.warning(
            f"Access denied: User {user.username} attempted to access "
            f"API key {api_key.id} owned by merchant {api_key.merchant_id}"
        )
        return False
    
    return True


def require_conversion_ownership(view_func):
    """
    Decorator to ensure user owns the conversion before allowing access.
    Expects conversion_id in URL kwargs.
    
    Usage:
        @require_conversion_ownership
        def download_view(request, conversion_id):
            ...
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        from apps.tools.models import ConversionHistory
        from django.shortcuts import get_object_or_404
        
        # Get conversion_id from kwargs
        conversion_id = kwargs.get('conversion_id')
        if not conversion_id:
            logger.error("require_conversion_ownership: conversion_id not in kwargs")
            return HttpResponseForbidden("Invalid request")
        
        # Get conversion
        try:
            conversion = ConversionHistory.objects.get(id=conversion_id)
        except ConversionHistory.DoesNotExist:
            logger.warning(f"Conversion {conversion_id} not found")
            return HttpResponseForbidden("Conversion not found")
        
        # Check ownership
        if not user_owns_conversion(request.user, conversion):
            messages.error(request, "You don't have permission to access this conversion.")
            return redirect('tools:conversion_history')
        
        # Add conversion to request for convenience
        request.conversion = conversion
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def require_premium(view_func):
    """
    Decorator to ensure user has premium subscription.
    
    Usage:
        @require_premium
        def premium_feature_view(request):
            ...
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Please log in to access this feature.")
            return redirect('accounts:login')
        
        if not request.user.is_premium:
            logger.info(
                f"Premium access denied for user {request.user.username}"
            )
            messages.error(
                request,
                "This feature requires a premium subscription. Please upgrade your account."
            )
            return redirect('dashboard:pricing')
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def require_admin(view_func):
    """
    Decorator to ensure user is admin/staff.
    
    Usage:
        @require_admin
        def admin_view(request):
            ...
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Please log in to access this page.")
            return redirect('accounts:login')
        
        if not request.user.is_staff:
            logger.warning(
                f"Admin access denied for user {request.user.username}"
            )
            messages.error(request, "You don't have permission to access this page.")
            return HttpResponseForbidden("Access denied")
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def require_api_merchant(view_func):
    """
    Decorator to ensure user has an API merchant account.
    
    Usage:
        @require_api_merchant
        def merchant_dashboard_view(request):
            ...
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Please log in to access the merchant dashboard.")
            return redirect('accounts:login')
        
        if not hasattr(request.user, 'api_merchant'):
            logger.info(
                f"API merchant access denied for user {request.user.username} "
                f"(no merchant account)"
            )
            messages.error(
                request,
                "You don't have an API merchant account. Please request API access first."
            )
            return redirect('api:request_access')
        
        if not request.user.api_merchant.is_active:
            logger.warning(
                f"Inactive merchant account access attempt by {request.user.username}"
            )
            messages.error(
                request,
                "Your merchant account is inactive. Please contact support."
            )
            return HttpResponseForbidden("Merchant account inactive")
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


class APIPermissionMixin:
    """
    Mixin for API views to check permissions.
    """
    
    def check_merchant_ownership(self, obj):
        """
        Check if the current merchant owns the object.
        
        Args:
            obj: Object with merchant foreign key
            
        Returns:
            bool: True if merchant owns the object
            
        Raises:
            PermissionDenied: If merchant doesn't own the object
        """
        if not hasattr(self.request, 'api_merchant'):
            raise PermissionDenied("API authentication required")
        
        merchant = self.request.api_merchant
        
        if hasattr(obj, 'merchant_id'):
            if obj.merchant_id != merchant.id:
                logger.warning(
                    f"API access denied: Merchant {merchant.company_name} "
                    f"attempted to access resource owned by merchant {obj.merchant_id}"
                )
                raise PermissionDenied("You don't have permission to access this resource")
        elif hasattr(obj, 'merchant'):
            if obj.merchant.id != merchant.id:
                logger.warning(
                    f"API access denied: Merchant {merchant.company_name} "
                    f"attempted to access resource owned by merchant {obj.merchant.id}"
                )
                raise PermissionDenied("You don't have permission to access this resource")
        
        return True
    
    def check_conversion_ownership(self, conversion):
        """
        Check if the current merchant owns the conversion.
        
        Args:
            conversion: ConversionHistory object
            
        Returns:
            bool: True if merchant owns the conversion
            
        Raises:
            PermissionDenied: If merchant doesn't own the conversion
        """
        if not hasattr(self.request, 'api_merchant'):
            raise PermissionDenied("API authentication required")
        
        merchant = self.request.api_merchant
        
        # Check if conversion was created via API by this merchant
        # This would require adding a merchant field to ConversionHistory
        # For now, we'll check if the conversion's user is linked to the merchant
        if hasattr(conversion, 'api_merchant_id'):
            if conversion.api_merchant_id != merchant.id:
                logger.warning(
                    f"API access denied: Merchant {merchant.company_name} "
                    f"attempted to access conversion {conversion.id}"
                )
                raise PermissionDenied("You don't have permission to access this conversion")
        
        return True


def check_log_viewing_permission(user):
    """
    Check if user has permission to view system logs.
    Only admins can view logs.
    
    Args:
        user: User object
        
    Returns:
        bool: True if user can view logs
    """
    if not user.is_authenticated:
        return False
    
    if not user.is_staff:
        logger.warning(
            f"Log viewing denied for non-admin user: {user.username}"
        )
        return False
    
    return True


def check_api_key_ownership(user, api_key):
    """
    Check if user owns an API key through their merchant account.
    
    Args:
        user: User object
        api_key: APIKey object
        
    Returns:
        bool: True if user owns the API key
    """
    return user_owns_api_key(user, api_key)


def check_premium_feature_access(user, feature_name):
    """
    Check if user has access to a premium feature.
    
    Args:
        user: User object
        feature_name: Name of the feature
        
    Returns:
        bool: True if user has access
    """
    if not user.is_authenticated:
        return False
    
    if not user.is_premium:
        logger.info(
            f"Premium feature '{feature_name}' access denied for user {user.username}"
        )
        return False
    
    return True


def log_access_denied(user, resource_type, resource_id, reason):
    """
    Log access denied events for security monitoring.
    
    Args:
        user: User object (or None for anonymous)
        resource_type: Type of resource (e.g., 'conversion', 'api_key')
        resource_id: ID of the resource
        reason: Reason for denial
    """
    username = user.username if user and user.is_authenticated else 'anonymous'
    
    logger.warning(
        f"ACCESS DENIED: User '{username}' attempted to access {resource_type} "
        f"'{resource_id}' - Reason: {reason}"
    )

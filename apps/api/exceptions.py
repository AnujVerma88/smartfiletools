"""
Custom exception handler for API responses.
Provides consistent error response format across all API endpoints.
"""
from rest_framework.views import exception_handler
from rest_framework.response import Response


def custom_exception_handler(exc, context):
    """
    Custom exception handler that returns consistent error responses.
    
    Format:
    {
        "success": false,
        "data": null,
        "message": "Error message",
        "errors": {
            "code": "ERROR_CODE",
            "details": "Detailed error information",
            "field": "field_name"  # Optional, for validation errors
        }
    }
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)
    
    if response is not None:
        # Customize the response format
        custom_response_data = {
            'success': False,
            'data': None,
            'message': 'An error occurred',
            'errors': {}
        }
        
        # Extract error details
        if isinstance(response.data, dict):
            # Handle validation errors
            if 'detail' in response.data:
                custom_response_data['message'] = str(response.data['detail'])
                custom_response_data['errors'] = {
                    'code': 'VALIDATION_ERROR',
                    'details': str(response.data['detail'])
                }
            else:
                # Handle field-specific validation errors
                custom_response_data['message'] = 'Validation error'
                custom_response_data['errors'] = {
                    'code': 'VALIDATION_ERROR',
                    'details': response.data
                }
        elif isinstance(response.data, list):
            custom_response_data['message'] = str(response.data[0]) if response.data else 'An error occurred'
            custom_response_data['errors'] = {
                'code': 'ERROR',
                'details': response.data
            }
        else:
            custom_response_data['message'] = str(response.data)
            custom_response_data['errors'] = {
                'code': 'ERROR',
                'details': str(response.data)
            }
        
        response.data = custom_response_data
    
    return response


def success_response(data=None, message='Success', status=200):
    """
    Helper function to create consistent success responses.
    
    Args:
        data: Response data (dict, list, or None)
        message: Success message
        status: HTTP status code
    
    Returns:
        Response object with consistent format
    """
    return Response({
        'success': True,
        'data': data,
        'message': message,
        'errors': None
    }, status=status)


def error_response(message='Error', errors=None, status=400):
    """
    Helper function to create consistent error responses.
    
    Args:
        message: Error message
        errors: Error details (dict or None)
        status: HTTP status code
    
    Returns:
        Response object with consistent format
    """
    return Response({
        'success': False,
        'data': None,
        'message': message,
        'errors': errors or {}
    }, status=status)

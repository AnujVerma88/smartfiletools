"""
Email notification utilities for conversion completion.

Feature: conversion-email-notification
"""
import logging
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from apps.common.models import EmailNotification
from apps.tools.models import ConversionHistory

logger = logging.getLogger('apps.tools')


def send_conversion_complete_email(conversion_id: int) -> EmailNotification:
    """
    Send conversion completion email to user and create tracking record.
    
    This function:
    1. Creates an EmailNotification record before sending
    2. Loads conversion and user data
    3. Renders email templates with conversion data
    4. Generates download URL using SITE_URL setting
    5. Sends email using Django's send_mail
    6. Updates EmailNotification status based on result
    7. Implements comprehensive error handling with logging
    
    Args:
        conversion_id: ID of the completed conversion
        
    Returns:
        EmailNotification: The created email notification record with status
        
    Requirements: 1.1, 1.2, 1.3, 4.1, 4.2, 4.3
    """
    try:
        # Load conversion data
        conversion = ConversionHistory.objects.select_related('user').get(id=conversion_id)
        
        # Check if user exists (skip for anonymous users)
        if not conversion.user:
            logger.info(f"Skipping email for conversion {conversion_id}: anonymous user")
            return None
        
        # Check if user has email
        if not conversion.user.email:
            logger.warning(f"Skipping email for conversion {conversion_id}: user has no email")
            return None
        
        # Check if conversion is completed (skip for failed conversions)
        if conversion.status != 'completed':
            logger.info(f"Skipping email for conversion {conversion_id}: status is {conversion.status}")
            return None
        
        # Get user information
        user = conversion.user
        user_name = user.get_full_name() or user.username
        
        # Format conversion type for display
        conversion_type_display = dict(ConversionHistory.TOOL_CHOICES).get(
            conversion.tool_type,
            conversion.tool_type.replace('_', ' ').title()
        )
        
        # Format file sizes
        def format_file_size(size_bytes):
            """Format file size in bytes to human-readable format."""
            if not size_bytes:
                return None
            
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size_bytes < 1024.0:
                    return f"{size_bytes:.2f} {unit}"
                size_bytes /= 1024.0
            return f"{size_bytes:.2f} TB"
        
        file_size_before = format_file_size(conversion.file_size_before)
        file_size_after = format_file_size(conversion.file_size_after)
        
        # Generate download URL
        site_url = settings.SITE_URL.rstrip('/')
        download_url = f"{site_url}/tools/conversion/{conversion.id}/"
        
        # Format completion timestamp
        completed_at = conversion.completed_at or conversion.created_at
        completed_at_formatted = completed_at.strftime('%B %d, %Y at %I:%M %p')
        
        # Get original filename from input_file path
        original_filename = conversion.input_file.name.split('/')[-1] if conversion.input_file else 'file'
        
        # Prepare email context
        context = {
            'user_name': user_name,
            'conversion_type': conversion_type_display,
            'original_filename': original_filename,
            'completed_at': completed_at_formatted,
            'download_url': download_url,
            'file_size_before': file_size_before,
            'file_size_after': file_size_after,
            'site_url': site_url,
        }
        
        # Create email subject
        subject = f"Your {conversion_type_display} conversion is complete!"
        
        # Create EmailNotification record
        email_notification = EmailNotification.objects.create(
            conversion=conversion,
            recipient_email=user.email,
            user=user,
            email_type='conversion_complete',
            subject=subject,
            status='pending'
        )
        
        try:
            # Render email templates
            html_message = render_to_string('emails/conversion_complete.html', context)
            text_message = render_to_string('emails/conversion_complete.txt', context)
            
            # Send email
            send_mail(
                subject=subject,
                message=text_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )
            
            # Mark as sent
            email_notification.mark_as_sent()
            logger.info(
                f"Email sent successfully for conversion {conversion_id} to {user.email}"
            )
            
            return email_notification
            
        except Exception as e:
            # Mark as failed and log error
            error_message = f"{type(e).__name__}: {str(e)}"
            email_notification.mark_as_failed(error_message)
            logger.error(
                f"Failed to send email for conversion {conversion_id}: {error_message}",
                exc_info=True
            )
            
            # Don't raise exception - email failure should not affect conversion
            return email_notification
            
    except ConversionHistory.DoesNotExist:
        logger.error(f"Conversion {conversion_id} not found")
        return None
        
    except Exception as e:
        logger.error(
            f"Unexpected error in send_conversion_complete_email for conversion {conversion_id}: {str(e)}",
            exc_info=True
        )
        return None

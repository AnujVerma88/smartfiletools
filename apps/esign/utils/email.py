from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import logging

logger = logging.getLogger('apps.esign')

def send_otp_email(session, otp_code):
    """
    Send OTP verification code via email
    """
    try:
        subject = settings.ESIGN_OTP_SUBJECT
        
        # Simple text content for now, can be upgraded to HTML template later
        message = f"""
Hello {session.signer_name},

Your verification code for signing "{session.original_filename}" is:

{otp_code}

This code will expire in {settings.ESIGN_OTP_EXPIRY_MINUTES} minutes.

If you didn't request this, please ignore this email.

Best regards,
SmartFileTools Team
"""
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[session.signer_email],
            fail_silently=False,
        )
        
        logger.info(f"OTP email sent to {session.signer_email} for session {session.id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send OTP email to {session.signer_email}: {str(e)}")
        return False

def send_completion_email(session):
    """
    Send completion email with download link
    """
    try:
        subject = settings.ESIGN_COMPLETION_SUBJECT
        
        download_url = f"{settings.SITE_URL}/esign/download/{session.id}/"
        
        message = f"""
Hello {session.signer_name},

Your document "{session.original_filename}" has been successfully signed.

You can download the signed PDF here:
{download_url}

Best regards,
SmartFileTools Team
"""
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[session.signer_email],
            fail_silently=False,
        )
        
        logger.info(f"Completion email sent to {session.signer_email} for session {session.id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send completion email to {session.signer_email}: {str(e)}")
        return False

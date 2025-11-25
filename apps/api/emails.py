"""
Email utilities for API access requests and merchant notifications.
"""
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.auth import get_user_model
import logging

logger = logging.getLogger('apps.api')

User = get_user_model()


def send_api_access_request_confirmation(request_obj):
    """
    Send confirmation email to requester after submitting API access request.
    
    Args:
        request_obj: APIAccessRequest instance
    """
    try:
        subject = 'API Access Request Received - SmartToolPDF'
        
        # Render email content
        html_message = render_to_string('api/emails/access_request_confirmation.html', {
            'full_name': request_obj.full_name,
            'company_name': request_obj.company_name,
            'request_id': request_obj.id,
        })
        
        plain_message = f"""
Dear {request_obj.full_name},

Thank you for your interest in SmartToolPDF API!

We have received your API access request for {request_obj.company_name}.

Our team will review your application and get back to you within 1-2 business days.

Request Details:
- Company: {request_obj.company_name}
- Email: {request_obj.email}
- Request ID: #{request_obj.id}

If you have any questions in the meantime, please don't hesitate to contact us.

Best regards,
The SmartToolPDF Team
https://smarttoolpdf.com
        """.strip()
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@smarttoolpdf.com',
            recipient_list=[request_obj.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Confirmation email sent to {request_obj.email} for request #{request_obj.id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send confirmation email to {request_obj.email}: {str(e)}")
        return False


def send_api_access_request_notification_to_admins(request_obj):
    """
    Send notification email to admins when a new API access request is submitted.
    
    Args:
        request_obj: APIAccessRequest instance
    """
    try:
        # Get all admin/staff users
        admin_emails = User.objects.filter(
            is_staff=True,
            is_active=True
        ).values_list('email', flat=True)
        
        if not admin_emails:
            logger.warning("No admin emails found to send API access request notification")
            return False
        
        subject = f'New API Access Request from {request_obj.company_name}'
        
        # Render email content
        html_message = render_to_string('api/emails/access_request_admin_notification.html', {
            'request': request_obj,
            'admin_url': f'/admin/api/apiaccessrequest/{request_obj.id}/change/',
        })
        
        plain_message = f"""
New API Access Request Received

Company: {request_obj.company_name}
Contact: {request_obj.full_name}
Email: {request_obj.email}
Phone: {request_obj.phone_number or 'Not provided'}
Website: {request_obj.company_website or 'Not provided'}

Use Case:
{request_obj.use_case}

Estimated Monthly Volume: {request_obj.estimated_monthly_volume:,} requests

Request ID: #{request_obj.id}
Submitted: {request_obj.created_at.strftime('%Y-%m-%d %H:%M:%S')}

Review this request in the admin panel:
{settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://localhost:8000'}/admin/api/apiaccessrequest/{request_obj.id}/change/
        """.strip()
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@smarttoolpdf.com',
            recipient_list=list(admin_emails),
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Admin notification sent for API access request #{request_obj.id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send admin notification for request #{request_obj.id}: {str(e)}")
        return False


def send_api_access_approved_email(request_obj, api_key, api_secret):
    """
    Send email to requester when their API access is approved.
    Includes API credentials (sent only once).
    
    Args:
        request_obj: APIAccessRequest instance
        api_key: Plain text API key
        api_secret: Plain text API secret
    """
    try:
        subject = 'API Access Approved - Your SmartToolPDF API Credentials'
        
        # Render email content
        html_message = render_to_string('api/emails/access_approved.html', {
            'full_name': request_obj.full_name,
            'company_name': request_obj.company_name,
            'api_key': api_key,
            'api_secret': api_secret,
            'merchant': request_obj.merchant,
        })
        
        plain_message = f"""
Dear {request_obj.full_name},

Great news! Your API access request has been approved.

Your API Credentials:
API Key: {api_key}
API Secret: {api_secret}

IMPORTANT: Please save these credentials securely. For security reasons, we cannot retrieve your API secret after this email.

Getting Started:
1. Visit our API documentation: https://smarttoolpdf.com/api/docs/
2. Review the authentication guide
3. Start integrating our API into your application

Your current plan: {request_obj.merchant.plan}
Monthly request limit: {request_obj.merchant.monthly_request_limit:,} requests

Manage your API keys and view usage statistics in your merchant dashboard:
https://smarttoolpdf.com/merchant/dashboard/

If you have any questions or need assistance, please contact our support team.

Welcome to SmartToolPDF API!

Best regards,
The SmartToolPDF Team
https://smarttoolpdf.com
        """.strip()
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@smarttoolpdf.com',
            recipient_list=[request_obj.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Approval email with credentials sent to {request_obj.email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send approval email to {request_obj.email}: {str(e)}")
        return False


def send_api_access_rejected_email(request_obj):
    """
    Send email to requester when their API access is rejected.
    
    Args:
        request_obj: APIAccessRequest instance
    """
    try:
        subject = 'API Access Request Update - SmartToolPDF'
        
        # Render email content
        html_message = render_to_string('api/emails/access_rejected.html', {
            'full_name': request_obj.full_name,
            'company_name': request_obj.company_name,
            'rejection_reason': request_obj.rejection_reason,
        })
        
        plain_message = f"""
Dear {request_obj.full_name},

Thank you for your interest in SmartToolPDF API.

After reviewing your application, we are unable to approve your API access request at this time.

{f'Reason: {request_obj.rejection_reason}' if request_obj.rejection_reason else ''}

If you have any questions or would like to discuss this decision, please contact our support team at support@smarttoolpdf.com.

You are welcome to submit a new request in the future if your use case changes.

Best regards,
The SmartToolPDF Team
https://smarttoolpdf.com
        """.strip()
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@smarttoolpdf.com',
            recipient_list=[request_obj.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Rejection email sent to {request_obj.email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send rejection email to {request_obj.email}: {str(e)}")
        return False



def send_plan_change_confirmation(merchant, old_plan, new_plan, billing_info):
    """
    Send email confirmation when merchant changes subscription plan.
    
    Args:
        merchant: APIMerchant instance
        old_plan: str - Previous plan name
        new_plan: str - New plan name
        billing_info: dict - Billing information
    """
    try:
        subject = f'Subscription Plan Changed - SmartToolPDF'
        
        # Determine if upgrade or downgrade
        plan_order = ['free', 'starter', 'professional', 'enterprise']
        is_upgrade = plan_order.index(new_plan) > plan_order.index(old_plan)
        change_type = 'upgraded' if is_upgrade else 'downgraded'
        
        plain_message = f"""
Dear {merchant.company_name},

Your subscription plan has been {change_type} successfully!

Plan Change Details:
- Previous Plan: {old_plan.title()}
- New Plan: {new_plan.title()}
- Effective: Immediately

Billing Information:
- New Monthly Price: ${billing_info['new_price']}
- Prorated Charge: ${billing_info['prorated_charge']}
- Credit Applied: ${billing_info['credit']}
- Next Billing Date: {billing_info['next_billing_date']}

Your new usage limits:
- Monthly Requests: {billing_info.get('monthly_requests', 'Check dashboard')}
- Rate Limit: {billing_info.get('per_minute', 'Check dashboard')} requests/minute

You can view your updated plan details in your merchant dashboard:
https://smarttoolpdf.com/merchant/dashboard/

If you have any questions, please contact our support team.

Best regards,
The SmartToolPDF Team
https://smarttoolpdf.com
        """.strip()
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@smarttoolpdf.com',
            recipient_list=[merchant.contact_email],
            fail_silently=False,
        )
        
        logger.info(f"Plan change confirmation email sent to {merchant.contact_email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send plan change email to {merchant.contact_email}: {str(e)}")
        return False

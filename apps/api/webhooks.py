"""
Webhook Delivery System.
Handles webhook notifications to merchants when conversions complete.
"""
import hmac
import hashlib
import json
import requests
from django.utils import timezone
from datetime import timedelta
from celery import shared_task
from .models import WebhookDelivery, APIMerchant
import logging

logger = logging.getLogger('apps.api')


def generate_webhook_signature(payload, secret):
    """
    Generate HMAC-SHA256 signature for webhook payload.
    
    Args:
        payload: dict - Webhook payload data
        secret: str - Merchant's webhook secret
    
    Returns:
        str: Hex digest of HMAC signature
    """
    # Convert payload to JSON string with sorted keys for consistency
    message = json.dumps(payload, sort_keys=True).encode('utf-8')
    
    # Generate HMAC signature
    signature = hmac.new(
        secret.encode('utf-8'),
        message,
        hashlib.sha256
    ).hexdigest()
    
    return signature


def verify_webhook_signature(payload, signature, secret):
    """
    Verify webhook signature.
    
    Args:
        payload: dict - Webhook payload data
        signature: str - Provided signature
        secret: str - Merchant's webhook secret
    
    Returns:
        bool: True if signature is valid
    """
    expected_signature = generate_webhook_signature(payload, secret)
    return hmac.compare_digest(signature, expected_signature)


def create_webhook_payload(conversion):
    """
    Create webhook payload for a conversion.
    
    Args:
        conversion: ConversionHistory instance
    
    Returns:
        dict: Webhook payload
    """
    payload = {
        'event': f'conversion.{conversion.status}',
        'conversion_id': str(conversion.id),
        'status': conversion.status,
        'tool_type': conversion.tool_type,
        'created_at': conversion.created_at.isoformat(),
        'completed_at': conversion.completed_at.isoformat() if conversion.completed_at else None,
        'processing_time': conversion.processing_time,
    }
    
    # Add input file info
    if conversion.input_file:
        payload['input_file'] = {
            'name': conversion.input_file.name.split('/')[-1],
            'size': conversion.file_size_before,
        }
    
    # Add output file info if completed
    if conversion.status == 'completed' and conversion.output_file:
        payload['output_file'] = {
            'name': conversion.output_file.name.split('/')[-1],
            'size': conversion.file_size_after,
            'download_url': f'/api/v1/conversions/{conversion.id}/download/',
            # Files expire after 24 hours
            'expires_at': (timezone.now() + timedelta(hours=24)).isoformat(),
        }
    
    # Add error info if failed
    if conversion.status == 'failed' and conversion.error_message:
        payload['error'] = {
            'message': conversion.error_message,
        }
    
    return payload


def trigger_webhook(conversion, merchant=None):
    """
    Trigger webhook delivery for a conversion.
    
    Args:
        conversion: ConversionHistory instance
        merchant: APIMerchant instance (optional, will be fetched if not provided)
    
    Returns:
        WebhookDelivery instance or None
    """
    # Get merchant if not provided
    if merchant is None:
        # Try to get merchant from conversion user
        if hasattr(conversion.user, 'api_merchant'):
            merchant = conversion.user.api_merchant
        else:
            logger.warning(f"No merchant found for conversion {conversion.id}")
            return None
    
    # Check if webhooks are enabled
    if not merchant.webhook_enabled or not merchant.webhook_url:
        logger.debug(f"Webhooks not enabled for merchant {merchant.company_name}")
        return None
    
    # Create webhook payload
    payload = create_webhook_payload(conversion)
    
    # Generate signature
    signature = generate_webhook_signature(payload, merchant.webhook_secret)
    
    # Create webhook delivery record
    webhook = WebhookDelivery.objects.create(
        merchant=merchant,
        conversion=conversion,
        webhook_url=merchant.webhook_url,
        payload=payload,
        signature=signature,
        status='pending',
    )
    
    logger.info(
        f"Created webhook delivery #{webhook.id} for conversion {conversion.id} "
        f"to {merchant.company_name}"
    )
    
    # Queue webhook delivery task
    deliver_webhook.delay(webhook.id)
    
    return webhook


@shared_task(bind=True, max_retries=3)
def deliver_webhook(self, webhook_id):
    """
    Celery task to deliver webhook to merchant.
    
    Args:
        webhook_id: WebhookDelivery ID
    """
    try:
        webhook = WebhookDelivery.objects.get(id=webhook_id)
    except WebhookDelivery.DoesNotExist:
        logger.error(f"Webhook {webhook_id} not found")
        return
    
    # Check if already delivered
    if webhook.status == 'success':
        logger.info(f"Webhook {webhook_id} already delivered")
        return
    
    # Check if max attempts reached
    if webhook.attempt_count >= webhook.max_attempts:
        logger.warning(f"Webhook {webhook_id} max attempts reached")
        webhook.status = 'failed'
        webhook.save()
        return
    
    # Increment attempt count
    webhook.attempt_count += 1
    webhook.status = 'retrying' if webhook.attempt_count > 1 else 'pending'
    webhook.save()
    
    logger.info(
        f"Delivering webhook {webhook_id} (attempt {webhook.attempt_count}/{webhook.max_attempts})"
    )
    
    try:
        # Prepare headers
        headers = {
            'Content-Type': 'application/json',
            'X-Webhook-Signature': webhook.signature,
            'X-Webhook-Event': webhook.payload.get('event', 'conversion.completed'),
            'User-Agent': 'SmartToolPDF-Webhook/1.0',
        }
        
        # Send POST request
        response = requests.post(
            webhook.webhook_url,
            json=webhook.payload,
            headers=headers,
            timeout=30,  # 30 second timeout
        )
        
        # Check response
        if 200 <= response.status_code < 300:
            # Success
            webhook.mark_success(response.status_code, response.text[:1000])
            logger.info(
                f"Webhook {webhook_id} delivered successfully: {response.status_code}"
            )
        else:
            # Failed
            error_msg = f"HTTP {response.status_code}: {response.text[:500]}"
            webhook.mark_failed(error_msg, response.status_code, response.text[:1000])
            logger.warning(f"Webhook {webhook_id} failed: {error_msg}")
            
            # Retry if attempts remaining
            if webhook.attempt_count < webhook.max_attempts:
                # Calculate retry delay with exponential backoff
                delay = 2 ** webhook.attempt_count * 60  # 2, 4, 8 minutes
                logger.info(f"Retrying webhook {webhook_id} in {delay} seconds")
                self.retry(countdown=delay)
    
    except requests.exceptions.Timeout:
        error_msg = "Request timeout after 30 seconds"
        webhook.mark_failed(error_msg)
        logger.warning(f"Webhook {webhook_id} timeout")
        
        # Retry if attempts remaining
        if webhook.attempt_count < webhook.max_attempts:
            delay = 2 ** webhook.attempt_count * 60
            self.retry(countdown=delay)
    
    except requests.exceptions.RequestException as e:
        error_msg = f"Request error: {str(e)}"
        webhook.mark_failed(error_msg)
        logger.error(f"Webhook {webhook_id} request error: {str(e)}")
        
        # Retry if attempts remaining
        if webhook.attempt_count < webhook.max_attempts:
            delay = 2 ** webhook.attempt_count * 60
            self.retry(countdown=delay)
    
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        webhook.mark_failed(error_msg)
        logger.error(f"Webhook {webhook_id} unexpected error: {str(e)}", exc_info=True)


@shared_task
def retry_failed_webhooks():
    """
    Celery task to retry failed webhooks that are due for retry.
    Runs periodically to handle retries.
    """
    from django.db import models
    
    logger.info("Checking for webhooks to retry...")
    
    # Get webhooks that are due for retry
    now = timezone.now()
    webhooks = WebhookDelivery.objects.filter(
        status='retrying',
        next_retry_at__lte=now,
        attempt_count__lt=models.F('max_attempts')
    )
    
    retry_count = 0
    for webhook in webhooks:
        logger.info(f"Retrying webhook {webhook.id}")
        deliver_webhook.delay(webhook.id)
        retry_count += 1
    
    logger.info(f"Queued {retry_count} webhooks for retry")
    
    return {
        'retry_count': retry_count,
        'timestamp': now.isoformat(),
    }


def test_webhook(merchant, test_payload=None):
    """
    Send a test webhook to merchant's webhook URL.
    
    Args:
        merchant: APIMerchant instance
        test_payload: dict (optional) - Custom test payload
    
    Returns:
        dict: Test result with status and details
    """
    if not merchant.webhook_url:
        return {
            'success': False,
            'error': 'No webhook URL configured',
        }
    
    # Create test payload
    if test_payload is None:
        test_payload = {
            'event': 'webhook.test',
            'message': 'This is a test webhook from SmartToolPDF',
            'merchant_id': merchant.id,
            'merchant_name': merchant.company_name,
            'timestamp': timezone.now().isoformat(),
        }
    
    # Generate signature
    signature = generate_webhook_signature(test_payload, merchant.webhook_secret)
    
    try:
        # Send test webhook
        headers = {
            'Content-Type': 'application/json',
            'X-Webhook-Signature': signature,
            'X-Webhook-Event': 'webhook.test',
            'User-Agent': 'SmartToolPDF-Webhook/1.0',
        }
        
        response = requests.post(
            merchant.webhook_url,
            json=test_payload,
            headers=headers,
            timeout=10,
        )
        
        if 200 <= response.status_code < 300:
            logger.info(f"Test webhook successful for {merchant.company_name}")
            return {
                'success': True,
                'status_code': response.status_code,
                'response': response.text[:500],
                'message': 'Test webhook delivered successfully',
            }
        else:
            logger.warning(
                f"Test webhook failed for {merchant.company_name}: {response.status_code}"
            )
            return {
                'success': False,
                'status_code': response.status_code,
                'response': response.text[:500],
                'error': f'Webhook endpoint returned {response.status_code}',
            }
    
    except requests.exceptions.Timeout:
        logger.warning(f"Test webhook timeout for {merchant.company_name}")
        return {
            'success': False,
            'error': 'Request timeout after 10 seconds',
        }
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Test webhook error for {merchant.company_name}: {str(e)}")
        return {
            'success': False,
            'error': f'Request error: {str(e)}',
        }
    
    except Exception as e:
        logger.error(
            f"Test webhook unexpected error for {merchant.company_name}: {str(e)}",
            exc_info=True
        )
        return {
            'success': False,
            'error': f'Unexpected error: {str(e)}',
        }

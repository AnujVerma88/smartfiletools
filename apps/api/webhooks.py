"""
Webhook Delivery System.
Handles webhook notifications to merchants when conversions or e-sign sessions complete.
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
    """
    expected_signature = generate_webhook_signature(payload, secret)
    return hmac.compare_digest(signature, expected_signature)


def create_webhook_payload(obj):
    """
    Create webhook payload for a conversion or sign session.
    """
    from apps.tools.models import ConversionHistory
    from apps.esign.models import SignSession

    if isinstance(obj, ConversionHistory):
        payload = {
            'event': f'conversion.{obj.status}',
            'conversion_id': str(obj.id),
            'status': obj.status,
            'tool_type': obj.tool_type,
            'created_at': obj.created_at.isoformat(),
            'completed_at': obj.completed_at.isoformat() if obj.completed_at else None,
            'processing_time': obj.processing_time,
        }
        
        # Add input file info
        if obj.input_file:
            payload['input_file'] = {
                'name': obj.input_file.name.split('/')[-1],
                'size': obj.file_size_before,
            }
        
        # Add output file info if completed
        if obj.status == 'completed' and obj.output_file:
            payload['output_file'] = {
                'name': obj.output_file.name.split('/')[-1],
                'size': obj.file_size_after,
                'download_url': f'/api/v1/conversions/{obj.id}/download/',
                'expires_at': (timezone.now() + timedelta(hours=24)).isoformat(),
            }
        
        # Add error info if failed
        if obj.status == 'failed' and obj.error_message:
            payload['error'] = {'message': obj.error_message}
            
        return payload

    elif isinstance(obj, SignSession):
        payload = {
            'event': f'esign.{obj.status}',
            'session_id': str(obj.id),
            'status': obj.status,
            'signer_email': obj.signer_email,
            'signer_name': obj.signer_name,
            'created_at': obj.created_at.isoformat(),
            'signed_at': obj.signed_at.isoformat() if obj.signed_at else None,
        }

        if obj.status == 'signed' and obj.signed_pdf:
             import base64
             try:
                 obj.signed_pdf.open('rb')
                 pdf_content = obj.signed_pdf.read()
                 pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
                 obj.signed_pdf.close()
             except Exception:
                 pdf_base64 = None
                 
             payload['signed_file'] = {
                'name': obj.original_filename, # Or signed filename
                'download_url': f'/api/v1/esign/download/{obj.id}/',
                'expires_at': obj.expires_at.isoformat(),
                'content_base64': pdf_base64
            }
        
        return payload
    
    return {}


def trigger_webhook(obj, merchant=None):
    """
    Trigger webhook delivery for a conversion or sign session.
    """
    from apps.tools.models import ConversionHistory
    from apps.esign.models import SignSession

    # Get merchant if not provided
    if merchant is None:
        if obj.user and hasattr(obj.user, 'api_merchant'):
            merchant = obj.user.api_merchant
        # Start of fix for external users
        elif isinstance(obj, SignSession) and obj.metadata.get('merchant_id'):
            # Fallback for API sessions where user might be generic or session is owned by someone else
            try:
                merchant = APIMerchant.objects.get(id=obj.metadata.get('merchant_id'))
            except APIMerchant.DoesNotExist:
                logger.warning(f"Merchant ID {obj.metadata.get('merchant_id')} not found for session {obj.id}")
                return None
        # End of fix
        else:
            logger.warning(f"No merchant found for object {obj.id} (Metadata: {getattr(obj, 'metadata', {})})")
            return None
    
    # Check if webhooks are enabled
    if not merchant.webhook_enabled or not merchant.webhook_url:
        logger.debug(f"Webhooks not enabled for merchant {merchant.company_name}")
        return None
    
    # Create webhook payload
    payload = create_webhook_payload(obj)
    
    # Generate signature
    signature = generate_webhook_signature(payload, merchant.webhook_secret)
    
    # Create webhook delivery record
    webhook_kwargs = {
        'merchant': merchant,
        'webhook_url': merchant.webhook_url,
        'payload': payload,
        'signature': signature,
        'status': 'pending',
    }

    if isinstance(obj, ConversionHistory):
        webhook_kwargs['conversion'] = obj
    elif isinstance(obj, SignSession):
        webhook_kwargs['sign_session'] = obj

    webhook = WebhookDelivery.objects.create(**webhook_kwargs)
    
    # Prepare payload for logging (truncate base64)
    log_payload = payload.copy()
    if 'signed_file' in log_payload and 'content_base64' in log_payload['signed_file']:
        b64_len = len(log_payload['signed_file']['content_base64'] or '')
        log_payload['signed_file']['content_base64'] = f"<Base64 Data: {b64_len} chars truncated>"

    logger.info("="*50)
    logger.info(f"WEBHOOK TRIGGERED & STORED IN MODEL (ID: {webhook.id})")
    logger.info(f"Target URL: {merchant.webhook_url}")
    logger.info(f"Payload Preview: {json.dumps(log_payload, indent=2)}")
    logger.info("="*50)
    
    # Queue webhook delivery task
    deliver_webhook.delay(webhook.id)
    
    return webhook


@shared_task(bind=True, max_retries=3)
def deliver_webhook(self, webhook_id):
    """
    Celery task to deliver webhook to merchant.
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
            'X-Webhook-Event': webhook.payload.get('event', 'unknown'),
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

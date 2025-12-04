"""
Celery tasks for E-Sign PDF processing.
Following the same pattern as apps.tools.tasks
"""
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import SignSession, AuditEvent
import logging

logger = logging.getLogger('apps.esign')


@shared_task(bind=True, max_retries=3)
def process_signed_pdf(self, session_id):
    """
    Process and embed signatures into PDF.
    Similar to apps.tools.tasks.process_conversion
    
    This task:
    1. Loads the original PDF
    2. Embeds all signatures
    3. Adds audit page
    4. Saves signed PDF
    5. Updates session status
    
    Args:
        session_id: UUID of the SignSession
    
    Returns:
        dict: Result with status and metadata
    """
    try:
        session = SignSession.objects.get(id=session_id)
        session.status = 'signing'
        session.celery_task_id = self.request.id if self.request.id else ''
        session.save()
        
        # Create audit event
        AuditEvent.objects.create(
            session=session,
            event_type='pdf_signing_started',
            payload={'task_id': self.request.id or 'direct'}
        )
        
        logger.info(f"Starting PDF signing for session {session_id}")
        
        # Process PDF
        from .utils.pdf_processor import PDFProcessor
        from django.core.files import File
        import os
        
        processor = PDFProcessor(file_path=session.original_pdf.path)
        
        # Embed signatures
        signatures = session.signatures.filter(field__isnull=False)
        audit_signatures = []
        
        for sig in signatures:
            field = sig.field
            processor.embed_signature(
                signature_image_path=sig.signature_image.path,
                page_num=field.page_number,
                x=field.x,
                y=field.y,
                width=field.width,
                height=field.height
            )
            
            audit_signatures.append({
                'signer': sig.signer_name,
                'email': sig.signer_email,
                'signed_at': sig.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'ip_address': sig.ip_address,
                'id': str(sig.id)
            })
            
        # Add audit page
        audit_data = {
            'session_id': str(session.id),
            'status': 'Completed',
            'created_at': session.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'signer_name': session.signer_name,
            'signer_email': session.signer_email,
            'original_hash': session.original_pdf_hash or 'N/A',
            'signatures': audit_signatures,
            'events': [
                {
                    'timestamp': e.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'type': e.event_type
                } for e in session.audit_events.all().order_by('created_at')
            ]
        }
        # Store audit trail in database instead of adding to PDF
        session.audit_trail_data = audit_data
        session.save(update_fields=['audit_trail_data'])
        
        # Save signed PDF
        output_filename = f"signed_{session.original_filename}"
        output_content = processor.save()
        
        # Save to model
        from django.core.files.base import ContentFile
        session.signed_pdf.save(output_filename, ContentFile(output_content), save=False)
        
        # Calculate hash
        # session.signed_pdf_hash = ... (can do this later)
        
        session.status = 'signed'
        session.signed_at = timezone.now()
        session.save()
        
        processor.close()
        
        # Create audit event
        AuditEvent.objects.create(
            session=session,
            event_type='pdf_signed',
            payload={
                'signed_at': session.signed_at.isoformat()
            }
        )
        
        logger.info(f"Successfully processed signed PDF for session {session_id}")
        
        # Trigger Webhook
        try:
            from apps.api.webhooks import trigger_webhook
            trigger_webhook(session)
        except Exception as e:
            logger.error(f"Failed to trigger webhook for session {session_id}: {str(e)}")

        return {
            'status': 'success',
            'session_id': str(session_id),
            'signed_at': session.signed_at.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error processing signed PDF for session {session_id}: {str(e)}")
        
        try:
            session = SignSession.objects.get(id=session_id)
            session.status = 'failed'
            session.error_message = str(e)
            session.save()
            
            AuditEvent.objects.create(
                session=session,
                event_type='pdf_signing_failed',
                payload={'error': str(e)}
            )
        except:
            pass
        
        raise self.retry(exc=e, countdown=60)


@shared_task
def cleanup_expired_sessions():
    """
    Cleanup expired signing sessions.
    Similar to apps.tools.tasks.cleanup_old_files
    Run daily via Celery Beat.
    """
    expired_sessions = SignSession.objects.filter(
        expires_at__lt=timezone.now(),
        status__in=['created', 'otp_sent', 'otp_verified', 'signing']
    )
    
    count = 0
    for session in expired_sessions:
        session.status = 'expired'
        session.save()
        
        AuditEvent.objects.create(
            session=session,
            event_type='session_expired',
            payload={'expired_at': timezone.now().isoformat()}
        )
        count += 1
    
    logger.info(f"Marked {count} sessions as expired")
    return count


@shared_task
def cleanup_old_esign_files():
    """
    Delete old signed PDFs and signatures based on retention policy.
    Similar to apps.tools.tasks.cleanup_old_files
    Run daily via Celery Beat.
    """
    from django.conf import settings
    
    retention_days = getattr(settings, 'ESIGN_RETENTION_DAYS', 90)
    cutoff_date = timezone.now() - timedelta(days=retention_days)
    
    old_sessions = SignSession.objects.filter(
        created_at__lt=cutoff_date,
        status='signed'
    )
    
    count = 0
    for session in old_sessions:
        # Delete files
        if session.original_pdf:
            try:
                session.original_pdf.delete(save=False)
            except:
                pass
        
        if session.signed_pdf:
            try:
                session.signed_pdf.delete(save=False)
            except:
                pass
        
        # Delete signature images
        for signature in session.signatures.all():
            if signature.signature_image:
                try:
                    signature.signature_image.delete(save=False)
                except:
                    pass
        
        count += 1
    
    logger.info(f"Cleaned up {count} old signing sessions")
    return count

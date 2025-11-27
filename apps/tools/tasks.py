"""
Celery tasks for file conversion and processing.
"""
import os
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from celery import shared_task
from django.conf import settings
from django.utils import timezone


from .models import ConversionHistory
from apps.common.models import ConversionLog
from .utils.converter_factory import get_converter
from .utils.base_converter import ConversionError

logger = logging.getLogger('apps.tools')


@shared_task(bind=True, max_retries=3)
def process_conversion(self, conversion_id):
    """
    Asynchronous task to process file conversion.
    Updates ConversionHistory status throughout the process.
    
    Args:
        conversion_id: ID of the ConversionHistory record
        
    Returns:
        dict: Result with status and metadata
    """
    conversion = None
    start_time = time.time()
    
    try:
        # Retrieve conversion record
        conversion = ConversionHistory.objects.get(id=conversion_id)
        
        # Update status to processing
        conversion.status = 'processing'
        conversion.celery_task_id = self.request.id
        conversion.save()
        
        # Log conversion start
        ConversionLog.objects.create(
            conversion=conversion,
            action='started',
            message=f'Conversion started for {conversion.tool_type}',
            metadata={'task_id': self.request.id}
        )
        
        logger.info(f"Starting conversion {conversion_id}: {conversion.tool_type}")
        
        # Get appropriate converter
        converter = get_converter(conversion.tool_type)
        
        # Prepare input and output paths
        input_path = conversion.input_file.path
        output_dir = Path(settings.MEDIA_ROOT) / 'output' / datetime.now().strftime('%Y/%m/%d')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Prepare output path
        output_path = converter.prepare_output_path(input_path, output_dir)
        
        # Log processing
        ConversionLog.objects.create(
            conversion=conversion,
            action='processing',
            message=f'Processing file with {converter.__class__.__name__}',
            metadata={
                'input_path': input_path,
                'output_path': output_path,
            }
        )
        
        # Perform conversion
        result = converter.convert(input_path, output_path)
        
        # Update conversion record with results using atomic transaction
        from django.db import transaction
        
        logger.info(f"Updating conversion {conversion_id} status to completed...")
        
        with transaction.atomic():
            # Get fresh instance from database
            conversion = ConversionHistory.objects.select_for_update().get(id=conversion_id)
            
            conversion.output_file.name = os.path.relpath(output_path, settings.MEDIA_ROOT)
            conversion.status = 'completed'
            conversion.processing_time = time.time() - start_time
            conversion.completed_at = timezone.now()
            
            # Update file sizes
            if 'input_info' in result:
                conversion.file_size_before = result['input_info']['size']
            if 'output_info' in result:
                conversion.file_size_after = result['output_info']['size']
            
            conversion.save()
            
        logger.info(f"Conversion {conversion_id} status updated to: {conversion.status}")
        
        # Log completion
        ConversionLog.objects.create(
            conversion=conversion,
            action='completed',
            message=f'Conversion completed successfully',
            metadata={
                'duration': conversion.processing_time,
                'output_size': conversion.file_size_after,
            }
        )
        
        logger.info(
            f"Conversion {conversion_id} completed successfully in "
            f"{conversion.processing_time:.2f}s"
        )
        
        # Send email notification for authenticated users
        try:
            from apps.tools.utils.email_notifications import send_conversion_complete_email
            
            if conversion.user:
                logger.info(f"Attempting to send email notification for conversion {conversion_id}")
                email_notification = send_conversion_complete_email(conversion_id)
                
                if email_notification and email_notification.status == 'sent':
                    logger.info(
                        f"Email notification sent successfully to {conversion.user.email} "
                        f"for conversion {conversion_id}"
                    )
                elif email_notification and email_notification.status == 'failed':
                    logger.error(
                        f"Email notification failed for conversion {conversion_id}: "
                        f"{email_notification.error_message}"
                    )
                else:
                    logger.info(f"Email notification skipped for conversion {conversion_id}")
            else:
                logger.debug(f"Skipping email notification for anonymous conversion {conversion_id}")
        except Exception as e:
            # Email failures should not affect conversion status
            logger.error(
                f"Error sending email notification for conversion {conversion_id}: {str(e)}",
                exc_info=True
            )
        
        return {
            'status': 'success',
            'conversion_id': conversion_id,
            'output_path': output_path,
            'duration': conversion.processing_time,
        }
        
    except ConversionHistory.DoesNotExist:
        logger.error(f"Conversion {conversion_id} not found")
        return {
            'status': 'error',
            'conversion_id': conversion_id,
            'error': 'Conversion record not found',
        }
        
    except ConversionError as e:
        # Handle conversion-specific errors
        error_msg = str(e)
        logger.error(f"Conversion {conversion_id} failed: {error_msg}")
        
        if conversion:
            conversion.status = 'failed'
            conversion.error_message = error_msg
            conversion.processing_time = time.time() - start_time
            conversion.save()
            
            ConversionLog.objects.create(
                conversion=conversion,
                action='failed',
                message=f'Conversion failed: {error_msg}',
                metadata={'error_type': 'ConversionError'}
            )
        
        return {
            'status': 'error',
            'conversion_id': conversion_id,
            'error': error_msg,
        }
        
    except Exception as e:
        # Handle unexpected errors
        error_msg = str(e)
        logger.exception(f"Unexpected error in conversion {conversion_id}: {error_msg}")
        
        if conversion:
            conversion.status = 'failed'
            conversion.error_message = f"Unexpected error: {error_msg}"
            conversion.processing_time = time.time() - start_time
            conversion.save()
            
            ConversionLog.objects.create(
                conversion=conversion,
                action='failed',
                message=f'Unexpected error: {error_msg}',
                metadata={'error_type': type(e).__name__}
            )
        
        # Retry the task if retries are available
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))
        
        return {
            'status': 'error',
            'conversion_id': conversion_id,
            'error': error_msg,
        }


@shared_task
def cleanup_old_files():
    """
    Celery scheduled task to delete old files from temp and output directories.
    Deletes files older than FILE_CLEANUP_AGE_HOURS (default 24 hours).
    """
    logger.info("Starting file cleanup task")
    
    cleanup_age_hours = getattr(settings, 'FILE_CLEANUP_AGE_HOURS', 24)
    cutoff_time = timezone.now() - timedelta(hours=cleanup_age_hours)
    
    deleted_count = 0
    error_count = 0
    
    # Directories to clean
    cleanup_dirs = [
        Path(settings.MEDIA_ROOT) / 'temp',
        Path(settings.MEDIA_ROOT) / 'uploads',
        Path(settings.MEDIA_ROOT) / 'output',
    ]
    
    for directory in cleanup_dirs:
        if not directory.exists():
            continue
        
        logger.info(f"Cleaning directory: {directory}")
        
        # Walk through directory recursively
        for file_path in directory.rglob('*'):
            if not file_path.is_file():
                continue
            
            try:
                # Check file modification time
                file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                file_mtime = timezone.make_aware(file_mtime)
                
                if file_mtime < cutoff_time:
                    file_size = file_path.stat().st_size
                    file_path.unlink()
                    deleted_count += 1
                    logger.debug(
                        f"Deleted old file: {file_path} "
                        f"(size: {file_size} bytes, age: {timezone.now() - file_mtime})"
                    )
            
            except Exception as e:
                error_count += 1
                logger.error(f"Error deleting file {file_path}: {str(e)}")
    
    logger.info(
        f"File cleanup completed: {deleted_count} files deleted, "
        f"{error_count} errors"
    )
    
    return {
        'deleted_count': deleted_count,
        'error_count': error_count,
        'cleanup_age_hours': cleanup_age_hours,
    }


@shared_task
def cleanup_old_logs():
    """
    Celery scheduled task to delete old log entries from database.
    Deletes RequestLog entries older than 30 days and ConversionLog older than 60 days.
    """
    logger.info("Starting log cleanup task")
    
    from apps.common.models import RequestLog
    
    # Delete old RequestLog entries (30 days)
    request_log_cutoff = timezone.now() - timedelta(days=30)
    request_logs_deleted = RequestLog.objects.filter(
        created_at__lt=request_log_cutoff
    ).delete()[0]
    
    # Delete old ConversionLog entries (60 days)
    conversion_log_cutoff = timezone.now() - timedelta(days=60)
    conversion_logs_deleted = ConversionLog.objects.filter(
        created_at__lt=conversion_log_cutoff
    ).delete()[0]
    
    logger.info(
        f"Log cleanup completed: {request_logs_deleted} request logs deleted, "
        f"{conversion_logs_deleted} conversion logs deleted"
    )
    
    return {
        'request_logs_deleted': request_logs_deleted,
        'conversion_logs_deleted': conversion_logs_deleted,
    }

"""
Celery tasks for API management.
Handles periodic tasks like resetting monthly usage counters.
"""
from celery import shared_task
from django.utils import timezone
from .models import APIMerchant
import logging

logger = logging.getLogger('apps.api')


@shared_task
def reset_monthly_usage_counters():
    """
    Reset monthly usage counters for all merchants.
    Should be run on the first day of each month.
    """
    logger.info("Starting monthly usage counter reset...")
    
    reset_count = 0
    error_count = 0
    
    # Get all active merchants
    merchants = APIMerchant.objects.filter(is_active=True)
    
    for merchant in merchants:
        try:
            old_usage = merchant.current_month_usage
            merchant.reset_monthly_usage()
            reset_count += 1
            
            logger.info(
                f"Reset usage for {merchant.company_name}: "
                f"{old_usage} -> 0"
            )
        except Exception as e:
            error_count += 1
            logger.error(
                f"Failed to reset usage for merchant {merchant.id}: {str(e)}"
            )
    
    logger.info(
        f"Monthly usage reset complete: {reset_count} successful, {error_count} errors"
    )
    
    return {
        'reset_count': reset_count,
        'error_count': error_count,
        'timestamp': timezone.now().isoformat(),
    }


@shared_task
def cleanup_old_usage_logs(days=90):
    """
    Clean up old API usage logs to keep database size manageable.
    
    Args:
        days: Number of days to keep (default: 90)
    """
    from .models import APIUsageLog
    from datetime import timedelta
    
    logger.info(f"Starting cleanup of usage logs older than {days} days...")
    
    cutoff_date = timezone.now() - timedelta(days=days)
    
    # Delete old logs
    deleted_count, _ = APIUsageLog.objects.filter(
        created_at__lt=cutoff_date
    ).delete()
    
    logger.info(f"Deleted {deleted_count} old usage log entries")
    
    return {
        'deleted_count': deleted_count,
        'cutoff_date': cutoff_date.isoformat(),
        'timestamp': timezone.now().isoformat(),
    }


@shared_task
def generate_usage_reports():
    """
    Generate monthly usage reports for all merchants.
    Can be used for billing or analytics.
    """
    logger.info("Generating monthly usage reports...")
    
    from .models import APIUsageLog
    from django.db.models import Count, Avg, Sum
    from datetime import timedelta
    
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    reports = []
    
    merchants = APIMerchant.objects.filter(is_active=True)
    
    for merchant in merchants:
        # Get usage statistics for this month
        stats = APIUsageLog.objects.filter(
            merchant=merchant,
            created_at__gte=month_start
        ).aggregate(
            total_requests=Count('id'),
            avg_response_time=Avg('response_time'),
            total_data_transferred=Sum('response_size'),
            billable_requests=Count('id', filter=models.Q(billable=True)),
        )
        
        # Get breakdown by status code
        status_breakdown = dict(
            APIUsageLog.objects.filter(
                merchant=merchant,
                created_at__gte=month_start
            ).values('status_code').annotate(
                count=Count('id')
            ).values_list('status_code', 'count')
        )
        
        report = {
            'merchant_id': merchant.id,
            'merchant_name': merchant.company_name,
            'plan': merchant.plan,
            'period_start': month_start.isoformat(),
            'period_end': now.isoformat(),
            'statistics': stats,
            'status_breakdown': status_breakdown,
        }
        
        reports.append(report)
        
        logger.info(
            f"Generated report for {merchant.company_name}: "
            f"{stats['total_requests']} requests"
        )
    
    logger.info(f"Generated {len(reports)} usage reports")
    
    return {
        'report_count': len(reports),
        'reports': reports,
        'timestamp': now.isoformat(),
    }


@shared_task
def check_quota_warnings():
    """
    Check merchants approaching their quota limits and send warnings.
    Runs daily to notify merchants at 80% and 90% usage.
    """
    logger.info("Checking for quota warnings...")
    
    warning_count = 0
    
    merchants = APIMerchant.objects.filter(is_active=True)
    
    for merchant in merchants:
        usage_percentage = merchant.get_usage_percentage()
        
        # Check if merchant is at 80% or 90% usage
        if usage_percentage >= 90:
            logger.warning(
                f"Merchant {merchant.company_name} at {usage_percentage:.1f}% usage "
                f"({merchant.current_month_usage}/{merchant.monthly_request_limit})"
            )
            # TODO: Send email notification
            warning_count += 1
        elif usage_percentage >= 80:
            logger.info(
                f"Merchant {merchant.company_name} at {usage_percentage:.1f}% usage "
                f"({merchant.current_month_usage}/{merchant.monthly_request_limit})"
            )
            # TODO: Send email notification
            warning_count += 1
    
    logger.info(f"Quota check complete: {warning_count} warnings")
    
    return {
        'warning_count': warning_count,
        'timestamp': timezone.now().isoformat(),
    }



@shared_task
def send_usage_alerts():
    """
    Send email alerts to merchants at 80% and 100% quota usage.
    Runs daily to check usage levels.
    """
    logger.info("Checking for usage alerts...")
    
    from django.core.mail import send_mail
    from django.conf import settings
    
    alert_count = 0
    
    merchants = APIMerchant.objects.filter(is_active=True)
    
    for merchant in merchants:
        usage_percentage = merchant.get_usage_percentage()
        
        # Check if at 100% (quota exceeded)
        if usage_percentage >= 100:
            try:
                subject = '⚠️ API Quota Exceeded - SmartToolPDF'
                message = f"""
Dear {merchant.company_name},

You have reached 100% of your monthly API quota.

Current Usage: {merchant.current_month_usage} / {merchant.monthly_request_limit} requests
Plan: {merchant.get_plan_display()}

Your API requests will be rate-limited until your quota resets on the 1st of next month.

To continue using the API without interruption, please consider upgrading your plan:
https://smarttoolpdf.com/merchant/dashboard/

Best regards,
The SmartToolPDF Team
                """.strip()
                
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@smarttoolpdf.com',
                    recipient_list=[merchant.contact_email],
                    fail_silently=False,
                )
                
                logger.warning(
                    f"100% quota alert sent to {merchant.company_name} "
                    f"({merchant.current_month_usage}/{merchant.monthly_request_limit})"
                )
                alert_count += 1
                
            except Exception as e:
                logger.error(f"Failed to send 100% alert to {merchant.contact_email}: {str(e)}")
        
        # Check if at 80% (warning)
        elif usage_percentage >= 80:
            try:
                subject = '⚠️ API Quota Warning (80%) - SmartToolPDF'
                message = f"""
Dear {merchant.company_name},

You have used 80% of your monthly API quota.

Current Usage: {merchant.current_month_usage} / {merchant.monthly_request_limit} requests
Remaining: {merchant.monthly_request_limit - merchant.current_month_usage} requests
Plan: {merchant.get_plan_display()}

Your quota will reset on the 1st of next month. To avoid service interruption, consider upgrading your plan:
https://smarttoolpdf.com/merchant/dashboard/

Best regards,
The SmartToolPDF Team
                """.strip()
                
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@smarttoolpdf.com',
                    recipient_list=[merchant.contact_email],
                    fail_silently=False,
                )
                
                logger.info(
                    f"80% quota alert sent to {merchant.company_name} "
                    f"({merchant.current_month_usage}/{merchant.monthly_request_limit})"
                )
                alert_count += 1
                
            except Exception as e:
                logger.error(f"Failed to send 80% alert to {merchant.contact_email}: {str(e)}")
    
    logger.info(f"Usage alerts complete: {alert_count} alerts sent")
    
    return {
        'alert_count': alert_count,
        'timestamp': timezone.now().isoformat(),
    }


@shared_task
def generate_monthly_usage_report(merchant_id):
    """
    Generate detailed monthly usage report for a merchant.
    
    Args:
        merchant_id: APIMerchant ID
    
    Returns:
        dict: Usage report data
    """
    try:
        merchant = APIMerchant.objects.get(id=merchant_id)
    except APIMerchant.DoesNotExist:
        logger.error(f"Merchant {merchant_id} not found")
        return None
    
    from .models import APIUsageLog
    from django.db.models import Count, Avg, Sum, Q
    from datetime import timedelta
    
    logger.info(f"Generating monthly usage report for {merchant.company_name}")
    
    # Get current month date range
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Get usage statistics
    logs = APIUsageLog.objects.filter(
        merchant=merchant,
        created_at__gte=month_start
    )
    
    # Overall statistics
    stats = logs.aggregate(
        total_requests=Count('id'),
        successful_requests=Count('id', filter=Q(status_code__lt=400)),
        failed_requests=Count('id', filter=Q(status_code__gte=400)),
        avg_response_time=Avg('response_time'),
        total_data_transferred=Sum('response_size'),
        billable_requests=Count('id', filter=Q(billable=True)),
    )
    
    # Breakdown by status code
    status_breakdown = dict(
        logs.values('status_code').annotate(
            count=Count('id')
        ).values_list('status_code', 'count')
    )
    
    # Breakdown by endpoint
    endpoint_breakdown = list(
        logs.values('endpoint').annotate(
            count=Count('id'),
            avg_time=Avg('response_time')
        ).order_by('-count')[:10]
    )
    
    # Breakdown by tool type
    tool_breakdown = dict(
        logs.filter(tool_type__isnull=False).values('tool_type').annotate(
            count=Count('id')
        ).values_list('tool_type', 'count')
    )
    
    # Daily usage
    daily_usage = []
    current_date = month_start.date()
    today = now.date()
    
    while current_date <= today:
        day_logs = logs.filter(
            created_at__date=current_date
        )
        daily_usage.append({
            'date': current_date.isoformat(),
            'requests': day_logs.count(),
            'successful': day_logs.filter(status_code__lt=400).count(),
            'failed': day_logs.filter(status_code__gte=400).count(),
        })
        current_date += timedelta(days=1)
    
    report = {
        'merchant_id': merchant.id,
        'merchant_name': merchant.company_name,
        'plan': merchant.plan,
        'period_start': month_start.isoformat(),
        'period_end': now.isoformat(),
        'statistics': {
            'total_requests': stats['total_requests'] or 0,
            'successful_requests': stats['successful_requests'] or 0,
            'failed_requests': stats['failed_requests'] or 0,
            'success_rate': (stats['successful_requests'] / stats['total_requests'] * 100) if stats['total_requests'] else 0,
            'avg_response_time': float(stats['avg_response_time'] or 0),
            'total_data_transferred': stats['total_data_transferred'] or 0,
            'billable_requests': stats['billable_requests'] or 0,
        },
        'quota': {
            'limit': merchant.monthly_request_limit,
            'used': merchant.current_month_usage,
            'remaining': max(0, merchant.monthly_request_limit - merchant.current_month_usage),
            'usage_percentage': merchant.get_usage_percentage(),
        },
        'breakdowns': {
            'by_status': status_breakdown,
            'by_endpoint': endpoint_breakdown,
            'by_tool': tool_breakdown,
        },
        'daily_usage': daily_usage,
        'generated_at': now.isoformat(),
    }
    
    logger.info(
        f"Generated report for {merchant.company_name}: "
        f"{stats['total_requests']} requests, "
        f"{stats['successful_requests']} successful"
    )
    
    return report

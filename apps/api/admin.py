"""
Admin interface for API Merchant and Partner System.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django.contrib import messages
from .models import (
    APIAccessRequest,
    APIMerchant,
    APIKey,
    APIUsageLog,
    WebhookDelivery
)


@admin.register(APIAccessRequest)
class APIAccessRequestAdmin(admin.ModelAdmin):
    """Admin interface for API access requests."""
    
    list_display = [
        'company_name',
        'email',
        'status_badge',
        'estimated_monthly_volume',
        'created_at',
        'reviewed_at',
    ]
    list_filter = ['status', 'created_at', 'reviewed_at']
    search_fields = ['company_name', 'email', 'full_name']
    readonly_fields = [
        'created_at',
        'updated_at',
        'reviewed_at',
        'reviewed_by',
        'merchant_link',
    ]
    
    fieldsets = (
        ('Requester Information', {
            'fields': (
                'full_name',
                'email',
                'company_name',
                'company_website',
                'phone_number',
            )
        }),
        ('Use Case', {
            'fields': (
                'use_case',
                'estimated_monthly_volume',
            )
        }),
        ('Status', {
            'fields': (
                'status',
                'rejection_reason',
                'merchant_link',
            )
        }),
        ('Review Information', {
            'fields': (
                'reviewed_by',
                'reviewed_at',
                'created_at',
                'updated_at',
            )
        }),
    )
    
    actions = ['approve_requests', 'reject_requests']
    
    def status_badge(self, obj):
        """Display status as colored badge."""
        colors = {
            'pending': '#FFA500',
            'approved': '#28A745',
            'rejected': '#DC3545',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            colors.get(obj.status, '#6C757D'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def merchant_link(self, obj):
        """Link to associated merchant account."""
        if obj.merchant:
            url = reverse('admin:api_apimerchant_change', args=[obj.merchant.pk])
            return format_html('<a href="{}">{}</a>', url, obj.merchant.company_name)
        return '-'
    merchant_link.short_description = 'Merchant Account'
    
    def approve_requests(self, request, queryset):
        """Approve selected API access requests."""
        from django.contrib.auth import get_user_model
        from .emails import send_api_access_approved_email
        from .utils import generate_api_key, generate_api_secret, hash_api_credential, extract_key_prefix
        import logging
        
        logger = logging.getLogger('apps.api')
        User = get_user_model()
        approved_count = 0
        failed_count = 0
        
        for access_request in queryset.filter(status='pending'):
            try:
                # Create user account if doesn't exist
                username = access_request.email.split('@')[0]
                base_username = username
                counter = 1
                
                # Ensure unique username
                while User.objects.filter(username=username).exists():
                    username = f"{base_username}{counter}"
                    counter += 1
                
                user, created = User.objects.get_or_create(
                    email=access_request.email,
                    defaults={
                        'username': username,
                        'first_name': access_request.full_name.split()[0] if access_request.full_name else '',
                    }
                )
                
                # Create merchant account
                merchant = APIMerchant.objects.create(
                    user=user,
                    company_name=access_request.company_name,
                    company_website=access_request.company_website,
                    contact_email=access_request.email,
                    contact_phone=access_request.phone_number,
                    plan='free',  # Start with free plan
                    monthly_request_limit=1000,  # Free plan limit
                )
                
                # Generate initial API key using utilities
                plain_key = generate_api_key(environment='production')
                plain_secret = generate_api_secret()
                
                api_key = APIKey.objects.create(
                    merchant=merchant,
                    name='Production Key',
                    environment='production',
                    key=hash_api_credential(plain_key),
                    key_prefix=extract_key_prefix(plain_key),
                    secret=hash_api_credential(plain_secret),
                )
                
                # Approve the request
                access_request.merchant = merchant
                access_request.approve(request.user)
                
                # Send approval email with credentials
                try:
                    send_api_access_approved_email(access_request, plain_key, plain_secret)
                    logger.info(f"Approval email sent for request #{access_request.id}")
                except Exception as e:
                    logger.error(f"Failed to send approval email for request #{access_request.id}: {str(e)}")
                    # Don't fail the approval if email fails
                
                approved_count += 1
                logger.info(
                    f"Approved API access request #{access_request.id} for {access_request.company_name}. "
                    f"Created merchant #{merchant.id} and API key #{api_key.id}"
                )
                
            except Exception as e:
                failed_count += 1
                logger.error(f"Failed to approve request #{access_request.id}: {str(e)}")
                self.message_user(
                    request,
                    f'Failed to approve request for {access_request.company_name}: {str(e)}',
                    messages.ERROR
                )
        
        if approved_count > 0:
            self.message_user(
                request,
                f'{approved_count} request(s) approved successfully. API credentials sent via email.',
                messages.SUCCESS
            )
        
        if failed_count > 0:
            self.message_user(
                request,
                f'{failed_count} request(s) failed to approve.',
                messages.ERROR
            )
    approve_requests.short_description = 'Approve selected requests'
    
    def reject_requests(self, request, queryset):
        """Reject selected API access requests."""
        from .emails import send_api_access_rejected_email
        import logging
        
        logger = logging.getLogger('apps.api')
        rejected_count = 0
        
        # Default rejection reason
        default_reason = (
            'Thank you for your interest in our API. After careful review, '
            'we are unable to approve your request at this time. This may be due to '
            'incomplete information or our current capacity limitations. '
            'You are welcome to reapply in the future.'
        )
        
        for access_request in queryset.filter(status='pending'):
            try:
                # Reject the request
                access_request.reject(request.user, default_reason)
                
                # Send rejection email
                try:
                    send_api_access_rejected_email(access_request)
                    logger.info(f"Rejection email sent for request #{access_request.id}")
                except Exception as e:
                    logger.error(f"Failed to send rejection email for request #{access_request.id}: {str(e)}")
                    # Don't fail the rejection if email fails
                
                rejected_count += 1
                logger.info(f"Rejected API access request #{access_request.id} for {access_request.company_name}")
                
            except Exception as e:
                logger.error(f"Failed to reject request #{access_request.id}: {str(e)}")
        
        self.message_user(
            request,
            f'{rejected_count} request(s) rejected. Notification emails sent.',
            messages.WARNING
        )
    reject_requests.short_description = 'Reject selected requests'


@admin.register(APIMerchant)
class APIMerchantAdmin(admin.ModelAdmin):
    """Admin interface for API merchants."""
    
    list_display = [
        'company_name',
        'plan_badge',
        'is_active',
        'usage_display',
        'total_requests',
        'last_request_at',
        'created_at',
    ]
    list_filter = ['plan', 'is_active', 'billing_cycle', 'created_at']
    search_fields = ['company_name', 'contact_email', 'user__username']
    readonly_fields = [
        'current_month_usage',
        'total_requests',
        'last_request_at',
        'created_at',
        'updated_at',
        'usage_percentage',
    ]
    
    fieldsets = (
        ('Company Information', {
            'fields': (
                'user',
                'company_name',
                'company_website',
                'contact_email',
                'contact_phone',
            )
        }),
        ('Subscription', {
            'fields': (
                'plan',
                'is_active',
                'billing_cycle',
                'next_billing_date',
            )
        }),
        ('Usage & Limits', {
            'fields': (
                'monthly_request_limit',
                'current_month_usage',
                'usage_percentage',
                'total_requests',
                'last_request_at',
            )
        }),
        ('Webhook Configuration', {
            'fields': (
                'webhook_enabled',
                'webhook_url',
                'webhook_secret',
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'updated_at',
            )
        }),
    )
    
    actions = ['reset_monthly_usage', 'activate_merchants', 'deactivate_merchants']
    
    def plan_badge(self, obj):
        """Display plan as colored badge."""
        colors = {
            'free': '#6C757D',
            'starter': '#17A2B8',
            'professional': '#FFC107',
            'enterprise': '#28A745',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            colors.get(obj.plan, '#6C757D'),
            obj.get_plan_display()
        )
    plan_badge.short_description = 'Plan'
    
    def usage_display(self, obj):
        """Display usage with progress bar."""
        percentage = obj.get_usage_percentage()
        color = '#28A745' if percentage < 80 else '#FFC107' if percentage < 100 else '#DC3545'
        
        return format_html(
            '<div style="width: 100px; background-color: #E9ECEF; border-radius: 3px;">'
            '<div style="width: {}%; background-color: {}; padding: 2px 5px; border-radius: 3px; color: white; font-size: 11px;">'
            '{}%'
            '</div></div>',
            min(percentage, 100),
            color,
            int(percentage)
        )
    usage_display.short_description = 'Usage'
    
    def usage_percentage(self, obj):
        """Display usage percentage."""
        return f"{obj.get_usage_percentage():.1f}%"
    usage_percentage.short_description = 'Usage Percentage'
    
    def reset_monthly_usage(self, request, queryset):
        """Reset monthly usage for selected merchants."""
        count = 0
        for merchant in queryset:
            merchant.reset_monthly_usage()
            count += 1
        
        self.message_user(
            request,
            f'Monthly usage reset for {count} merchant(s).',
            messages.SUCCESS
        )
    reset_monthly_usage.short_description = 'Reset monthly usage'
    
    def activate_merchants(self, request, queryset):
        """Activate selected merchants."""
        count = queryset.update(is_active=True)
        self.message_user(
            request,
            f'{count} merchant(s) activated.',
            messages.SUCCESS
        )
    activate_merchants.short_description = 'Activate selected merchants'
    
    def deactivate_merchants(self, request, queryset):
        """Deactivate selected merchants."""
        count = queryset.update(is_active=False)
        self.message_user(
            request,
            f'{count} merchant(s) deactivated.',
            messages.WARNING
        )
    deactivate_merchants.short_description = 'Deactivate selected merchants'


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    """Admin interface for API keys."""
    
    list_display = [
        'key_prefix_display',
        'merchant',
        'name',
        'environment',
        'is_active',
        'last_used_at',
        'created_at',
    ]
    list_filter = ['environment', 'is_active', 'created_at']
    search_fields = ['merchant__company_name', 'name', 'key_prefix']
    readonly_fields = [
        'key',
        'key_prefix',
        'secret',
        'created_at',
        'last_used_at',
        'revoked_at',
    ]
    
    fieldsets = (
        ('Key Information', {
            'fields': (
                'merchant',
                'name',
                'environment',
                'key_prefix',
            )
        }),
        ('Status', {
            'fields': (
                'is_active',
                'expires_at',
                'last_used_at',
                'revoked_at',
            )
        }),
        ('Security Settings', {
            'fields': (
                'allowed_ips',
                'rate_limit_override',
            )
        }),
        ('Credentials (Hashed)', {
            'fields': (
                'key',
                'secret',
            ),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
            )
        }),
    )
    
    actions = ['revoke_keys', 'activate_keys']
    
    def key_prefix_display(self, obj):
        """Display key prefix with monospace font."""
        return format_html('<code>{}</code>', obj.key_prefix + '...')
    key_prefix_display.short_description = 'Key Prefix'
    
    def revoke_keys(self, request, queryset):
        """Revoke selected API keys."""
        count = 0
        for api_key in queryset.filter(is_active=True):
            api_key.revoke()
            count += 1
        
        self.message_user(
            request,
            f'{count} API key(s) revoked.',
            messages.WARNING
        )
    revoke_keys.short_description = 'Revoke selected keys'
    
    def activate_keys(self, request, queryset):
        """Activate selected API keys."""
        count = queryset.update(is_active=True, revoked_at=None)
        self.message_user(
            request,
            f'{count} API key(s) activated.',
            messages.SUCCESS
        )
    activate_keys.short_description = 'Activate selected keys'


@admin.register(APIUsageLog)
class APIUsageLogAdmin(admin.ModelAdmin):
    """Admin interface for API usage logs."""
    
    list_display = [
        'created_at',
        'merchant',
        'method',
        'endpoint',
        'status_code_display',
        'response_time_display',
        'billable',
    ]
    list_filter = [
        'method',
        'status_code',
        'billable',
        'created_at',
    ]
    search_fields = [
        'merchant__company_name',
        'endpoint',
        'ip_address',
    ]
    readonly_fields = [
        'merchant',
        'api_key',
        'endpoint',
        'method',
        'status_code',
        'ip_address',
        'user_agent',
        'request_size',
        'response_size',
        'response_time',
        'conversion',
        'tool_type',
        'billable',
        'cost',
        'error_message',
        'created_at',
    ]
    
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Request Information', {
            'fields': (
                'merchant',
                'api_key',
                'endpoint',
                'method',
                'status_code',
            )
        }),
        ('Client Information', {
            'fields': (
                'ip_address',
                'user_agent',
            )
        }),
        ('Performance', {
            'fields': (
                'request_size',
                'response_size',
                'response_time',
            )
        }),
        ('Conversion Details', {
            'fields': (
                'conversion',
                'tool_type',
            )
        }),
        ('Billing', {
            'fields': (
                'billable',
                'cost',
            )
        }),
        ('Error Information', {
            'fields': (
                'error_message',
            )
        }),
        ('Timestamp', {
            'fields': (
                'created_at',
            )
        }),
    )
    
    def has_add_permission(self, request):
        """Disable manual creation of usage logs."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Make usage logs read-only."""
        return False
    
    def status_code_display(self, obj):
        """Display status code with color."""
        if obj.status_code < 300:
            color = '#28A745'
        elif obj.status_code < 400:
            color = '#17A2B8'
        elif obj.status_code < 500:
            color = '#FFC107'
        else:
            color = '#DC3545'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.status_code
        )
    status_code_display.short_description = 'Status'
    
    def response_time_display(self, obj):
        """Display response time in milliseconds."""
        return f"{obj.response_time * 1000:.0f} ms"
    response_time_display.short_description = 'Response Time'


@admin.register(WebhookDelivery)
class WebhookDeliveryAdmin(admin.ModelAdmin):
    """Admin interface for webhook deliveries."""
    
    list_display = [
        'created_at',
        'merchant',
        'conversion',
        'status_badge',
        'attempt_count',
        'next_retry_at',
    ]
    list_filter = ['status', 'created_at']
    search_fields = ['merchant__company_name', 'webhook_url']
    readonly_fields = [
        'merchant',
        'conversion',
        'webhook_url',
        'payload',
        'signature',
        'status',
        'response_status_code',
        'response_body',
        'error_message',
        'attempt_count',
        'max_attempts',
        'next_retry_at',
        'created_at',
        'delivered_at',
    ]
    
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Webhook Information', {
            'fields': (
                'merchant',
                'conversion',
                'webhook_url',
            )
        }),
        ('Payload', {
            'fields': (
                'payload',
                'signature',
            )
        }),
        ('Delivery Status', {
            'fields': (
                'status',
                'response_status_code',
                'response_body',
                'error_message',
            )
        }),
        ('Retry Information', {
            'fields': (
                'attempt_count',
                'max_attempts',
                'next_retry_at',
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'delivered_at',
            )
        }),
    )
    
    actions = ['retry_failed_webhooks']
    
    def has_add_permission(self, request):
        """Disable manual creation of webhook deliveries."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Make webhook deliveries read-only."""
        return False
    
    def status_badge(self, obj):
        """Display status as colored badge."""
        colors = {
            'pending': '#FFC107',
            'success': '#28A745',
            'failed': '#DC3545',
            'retrying': '#17A2B8',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            colors.get(obj.status, '#6C757D'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def retry_failed_webhooks(self, request, queryset):
        """Retry failed webhook deliveries."""
        count = 0
        for webhook in queryset.filter(status__in=['failed', 'retrying']):
            if webhook.attempt_count < webhook.max_attempts:
                webhook.status = 'pending'
                webhook.next_retry_at = timezone.now()
                webhook.save()
                count += 1
                
                # TODO: Queue webhook delivery task
                # retry_webhook_delivery.delay(webhook.id)
        
        self.message_user(
            request,
            f'{count} webhook(s) queued for retry.',
            messages.SUCCESS
        )
    retry_failed_webhooks.short_description = 'Retry failed webhooks'

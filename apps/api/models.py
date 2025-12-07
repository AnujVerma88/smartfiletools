"""
API Merchant and Partner System Models.
Handles API access requests, merchant accounts, API keys, usage tracking, and webhooks.
"""
from django.db import models
from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
import secrets
import hmac
import hashlib
import json


class APIAccessRequest(models.Model):
    """
    Model for API access requests from potential merchants.
    Admins review and approve/reject these requests.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    # Requester information
    full_name = models.CharField(max_length=255, help_text='Full name of requester')
    email = models.EmailField(help_text='Contact email address')
    company_name = models.CharField(max_length=255, help_text='Company or organization name')
    company_website = models.URLField(blank=True, help_text='Company website URL')
    phone_number = models.CharField(max_length=20, blank=True, help_text='Contact phone number')
    
    # Use case information
    use_case = models.TextField(help_text='Description of intended API usage')
    estimated_monthly_volume = models.IntegerField(
        default=0,
        help_text='Estimated number of API requests per month'
    )
    
    # Request status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text='Current status of the request'
    )
    rejection_reason = models.TextField(
        blank=True,
        help_text='Reason for rejection (if applicable)'
    )
    
    # Linked merchant (created upon approval)
    merchant = models.OneToOneField(
        'APIMerchant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='access_request',
        help_text='Associated merchant account (created on approval)'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_api_requests'
    )
    
    class Meta:
        verbose_name = 'API Access Request'
        verbose_name_plural = 'API Access Requests'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['email']),
        ]
    
    def __str__(self):
        return f"{self.company_name} - {self.email} ({self.status})"
    
    def approve(self, reviewed_by):
        """Approve the request and create merchant account."""
        self.status = 'approved'
        self.reviewed_by = reviewed_by
        self.reviewed_at = timezone.now()
        self.save()
    
    def reject(self, reviewed_by, reason):
        """Reject the request with a reason."""
        self.status = 'rejected'
        self.rejection_reason = reason
        self.reviewed_by = reviewed_by
        self.reviewed_at = timezone.now()
        self.save()


class APIMerchant(models.Model):
    """
    Merchant account for API access.
    Represents a business or developer using the API.
    """
    PLAN_CHOICES = [
        ('free', 'Free - 100 requests/month'),
        ('starter', 'Starter - 10,000 requests/month'),
        ('professional', 'Professional - 100,000 requests/month'),
        ('enterprise', 'Enterprise - Custom limits'),
    ]
    
    # Linked user account
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='api_merchant',
        help_text='Associated user account'
    )
    
    # Company information
    company_name = models.CharField(max_length=255, help_text='Company or organization name')
    company_website = models.URLField(blank=True, help_text='Company website URL')
    contact_email = models.EmailField(help_text='Primary contact email')
    contact_phone = models.CharField(max_length=20, blank=True, help_text='Contact phone number')
    
    # Subscription and billing
    plan = models.CharField(
        max_length=20,
        choices=PLAN_CHOICES,
        default='free',
        help_text='Current subscription plan'
    )
    is_active = models.BooleanField(default=True, help_text='Whether merchant account is active')
    
    # Usage limits and tracking
    monthly_request_limit = models.IntegerField(
        default=100,
        help_text='Maximum API requests per month'
    )
    current_month_usage = models.IntegerField(
        default=0,
        help_text='API requests used this month'
    )
    total_requests = models.IntegerField(
        default=0,
        help_text='Total API requests all-time'
    )
    last_request_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Timestamp of last API request'
    )
    
    # Billing information
    billing_cycle = models.CharField(
        max_length=20,
        default='monthly',
        choices=[('monthly', 'Monthly'), ('annual', 'Annual')],
        help_text='Billing cycle'
    )
    next_billing_date = models.DateField(
        null=True,
        blank=True,
        help_text='Next billing date'
    )
    
    # Webhook configuration
    webhook_url = models.URLField(
        blank=True,
        help_text='URL to receive webhook notifications'
    )
    webhook_secret = models.CharField(
        max_length=64,
        blank=True,
        help_text='Secret for HMAC webhook signature'
    )
    webhook_enabled = models.BooleanField(
        default=False,
        help_text='Whether webhooks are enabled'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'API Merchant'
        verbose_name_plural = 'API Merchants'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['plan', 'is_active']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"{self.company_name} ({self.plan})"
    
    def reset_monthly_usage(self):
        """Reset usage counter at the start of each month."""
        self.current_month_usage = 0
        self.save(update_fields=['current_month_usage'])
    
    def increment_usage(self):
        """Increment usage counters."""
        self.current_month_usage += 1
        self.total_requests += 1
        self.last_request_at = timezone.now()
        self.save(update_fields=['current_month_usage', 'total_requests', 'last_request_at'])
    
    def has_quota_remaining(self):
        """Check if merchant has remaining quota."""
        return self.current_month_usage < self.monthly_request_limit
    
    def get_usage_percentage(self):
        """Calculate usage percentage."""
        if self.monthly_request_limit == 0:
            return 0
        return (self.current_month_usage / self.monthly_request_limit) * 100
    
    def generate_webhook_secret(self):
        """Generate a new webhook secret."""
        self.webhook_secret = secrets.token_urlsafe(32)
        self.save(update_fields=['webhook_secret'])
        return self.webhook_secret


class APIKey(models.Model):
    """
    API credentials for merchant authentication.
    Supports multiple keys per merchant for different environments.
    """
    ENVIRONMENT_CHOICES = [
        ('sandbox', 'Sandbox/Testing'),
        ('production', 'Production'),
    ]
    
    merchant = models.ForeignKey(
        APIMerchant,
        on_delete=models.CASCADE,
        related_name='api_keys',
        help_text='Associated merchant account'
    )
    name = models.CharField(
        max_length=100,
        help_text='Key name (e.g., "Production Key", "Mobile App Key")'
    )
    key = models.CharField(
        max_length=255,  # Increased to accommodate hashed password
        unique=True,
        db_index=True,
        help_text='API key (hashed)'
    )
    key_prefix = models.CharField(
        max_length=8,
        help_text='First 8 characters for display'
    )
    secret = models.CharField(
        max_length=255,  # Increased to accommodate hashed password
        help_text='API secret (hashed)'
    )
    environment = models.CharField(
        max_length=20,
        choices=ENVIRONMENT_CHOICES,
        default='production',
        help_text='Environment (sandbox or production)'
    )
    
    # Status and security
    is_active = models.BooleanField(default=True, help_text='Whether key is active')
    last_used_at = models.DateTimeField(null=True, blank=True, help_text='Last usage timestamp')
    expires_at = models.DateTimeField(null=True, blank=True, help_text='Optional expiration date')
    
    # Security settings
    allowed_ips = models.JSONField(
        default=list,
        blank=True,
        help_text='IP whitelist (empty = all IPs allowed)'
    )
    rate_limit_override = models.IntegerField(
        null=True,
        blank=True,
        help_text='Custom rate limit (requests per minute)'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'API Key'
        verbose_name_plural = 'API Keys'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['merchant', 'is_active']),
            models.Index(fields=['key']),
        ]
    
    def __str__(self):
        return f"{self.merchant.company_name} - {self.name} ({self.key_prefix}...)"
    
    def generate_key_pair(self):
        """
        Generate unique API key and secret.
        Returns the plain text key and secret (only shown once).
        """
        # Generate API key with prefix
        env_prefix = 'test' if self.environment == 'sandbox' else 'live'
        random_part = secrets.token_urlsafe(32)
        plain_key = f"stpdf_{env_prefix}_{random_part}"
        
        # Generate secret
        plain_secret = secrets.token_urlsafe(48)
        
        # Store hashed versions
        self.key = make_password(plain_key)
        self.key_prefix = plain_key[:8]
        self.secret = make_password(plain_secret)
        
        return plain_key, plain_secret
    
    def verify_key(self, plain_key):
        """Verify provided key against stored hash."""
        return check_password(plain_key, self.key)
    
    def verify_secret(self, plain_secret):
        """Verify provided secret against stored hash."""
        return check_password(plain_secret, self.secret)
    
    def revoke(self):
        """Revoke this API key."""
        self.is_active = False
        self.revoked_at = timezone.now()
        self.save(update_fields=['is_active', 'revoked_at'])
    
    def is_expired(self):
        """Check if key has expired."""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False


class APIUsageLog(models.Model):
    """
    Log of all API requests for tracking and billing.
    """
    merchant = models.ForeignKey(
        APIMerchant,
        on_delete=models.CASCADE,
        related_name='usage_logs',
        help_text='Associated merchant'
    )
    api_key = models.ForeignKey(
        APIKey,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='usage_logs',
        help_text='API key used for request'
    )
    
    # Request details
    endpoint = models.CharField(max_length=255, help_text='API endpoint path')
    method = models.CharField(max_length=10, help_text='HTTP method')
    status_code = models.IntegerField(help_text='HTTP status code')
    
    # Client information
    ip_address = models.GenericIPAddressField(help_text='Client IP address')
    user_agent = models.TextField(help_text='User agent string')
    
    # Performance metrics
    request_size = models.BigIntegerField(default=0, help_text='Request body size in bytes')
    response_size = models.BigIntegerField(default=0, help_text='Response size in bytes')
    response_time = models.FloatField(help_text='Response time in seconds')
    
    # Conversion details (if applicable)
    conversion = models.ForeignKey(
        'tools.ConversionHistory',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='api_usage_logs',
        help_text='Associated conversion'
    )
    tool_type = models.CharField(
        max_length=50,
        blank=True,
        help_text='Tool type used'
    )
    
    # Billing
    billable = models.BooleanField(default=True, help_text='Whether request is billable')
    cost = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=0,
        help_text='Cost of this request'
    )
    
    # Error tracking
    error_message = models.TextField(blank=True, help_text='Error message if request failed')
    
    # Timestamp
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        verbose_name = 'API Usage Log'
        verbose_name_plural = 'API Usage Logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['merchant', '-created_at']),
            models.Index(fields=['api_key', '-created_at']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['status_code']),
        ]
    
    def __str__(self):
        return f"{self.merchant.company_name} - {self.method} {self.endpoint} ({self.status_code})"


class WebhookDelivery(models.Model):
    """
    Track webhook delivery attempts and status.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('retrying', 'Retrying'),
    ]
    
    merchant = models.ForeignKey(
        APIMerchant,
        on_delete=models.CASCADE,
        related_name='webhook_deliveries',
        help_text='Associated merchant'
    )
    conversion = models.ForeignKey(
        'tools.ConversionHistory',
        on_delete=models.CASCADE,
        related_name='webhook_deliveries',
        help_text='Associated conversion',
        null=True,
        blank=True
    )
    sign_session = models.ForeignKey(
        'esign.SignSession',
        on_delete=models.CASCADE,
        related_name='webhook_deliveries',
        help_text='Associated e-sign session',
        null=True,
        blank=True
    )
    
    # Webhook details
    webhook_url = models.URLField(help_text='Destination webhook URL')
    payload = models.JSONField(help_text='Webhook payload data')
    signature = models.CharField(max_length=128, help_text='HMAC signature')
    
    # Delivery status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text='Delivery status'
    )
    response_status_code = models.IntegerField(
        null=True,
        blank=True,
        help_text='HTTP status code from webhook endpoint'
    )
    response_body = models.TextField(
        blank=True,
        help_text='Response body from webhook endpoint'
    )
    error_message = models.TextField(
        blank=True,
        help_text='Error message if delivery failed'
    )
    
    # Retry logic
    attempt_count = models.IntegerField(default=0, help_text='Number of delivery attempts')
    max_attempts = models.IntegerField(default=3, help_text='Maximum delivery attempts')
    next_retry_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Next retry timestamp'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Successful delivery timestamp'
    )
    
    class Meta:
        verbose_name = 'Webhook Delivery'
        verbose_name_plural = 'Webhook Deliveries'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['merchant', '-created_at']),
            models.Index(fields=['status', 'next_retry_at']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"Webhook for {self.merchant.company_name} - Conversion {self.conversion.id} ({self.status})"
    
    def generate_signature(self):
        """Generate HMAC signature for webhook payload."""
        message = json.dumps(self.payload, sort_keys=True).encode()
        secret = self.merchant.webhook_secret.encode()
        signature = hmac.new(secret, message, hashlib.sha256).hexdigest()
        self.signature = signature
        return signature
    
    def verify_signature(self, provided_signature):
        """Verify webhook signature."""
        expected_signature = self.generate_signature()
        return hmac.compare_digest(provided_signature, expected_signature)
    
    def mark_success(self, status_code, response_body=''):
        """Mark delivery as successful."""
        self.status = 'success'
        self.response_status_code = status_code
        self.response_body = response_body
        self.delivered_at = timezone.now()
        self.save()
    
    def mark_failed(self, error_message, status_code=None, response_body=''):
        """Mark delivery as failed."""
        self.attempt_count += 1
        self.error_message = error_message
        self.response_status_code = status_code
        self.response_body = response_body
        
        if self.attempt_count < self.max_attempts:
            # Schedule retry with exponential backoff
            self.status = 'retrying'
            delay_minutes = 2 ** self.attempt_count  # 2, 4, 8 minutes
            self.next_retry_at = timezone.now() + timezone.timedelta(minutes=delay_minutes)
        else:
            self.status = 'failed'
            self.next_retry_at = None
        
        self.save()

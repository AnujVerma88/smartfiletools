"""
E-Sign models for PDF electronic signature functionality
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid


class SignSession(models.Model):
    """
    Main signing session tracking.
    Similar to ConversionHistory but for e-sign workflow.
    """
    
    STATUS_CHOICES = [
        ('created', 'Created'),
        ('otp_sent', 'OTP Sent'),
        ('otp_verified', 'OTP Verified'),
        ('signing', 'Signing in Progress'),
        ('signed', 'Signed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Ownership (similar to ConversionHistory)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sign_sessions',
        help_text='User who created this session (if via web UI)'
    )
    
    # Signer information
    signer_email = models.EmailField(help_text='Email of the person signing')
    signer_name = models.CharField(max_length=255, help_text='Full name of signer')
    
    # Document storage (similar to ConversionHistory file fields)
    original_pdf = models.FileField(
        upload_to='esign/originals/%Y/%m/%d/',
        help_text='Original uploaded PDF'
    )
    signed_pdf = models.FileField(
        upload_to='esign/signed/%Y/%m/%d/',
        null=True,
        blank=True,
        help_text='Signed PDF with embedded signatures'
    )
    
    # File metadata
    original_filename = models.CharField(max_length=255, blank=True)
    original_file_size = models.BigIntegerField(default=0, help_text='Original file size in bytes')
    signed_file_size = models.BigIntegerField(default=0, help_text='Signed file size in bytes')
    
    # Hashes for integrity
    original_pdf_hash = models.CharField(
        max_length=500, 
        blank=True,
        default='',
        help_text='SHA-256 hash of original'
    )
    signed_pdf_hash = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        help_text='SHA-256 hash of signed PDF'
    )

    
    # Session state
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='created')
    expires_at = models.DateTimeField(help_text='Session expiration time')
    
    # Metadata (similar to ConversionHistory)
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text='Additional metadata'
    )
    
    # Audit trail data
    audit_trail_data = models.JSONField(
        default=dict,
        blank=True,
        help_text='Complete audit trail information (session details, signatures, events)'
    )
    
    # Celery task tracking (similar to ConversionHistory)
    celery_task_id = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text='Celery task ID for async processing'
    )
    
    # Error tracking
    error_message = models.TextField(blank=True, help_text='Error message if failed')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    signed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Sign Session'
        verbose_name_plural = 'Sign Sessions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['signer_email', '-created_at']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['celery_task_id']),
        ]
    
    def __str__(self):
        return f"SignSession {self.id} - {self.signer_email} - {self.status}"
    
    def is_expired(self):
        """Check if session has expired"""
        return timezone.now() > self.expires_at
    
    def can_sign(self):
        """Check if session is ready for signing"""
        return self.status == 'otp_verified' and not self.is_expired()


class SignatureField(models.Model):
    """
    Signature field placement on PDF pages.
    Defines where signatures should be placed.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        SignSession,
        on_delete=models.CASCADE,
        related_name='signature_fields'
    )
    
    # Position on page
    page_number = models.IntegerField(help_text='PDF page number (1-indexed)')
    x = models.FloatField(help_text='X coordinate (points)')
    y = models.FloatField(help_text='Y coordinate (points)')
    width = models.FloatField(help_text='Field width (points)')
    height = models.FloatField(help_text='Field height (points)')
    
    # Field properties
    name = models.CharField(max_length=100, help_text='Field identifier')
    label = models.CharField(max_length=255, blank=True, help_text='Display label')
    required = models.BooleanField(default=True)
    order = models.IntegerField(default=0, help_text='Signing order for multi-field')
    
    # Status
    is_signed = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Signature Field'
        verbose_name_plural = 'Signature Fields'
        ordering = ['session', 'order', 'page_number']
    
    def __str__(self):
        return f"{self.session.id} - Page {self.page_number} - {self.name}"


class OTP(models.Model):
    """
    OTP verification records for signer authentication.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        SignSession,
        on_delete=models.CASCADE,
        related_name='otps'
    )
    
    # OTP data (hashed for security)
    otp_hash = models.CharField(max_length=255, help_text='Hashed OTP code')
    
    # Verification tracking
    attempts = models.IntegerField(default=0)
    max_attempts = models.IntegerField(default=5)
    is_verified = models.BooleanField(default=False)
    
    # Expiration
    expires_at = models.DateTimeField(help_text='OTP expiration time')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'OTP'
        verbose_name_plural = 'OTPs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['session', '-created_at']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"OTP for {self.session.id} - {'Verified' if self.is_verified else 'Pending'}"
    
    def is_expired(self):
        """Check if OTP has expired"""
        return timezone.now() > self.expires_at
    
    def can_verify(self):
        """Check if OTP can still be verified"""
        return (
            not self.is_verified and
            not self.is_expired() and
            self.attempts < self.max_attempts
        )


class Signature(models.Model):
    """
    Captured signature data with audit trail.
    """
    
    METHOD_CHOICES = [
        ('draw', 'Drawn'),
        ('upload', 'Uploaded Image'),
        ('type', 'Typed Name'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        SignSession,
        on_delete=models.CASCADE,
        related_name='signatures'
    )
    field = models.ForeignKey(
        SignatureField,
        on_delete=models.CASCADE,
        related_name='signatures',
        null=True,
        blank=True
    )
    
    # Signature method and data
    method = models.CharField(max_length=10, choices=METHOD_CHOICES)
    signature_image = models.FileField(
        upload_to='esign/signatures/%Y/%m/%d/',
        help_text='Signature image (PNG with transparency)'
    )
    
    # Signer details
    signer_name = models.CharField(max_length=255)
    signer_email = models.EmailField()
    signer_reason = models.TextField(blank=True, help_text='Reason for signing')
    signer_location = models.CharField(max_length=255, blank=True)
    
    # Audit trail
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField()
    
    # Font info for typed signatures
    font_name = models.CharField(max_length=100, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Signature'
        verbose_name_plural = 'Signatures'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.method} signature by {self.signer_email}"


class AuditEvent(models.Model):
    """
    Comprehensive audit trail for all signing activities.
    Similar to ConversionLog but for e-sign events.
    """
    
    EVENT_TYPES = [
        ('session_created', 'Session Created'),
        ('pdf_uploaded', 'PDF Uploaded'),
        ('fields_placed', 'Signature Fields Placed'),
        ('otp_sent', 'OTP Sent'),
        ('otp_verified', 'OTP Verified'),
        ('otp_failed', 'OTP Verification Failed'),
        ('signature_added', 'Signature Added'),
        ('pdf_signed', 'PDF Signed'),
        ('session_expired', 'Session Expired'),
        ('session_cancelled', 'Session Cancelled'),
        ('download', 'Signed PDF Downloaded'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        SignSession,
        on_delete=models.CASCADE,
        related_name='audit_events'
    )
    
    event_type = models.CharField(max_length=30, choices=EVENT_TYPES)
    payload = models.JSONField(default=dict, help_text='Event details')
    
    # Context
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Audit Event'
        verbose_name_plural = 'Audit Events'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['session', '-created_at']),
            models.Index(fields=['event_type', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.event_type} - {self.session.id}"

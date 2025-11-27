from django.db import models
from django.conf import settings
from django.utils import timezone


class SiteTheme(models.Model):
    """
    Model to store site theme configurations with customizable colors.
    Only one theme can be active at a time.
    """
    theme_name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=False)
    primary_color = models.CharField(max_length=7, default='#14B8A6', help_text='Hex color code (e.g., #14B8A6)')
    primary_color_rgb = models.CharField(max_length=20, default='20, 184, 166', help_text='RGB values (e.g., 20, 184, 166)')
    secondary_color = models.CharField(max_length=7, null=True, blank=True, help_text='Optional secondary color')
    accent_color = models.CharField(max_length=7, null=True, blank=True, help_text='Optional accent color')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Site Theme'
        verbose_name_plural = 'Site Themes'
        ordering = ['-is_active', 'theme_name']

    def __str__(self):
        return f"{self.theme_name} {'(Active)' if self.is_active else ''}"

    def save(self, *args, **kwargs):
        """
        Ensure only one theme is active at a time.
        When activating a theme, deactivate all others.
        """
        if self.is_active:
            # Deactivate all other themes
            SiteTheme.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

    @classmethod
    def get_active_theme(cls):
        """
        Get the currently active theme or create a default teal theme if none exists.
        """
        active_theme = cls.objects.filter(is_active=True).first()
        
        if not active_theme:
            # Create default teal theme
            active_theme = cls.objects.create(
                theme_name='Default Teal',
                is_active=True,
                primary_color='#14B8A6',
                primary_color_rgb='20, 184, 166',
                secondary_color='#0F766E',
                accent_color='#5EEAD4'
            )
        
        return active_theme

    def get_css_variables(self):
        """
        Return a dictionary of CSS custom properties for use in templates.
        """
        return {
            '--primary-color': self.primary_color,
            '--primary-color-rgb': self.primary_color_rgb,
            '--secondary-color': self.secondary_color or self.primary_color,
            '--accent-color': self.accent_color or self.primary_color,
        }



class RequestLog(models.Model):
    """
    Model to log all HTTP requests and responses for monitoring and debugging.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='request_logs',
        help_text='User who made the request (null for anonymous users)'
    )
    method = models.CharField(max_length=10, help_text='HTTP method (GET, POST, PUT, DELETE, etc.)')
    path = models.CharField(max_length=500, help_text='Request path')
    status_code = models.IntegerField(help_text='HTTP status code')
    ip_address = models.GenericIPAddressField(help_text='Client IP address')
    user_agent = models.TextField(blank=True, help_text='Browser/client user agent string')
    request_body = models.TextField(null=True, blank=True, help_text='POST/PUT request data')
    response_body = models.TextField(null=True, blank=True, help_text='Response content')
    response_time = models.FloatField(help_text='Response time in seconds')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Request Log'
        verbose_name_plural = 'Request Logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status_code']),
            models.Index(fields=['path']),
            models.Index(fields=['ip_address']),
        ]

    def __str__(self):
        user_str = self.user.username if self.user else 'Anonymous'
        return f"{self.method} {self.path} - {self.status_code} ({user_str})"


class ConversionLog(models.Model):
    """
    Model to log conversion process steps and events.
    """
    conversion = models.ForeignKey(
        'tools.ConversionHistory',
        on_delete=models.CASCADE,
        related_name='logs',
        help_text='Related conversion history record'
    )
    action = models.CharField(
        max_length=50,
        help_text='Action performed (e.g., started, processing, completed, failed)'
    )
    message = models.TextField(help_text='Log message describing the action')
    metadata = models.JSONField(
        null=True,
        blank=True,
        help_text='Additional context data (JSON format)'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Conversion Log'
        verbose_name_plural = 'Conversion Logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['conversion', '-created_at']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"{self.action} - {self.conversion.tool_type} ({self.created_at})"



class SiteStatistics(models.Model):
    """
    Model to store site-wide statistics displayed on homepage and about page.
    Uses hybrid approach: base number + actual counts from database.
    Only one record should exist (singleton pattern).
    """
    base_files_converted = models.IntegerField(
        default=12590,
        help_text='Base number for files converted (actual count will be added to this)'
    )
    base_happy_users = models.IntegerField(
        default=950,
        help_text='Base number for happy users (actual count will be added to this)'
    )
    base_tools_available = models.IntegerField(
        default=25,
        help_text='Base number for tools available (actual count will be added to this)'
    )
    uptime_percentage = models.CharField(
        max_length=20,
        default='99.9%',
        help_text='Display value for uptime (e.g., "99.9%" or "100%")'
    )
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Site Statistics'
        verbose_name_plural = 'Site Statistics'
    
    def __str__(self):
        return f"Site Statistics (Updated: {self.updated_at.strftime('%Y-%m-%d %H:%M')})"
    
    def save(self, *args, **kwargs):
        """Ensure only one instance exists (singleton pattern)."""
        self.pk = 1
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Prevent deletion of the singleton instance."""
        pass
    
    def get_total_files_converted(self):
        """Get total files converted (base + actual)."""
        from apps.tools.models import ConversionHistory
        actual_count = ConversionHistory.objects.filter(status='completed').count()
        total = self.base_files_converted + actual_count
        return self._format_number(total)
    
    def get_total_happy_users(self):
        """Get total happy users (base + actual)."""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        actual_count = User.objects.count()
        total = self.base_happy_users + actual_count
        return self._format_number(total)
    
    def get_total_tools_available(self):
        """Get total tools available (base + actual)."""
        from apps.tools.models import Tool
        actual_count = Tool.objects.filter(is_active=True).count()
        total = self.base_tools_available + actual_count
        return str(total)
    
    def _format_number(self, num):
        """Format number with K, M suffixes and + sign."""
        if num >= 1000000:
            return f"{num / 1000000:.1f}M+".replace('.0M', 'M')
        elif num >= 1000:
            return f"{num / 1000:.1f}K+".replace('.0K', 'K')
        else:
            return f"{num}+"
    
    @classmethod
    def get_stats(cls):
        """Get or create the singleton statistics instance."""
        obj, created = cls.objects.get_or_create(pk=1)
        return obj


class EmailNotification(models.Model):
    """
    Model to track all email notifications sent by the system.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ]
    
    EMAIL_TYPE_CHOICES = [
        ('conversion_complete', 'Conversion Complete'),
    ]
    
    conversion = models.ForeignKey(
        'tools.ConversionHistory',
        on_delete=models.CASCADE,
        related_name='email_notifications',
        help_text='Related conversion history record'
    )
    recipient_email = models.EmailField(
        help_text='Email address where notification was sent'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='email_notifications',
        help_text='User who received the email'
    )
    email_type = models.CharField(
        max_length=50,
        choices=EMAIL_TYPE_CHOICES,
        default='conversion_complete',
        help_text='Type of email notification'
    )
    subject = models.CharField(
        max_length=255,
        help_text='Email subject line'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text='Status: sent, failed, or pending'
    )
    error_message = models.TextField(
        null=True,
        blank=True,
        help_text='Error details if sending failed'
    )
    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Timestamp when email was successfully sent'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text='When record was created'
    )
    
    class Meta:
        verbose_name = 'Email Notification'
        verbose_name_plural = 'Email Notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['conversion']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['email_type']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"{self.email_type} - {self.recipient_email} ({self.status})"
    
    def mark_as_sent(self):
        """Update status to 'sent' and set sent_at timestamp."""
        self.status = 'sent'
        self.sent_at = timezone.now()
        self.save(update_fields=['status', 'sent_at'])
    
    def mark_as_failed(self, error_message):
        """Update status to 'failed' and store error message."""
        self.status = 'failed'
        self.error_message = error_message
        self.save(update_fields=['status', 'error_message'])

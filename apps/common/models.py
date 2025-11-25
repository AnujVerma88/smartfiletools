from django.db import models
from django.conf import settings


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

"""
Admin interface for common app models.
"""
from django.contrib import admin
from .models import SiteTheme, RequestLog, ConversionLog, SiteStatistics, EmailNotification


@admin.register(SiteTheme)
class SiteThemeAdmin(admin.ModelAdmin):
    """
    Admin interface for managing site themes.
    """
    list_display = ['theme_name', 'is_active', 'primary_color', 'created_at', 'updated_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['theme_name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Theme Information', {
            'fields': ('theme_name', 'is_active')
        }),
        ('Colors', {
            'fields': ('primary_color', 'primary_color_rgb', 'secondary_color', 'accent_color'),
            'description': 'Configure theme colors. Primary color is required, others are optional.'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['activate_theme']
    
    def activate_theme(self, request, queryset):
        """
        Custom admin action to activate selected theme.
        Only one theme can be activated at a time.
        """
        if queryset.count() > 1:
            self.message_user(request, 'Please select only one theme to activate.', level='warning')
            return
        
        theme = queryset.first()
        theme.is_active = True
        theme.save()
        
        self.message_user(request, f'Theme "{theme.theme_name}" has been activated.', level='success')
    
    activate_theme.short_description = 'Activate selected theme'



@admin.register(RequestLog)
class RequestLogAdmin(admin.ModelAdmin):
    """
    Read-only admin interface for viewing request logs.
    """
    list_display = ['created_at', 'user', 'method', 'path', 'status_code', 'response_time', 'ip_address']
    list_filter = ['method', 'status_code', 'created_at']
    search_fields = ['user__username', 'user__email', 'path', 'ip_address']
    readonly_fields = [
        'user', 'method', 'path', 'status_code', 'ip_address',
        'user_agent', 'request_body', 'response_body', 'response_time', 'created_at'
    ]
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    fieldsets = (
        ('Request Information', {
            'fields': ('user', 'method', 'path', 'ip_address', 'user_agent')
        }),
        ('Response Information', {
            'fields': ('status_code', 'response_time', 'created_at')
        }),
        ('Request/Response Data', {
            'fields': ('request_body', 'response_body'),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        """Disable adding logs through admin."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Disable editing logs through admin."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Allow deletion for cleanup purposes."""
        return request.user.is_superuser


@admin.register(ConversionLog)
class ConversionLogAdmin(admin.ModelAdmin):
    """
    Admin interface for viewing conversion logs.
    """
    list_display = ['created_at', 'conversion', 'action', 'message_preview']
    list_filter = ['action', 'created_at']
    search_fields = ['conversion__id', 'action', 'message']
    readonly_fields = ['conversion', 'action', 'message', 'metadata', 'created_at']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    fieldsets = (
        ('Log Information', {
            'fields': ('conversion', 'action', 'message', 'created_at')
        }),
        ('Additional Data', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
    )
    
    def message_preview(self, obj):
        """Show truncated message in list view."""
        if len(obj.message) > 100:
            return obj.message[:100] + '...'
        return obj.message
    message_preview.short_description = 'Message'
    
    def has_add_permission(self, request):
        """Disable adding logs through admin."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Disable editing logs through admin."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Allow deletion for cleanup purposes."""
        return request.user.is_superuser



@admin.register(SiteStatistics)
class SiteStatisticsAdmin(admin.ModelAdmin):
    """
    Admin interface for managing site statistics.
    Only one record exists (singleton pattern).
    Uses hybrid approach: base numbers + actual counts.
    """
    list_display = ['display_files_converted', 'display_happy_users', 'display_tools_available', 'uptime_percentage', 'updated_at']
    readonly_fields = ['updated_at', 'display_files_converted', 'display_happy_users', 'display_tools_available']
    
    fieldsets = (
        ('Base Numbers (Starting Point)', {
            'fields': ('base_files_converted', 'base_happy_users', 'base_tools_available'),
            'description': 'Set base numbers. Actual counts from database will be added to these. Example: Base 12590 + 10 actual conversions = 12600+ displayed'
        }),
        ('Other Statistics', {
            'fields': ('uptime_percentage',),
            'description': 'Manually set uptime percentage (e.g., "99.9%")'
        }),
        ('Current Display Values (Read-Only)', {
            'fields': ('display_files_converted', 'display_happy_users', 'display_tools_available'),
            'description': 'These are the actual values shown on the website (base + actual counts)'
        }),
        ('Last Updated', {
            'fields': ('updated_at',),
        }),
    )
    
    def display_files_converted(self, obj):
        """Show calculated total for files converted."""
        return obj.get_total_files_converted()
    display_files_converted.short_description = 'Files Converted (Displayed)'
    
    def display_happy_users(self, obj):
        """Show calculated total for happy users."""
        return obj.get_total_happy_users()
    display_happy_users.short_description = 'Happy Users (Displayed)'
    
    def display_tools_available(self, obj):
        """Show calculated total for tools available."""
        return obj.get_total_tools_available()
    display_tools_available.short_description = 'Tools Available (Displayed)'
    
    def has_add_permission(self, request):
        """Only allow one instance to exist."""
        return not SiteStatistics.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of the singleton instance."""
        return False


@admin.register(EmailNotification)
class EmailNotificationAdmin(admin.ModelAdmin):
    """
    Admin interface for viewing email notification history.
    Provides comprehensive filtering, searching, and display of email notifications.
    """
    list_display = [
        'created_at', 
        'email_type', 
        'recipient_email', 
        'user_display', 
        'conversion_display', 
        'status_display', 
        'sent_at'
    ]
    list_filter = [
        'status', 
        'email_type', 
        'created_at',
        'sent_at'
    ]
    search_fields = [
        'recipient_email', 
        'conversion__id', 
        'user__username', 
        'user__email',
        'subject'
    ]
    readonly_fields = [
        'conversion', 
        'recipient_email', 
        'user', 
        'email_type', 
        'subject', 
        'status', 
        'error_message', 
        'sent_at', 
        'created_at',
        'conversion_details',
        'user_details'
    ]
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    fieldsets = (
        ('Email Information', {
            'fields': ('email_type', 'subject', 'recipient_email')
        }),
        ('Related User', {
            'fields': ('user', 'user_details')
        }),
        ('Related Conversion', {
            'fields': ('conversion', 'conversion_details')
        }),
        ('Status', {
            'fields': ('status', 'sent_at', 'error_message')
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )
    
    def user_display(self, obj):
        """Display user information with link to user admin."""
        if obj.user:
            return f"{obj.user.username} ({obj.user.email})"
        return "Anonymous"
    user_display.short_description = 'User'
    user_display.admin_order_field = 'user__username'
    
    def conversion_display(self, obj):
        """Display conversion information with link to conversion."""
        if obj.conversion:
            return f"#{obj.conversion.id} - {obj.conversion.tool_type}"
        return "N/A"
    conversion_display.short_description = 'Conversion'
    conversion_display.admin_order_field = 'conversion__id'
    
    def status_display(self, obj):
        """Display status with color coding."""
        colors = {
            'sent': 'green',
            'failed': 'red',
            'pending': 'orange'
        }
        color = colors.get(obj.status, 'gray')
        return f'<span style="color: {color}; font-weight: bold;">{obj.status.upper()}</span>'
    status_display.short_description = 'Status'
    status_display.admin_order_field = 'status'
    status_display.allow_tags = True
    
    def user_details(self, obj):
        """Display detailed user information."""
        if obj.user:
            return (
                f"Username: {obj.user.username}\n"
                f"Email: {obj.user.email}\n"
                f"Full Name: {obj.user.get_full_name() or 'N/A'}\n"
                f"User ID: {obj.user.id}"
            )
        return "No user associated (anonymous conversion)"
    user_details.short_description = 'User Details'
    
    def conversion_details(self, obj):
        """Display detailed conversion information."""
        if obj.conversion:
            details = (
                f"Conversion ID: {obj.conversion.id}\n"
                f"Tool Type: {obj.conversion.tool_type}\n"
                f"Status: {obj.conversion.status}\n"
                f"Created: {obj.conversion.created_at}\n"
            )
            if obj.conversion.completed_at:
                details += f"Completed: {obj.conversion.completed_at}\n"
            if obj.conversion.file_size_before:
                details += f"Input Size: {obj.conversion.file_size_before} bytes\n"
            if obj.conversion.file_size_after:
                details += f"Output Size: {obj.conversion.file_size_after} bytes\n"
            return details
        return "No conversion associated"
    conversion_details.short_description = 'Conversion Details'
    
    def has_add_permission(self, request):
        """Disable adding email notifications through admin."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Disable editing email notifications through admin."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Allow deletion for cleanup purposes."""
        return request.user.is_superuser

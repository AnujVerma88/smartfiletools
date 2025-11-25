"""
Admin interface for common app models.
"""
from django.contrib import admin
from .models import SiteTheme, RequestLog, ConversionLog


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

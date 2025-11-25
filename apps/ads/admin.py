"""
Admin interface for advertisement management.
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import Advertisement


@admin.register(Advertisement)
class AdvertisementAdmin(admin.ModelAdmin):
    """
    Admin interface for managing advertisements.
    """
    list_display = [
        'title', 'position', 'is_active', 'impression_count', 
        'click_count', 'ctr_display', 'schedule_status', 'created_at'
    ]
    list_filter = ['position', 'is_active', 'created_at', 'start_date', 'end_date']
    search_fields = ['title', 'description', 'link_url']
    readonly_fields = ['impression_count', 'click_count', 'ctr_display', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Advertisement Information', {
            'fields': ('title', 'description', 'image', 'link_url')
        }),
        ('Placement', {
            'fields': ('position', 'is_active')
        }),
        ('Scheduling', {
            'fields': ('start_date', 'end_date'),
            'description': 'Optional: Set date range for when this ad should be displayed'
        }),
        ('Statistics', {
            'fields': ('impression_count', 'click_count', 'ctr_display'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['activate_ads', 'deactivate_ads', 'reset_statistics']
    
    def ctr_display(self, obj):
        """Display click-through rate."""
        ctr = obj.get_ctr()
        return f"{ctr:.2f}%"
    ctr_display.short_description = 'CTR'
    
    def schedule_status(self, obj):
        """Display schedule status with color coding."""
        if obj.is_scheduled_active():
            return format_html(
                '<span style="color: green;">●</span> Active'
            )
        return format_html(
            '<span style="color: red;">●</span> Scheduled'
        )
    schedule_status.short_description = 'Schedule'
    
    def activate_ads(self, request, queryset):
        """Activate selected advertisements."""
        count = queryset.update(is_active=True)
        self.message_user(request, f'{count} advertisement(s) activated.', level='success')
    activate_ads.short_description = 'Activate selected advertisements'
    
    def deactivate_ads(self, request, queryset):
        """Deactivate selected advertisements."""
        count = queryset.update(is_active=False)
        self.message_user(request, f'{count} advertisement(s) deactivated.', level='success')
    deactivate_ads.short_description = 'Deactivate selected advertisements'
    
    def reset_statistics(self, request, queryset):
        """Reset impression and click counts."""
        count = queryset.update(impression_count=0, click_count=0)
        self.message_user(
            request, 
            f'Statistics reset for {count} advertisement(s).', 
            level='success'
        )
    reset_statistics.short_description = 'Reset statistics'

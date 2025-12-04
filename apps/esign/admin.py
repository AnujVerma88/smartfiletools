"""
Admin interface for E-Sign models.
Following the same pattern as apps.tools.admin
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import SignSession, SignatureField, OTP, Signature, AuditEvent


@admin.register(SignSession)
class SignSessionAdmin(admin.ModelAdmin):
    """
    Admin interface for SignSession.
    Similar to ConversionHistoryAdmin.
    """
    list_display = [
        'id',
        'signer_email',
        'signer_name',
        'status_badge',
        'created_at',
        'signed_at',
        'download_link',
    ]
    list_filter = ['status', 'created_at', 'signed_at']
    search_fields = ['signer_email', 'signer_name', 'id']
    readonly_fields = [
        'id',
        'original_pdf_hash',
        'signed_pdf_hash',
        'celery_task_id',
        'created_at',
        'updated_at',
        'signed_at',
        'audit_trail_display',
    ]
    
    fieldsets = (
        ('Session Information', {
            'fields': ('id', 'user', 'status', 'celery_task_id')
        }),
        ('Signer Details', {
            'fields': ('signer_email', 'signer_name')
        }),
        ('Documents', {
            'fields': (
                'original_pdf',
                'original_filename',
                'original_file_size',
                'original_pdf_hash',
                'signed_pdf',
                'signed_file_size',
                'signed_pdf_hash',
            )
        }),
        ('Session Timing', {
            'fields': ('expires_at', 'created_at', 'updated_at', 'signed_at')
        }),
        ('Audit Trail', {
            'fields': ('audit_trail_display',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('metadata', 'error_message'),
            'classes': ('collapse',)
        }),
    )
    
    def audit_trail_display(self, obj):
        """Display formatted audit trail"""
        if not obj.audit_trail_data:
            return '-'
        
        data = obj.audit_trail_data
        html = '<div style="font-family: monospace; background: #f5f5f5; padding: 15px; border-radius: 5px;">'
        
        # Session Details
        html += '<h3 style="margin-top: 0;">Session Details</h3>'
        html += f'<p><strong>Session ID:</strong> {data.get("session_id", "N/A")}</p>'
        html += f'<p><strong>Status:</strong> {data.get("status", "N/A")}</p>'
        html += f'<p><strong>Created:</strong> {data.get("created_at", "N/A")}</p>'
        html += f'<p><strong>Signer:</strong> {data.get("signer_name", "N/A")} ({data.get("signer_email", "N/A")})</p>'
        html += f'<p><strong>Original File Hash:</strong> {data.get("original_hash", "N/A")}</p>'
        
        # Signatures
        signatures = data.get('signatures', [])
        if signatures:
            html += '<h3>Signatures</h3>'
            html += '<ul>'
            for sig in signatures:
                html += f'<li>Signed by <strong>{sig.get("signer", "N/A")}</strong> on {sig.get("signed_at", "N/A")}<br>'
                html += f'IP: {sig.get("ip_address", "N/A")} | ID: {sig.get("id", "N/A")}</li>'
            html += '</ul>'
        
        # Events
        events = data.get('events', [])
        if events:
            html += '<h3>Event Log</h3>'
            html += '<ul>'
            for event in events:
                html += f'<li>{event.get("timestamp", "N/A")} - <strong>{event.get("type", "N/A")}</strong></li>'
            html += '</ul>'
        
        html += '</div>'
        return format_html(html)
    
    audit_trail_display.short_description = 'Audit Trail Report'
    
    
    def status_badge(self, obj):
        """Display status with color badge"""
        colors = {
            'created': 'gray',
            'otp_sent': 'blue',
            'otp_verified': 'lightblue',
            'signing': 'orange',
            'signed': 'green',
            'failed': 'red',
            'cancelled': 'darkgray',
            'expired': 'brown',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def download_link(self, obj):
        """Display download link for signed PDF"""
        if obj.signed_pdf:
            return format_html(
                '<a href="{}" target="_blank">Download Signed PDF</a>',
                obj.signed_pdf.url
            )
        return '-'
    download_link.short_description = 'Download'


@admin.register(SignatureField)
class SignatureFieldAdmin(admin.ModelAdmin):
    """Admin interface for SignatureField"""
    list_display = [
        'id',
        'session',
        'page_number',
        'name',
        'required',
        'is_signed',
        'created_at',
    ]
    list_filter = ['required', 'is_signed', 'page_number']
    search_fields = ['session__id', 'name', 'label']
    readonly_fields = ['id', 'created_at']
    
    fieldsets = (
        ('Field Information', {
            'fields': ('id', 'session', 'name', 'label', 'required', 'order')
        }),
        ('Position', {
            'fields': ('page_number', 'x', 'y', 'width', 'height')
        }),
        ('Status', {
            'fields': ('is_signed', 'created_at')
        }),
    )


@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    """Admin interface for OTP"""
    list_display = [
        'id',
        'session',
        'is_verified',
        'attempts',
        'max_attempts',
        'expires_at',
        'created_at',
    ]
    list_filter = ['is_verified', 'created_at']
    search_fields = ['session__id', 'session__signer_email']
    readonly_fields = [
        'id',
        'otp_hash',
        'created_at',
        'verified_at',
    ]
    
    fieldsets = (
        ('OTP Information', {
            'fields': ('id', 'session', 'otp_hash')
        }),
        ('Verification', {
            'fields': ('is_verified', 'attempts', 'max_attempts', 'expires_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'verified_at')
        }),
    )


@admin.register(Signature)
class SignatureAdmin(admin.ModelAdmin):
    """Admin interface for Signature"""
    list_display = [
        'id',
        'session',
        'method',
        'signer_email',
        'signer_name',
        'created_at',
        'signature_preview',
    ]
    list_filter = ['method', 'created_at']
    search_fields = ['session__id', 'signer_email', 'signer_name']
    readonly_fields = [
        'id',
        'created_at',
        'signature_preview',
    ]
    
    fieldsets = (
        ('Signature Information', {
            'fields': ('id', 'session', 'field', 'method', 'signature_image')
        }),
        ('Signer Details', {
            'fields': ('signer_name', 'signer_email', 'signer_reason', 'signer_location')
        }),
        ('Audit Trail', {
            'fields': ('ip_address', 'user_agent', 'created_at')
        }),
        ('Additional Info', {
            'fields': ('font_name',),
            'classes': ('collapse',)
        }),
    )
    
    def signature_preview(self, obj):
        """Display signature image preview"""
        if obj.signature_image:
            return format_html(
                '<img src="{}" style="max-width: 200px; max-height: 100px; border: 1px solid #ccc;" />',
                obj.signature_image.url
            )
        return '-'
    signature_preview.short_description = 'Preview'


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    """Admin interface for AuditEvent"""
    list_display = [
        'id',
        'session',
        'event_type',
        'ip_address',
        'created_at',
    ]
    list_filter = ['event_type', 'created_at']
    search_fields = ['session__id', 'event_type', 'ip_address']
    readonly_fields = ['id', 'created_at']
    
    fieldsets = (
        ('Event Information', {
            'fields': ('id', 'session', 'event_type', 'payload')
        }),
        ('Context', {
            'fields': ('ip_address', 'user_agent', 'created_at')
        }),
    )
    
    def has_add_permission(self, request):
        """Audit events should not be manually created"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Audit events should not be deleted"""
        return False

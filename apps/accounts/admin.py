from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import User, PaymentConfirmation


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'is_premium', 'email_verified', 'date_joined']
    list_filter = ['is_premium', 'email_verified', 'is_staff', 'is_active']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    readonly_fields = ['date_joined', 'last_login']


@admin.register(PaymentConfirmation)
class PaymentConfirmationAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'user_email',
        'plan_name',
        'plan_price_display',
        'status_badge',
        'submitted_at',
        'verified_at',
        'quick_actions'
    ]
    list_filter = ['status', 'plan_name', 'submitted_at', 'verified_at']
    search_fields = ['user__email', 'user__username', 'admin_notes']
    readonly_fields = [
        'user',
        'plan_name',
        'plan_price',
        'currency',
        'submitted_at',
        'verified_at',
        'verified_by',
        'ip_address',
        'user_agent'
    ]
    fieldsets = (
        ('Payment Information', {
            'fields': ('user', 'plan_name', 'plan_price', 'currency', 'status')
        }),
        ('Timestamps', {
            'fields': ('submitted_at', 'verified_at', 'verified_by')
        }),
        ('Admin Notes', {
            'fields': ('admin_notes',)
        }),
        ('Technical Details', {
            'fields': ('ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
    )
    actions = ['verify_payments', 'reject_payments']
    
    def user_email(self, obj):
        """Display user email with link to user admin."""
        return format_html(
            '<a href="/admin/accounts/user/{}/change/">{}</a>',
            obj.user.id,
            obj.user.email
        )
    user_email.short_description = 'User Email'
    
    def plan_price_display(self, obj):
        """Display price with currency."""
        return f"{obj.currency} {obj.plan_price}"
    plan_price_display.short_description = 'Price'
    
    def status_badge(self, obj):
        """Display status with colored badge."""
        colors = {
            'pending': '#FFA500',
            'verified': '#10B981',
            'rejected': '#EF4444',
            'refunded': '#6B7280',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            colors.get(obj.status, '#6B7280'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def quick_actions(self, obj):
        """Display quick action buttons."""
        if obj.status == 'pending':
            return format_html(
                '<a class="button" href="/admin/accounts/paymentconfirmation/{}/change/" '
                'style="background-color: #10B981; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px;">Verify</a>',
                obj.id
            )
        return '-'
    quick_actions.short_description = 'Actions'
    
    def verify_payments(self, request, queryset):
        """Bulk action to verify payments."""
        count = 0
        for payment in queryset.filter(status='pending'):
            payment.mark_as_verified(admin_user=request.user)
            count += 1
        
        self.message_user(
            request,
            f'{count} payment(s) verified and premium activated for users.'
        )
    verify_payments.short_description = 'Verify selected payments'
    
    def reject_payments(self, request, queryset):
        """Bulk action to reject payments."""
        count = queryset.filter(status='pending').update(status='rejected')
        self.message_user(
            request,
            f'{count} payment(s) rejected.'
        )
    reject_payments.short_description = 'Reject selected payments'

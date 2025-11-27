from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import User, PaymentConfirmation, Invoice


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
        'total_amount_display',
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
        'tax_rate',
        'tax_amount',
        'total_amount',
        'currency',
        'submitted_at',
        'verified_at',
        'verified_by',
        'ip_address',
        'user_agent'
    ]
    fieldsets = (
        ('Payment Information', {
            'fields': ('user', 'plan_name', 'plan_price', 'tax_rate', 'tax_amount', 'total_amount', 'currency', 'status')
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
    
    def save_model(self, request, obj, form, change):
        """Override save to automatically create invoice when status changes to verified."""
        # Check if this is an update (not a new object)
        if change:
            # Get the original object from database
            try:
                original = PaymentConfirmation.objects.get(pk=obj.pk)
                
                # Check if status changed from pending to verified
                if original.status == 'pending' and obj.status == 'verified':
                    # Call mark_as_verified to create invoice and activate premium
                    obj.mark_as_verified(admin_user=request.user)
                    # Don't call super().save_model() because mark_as_verified already saves
                    return
            except PaymentConfirmation.DoesNotExist:
                pass
        
        # For all other cases, use default save
        super().save_model(request, obj, form, change)
    
    def user_email(self, obj):
        """Display user email with link to user admin."""
        return format_html(
            '<a href="/admin/accounts/user/{}/change/">{}</a>',
            obj.user.id,
            obj.user.email
        )
    user_email.short_description = 'User Email'
    
    def total_amount_display(self, obj):
        """Display total amount with currency."""
        return f"{obj.currency} {obj.total_amount}"
    total_amount_display.short_description = 'Total Amount'
    
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
        """Bulk action to verify payments and generate invoices."""
        count = 0
        for payment in queryset.filter(status='pending'):
            payment.mark_as_verified(admin_user=request.user)
            count += 1
        
        self.message_user(
            request,
            f'{count} payment(s) verified, premium activated, and invoices generated.'
        )
    verify_payments.short_description = 'Verify selected payments and generate invoices'
    
    def reject_payments(self, request, queryset):
        """Bulk action to reject payments."""
        count = queryset.filter(status='pending').update(status='rejected')
        self.message_user(
            request,
            f'{count} payment(s) rejected.'
        )
    reject_payments.short_description = 'Reject selected payments'


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = [
        'invoice_number',
        'user_email',
        'plan_name',
        'total_amount_display',
        'payment_date',
        'payment_method',
        'download_link'
    ]
    list_filter = ['payment_method', 'payment_date', 'plan_name']
    search_fields = ['invoice_number', 'user__email', 'payment_id']
    readonly_fields = [
        'invoice_number',
        'tax_amount',
        'total_amount',
        'created_at',
        'updated_at'
    ]
    fieldsets = (
        ('Invoice Information', {
            'fields': ('invoice_number', 'user', 'payment_confirmation')
        }),
        ('Plan Details', {
            'fields': ('plan_name', 'plan_price', 'currency', 'tax_rate', 'tax_amount', 'total_amount')
        }),
        ('Payment Information', {
            'fields': ('payment_method', 'payment_id', 'payment_date')
        }),
        ('Billing Period', {
            'fields': ('billing_period_start', 'billing_period_end')
        }),
        ('Billing Address', {
            'fields': (
                'billing_name', 'billing_email', 'billing_phone',
                'billing_address', 'billing_city', 'billing_state',
                'billing_pincode', 'billing_country'
            ),
            'classes': ('collapse',)
        }),
        ('Company Information', {
            'fields': ('company_gstn',)
        }),
        ('Additional Information', {
            'fields': ('notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def user_email(self, obj):
        """Display user email with link to user admin."""
        return format_html(
            '<a href="/admin/accounts/user/{}/change/">{}</a>',
            obj.user.id,
            obj.user.email
        )
    user_email.short_description = 'User'
    
    def total_amount_display(self, obj):
        """Display total amount with currency symbol."""
        return f"₹{obj.total_amount:.2f}"
    total_amount_display.short_description = 'Total'
    
    def download_link(self, obj):
        """Display download PDF button."""
        from django.urls import reverse
        download_url = reverse('dashboard:download_invoice', kwargs={'invoice_id': obj.id})
        return format_html(
            '<a href="{}" target="_blank" class="button" '
            'style="background-color: #14B8A6; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px;">'
            'Download PDF</a>',
            download_url
        )
    download_link.short_description = 'Actions'

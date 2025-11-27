from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    """
    Custom user model extending Django's AbstractUser.
    Includes premium status, usage tracking, and profile information.
    """
    is_premium = models.BooleanField(
        default=False,
        help_text='Premium subscription status'
    )
    credits = models.IntegerField(
        default=10,
        help_text='Daily usage credits (default: 10 for free users)'
    )
    avatar = models.ImageField(
        upload_to='avatars/',
        null=True,
        blank=True,
        help_text='User profile picture'
    )
    
    # Email verification fields
    email_verified = models.BooleanField(
        default=False,
        help_text='Email verification status'
    )
    email_verification_token = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='Token for email verification'
    )
    email_verification_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When verification email was sent'
    )
    
    # Usage tracking fields
    daily_usage_count = models.IntegerField(
        default=0,
        help_text='Number of conversions performed today'
    )
    last_reset_date = models.DateField(
        default=timezone.now,
        help_text='Last date when daily usage was reset'
    )

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.username



class UserProfile(models.Model):
    """
    Extended user profile with additional information and preferences.
    One-to-one relationship with User model.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        help_text='Related user account'
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        help_text='Contact phone number'
    )
    bio = models.TextField(
        blank=True,
        help_text='User biography or description'
    )
    preferred_theme = models.ForeignKey(
        'common.SiteTheme',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        help_text='User preferred theme'
    )
    email_notifications = models.BooleanField(
        default=True,
        help_text='Receive email notifications'
    )
    marketing_emails = models.BooleanField(
        default=False,
        help_text='Receive marketing and promotional emails'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def __str__(self):
        return f"{self.user.username}'s Profile"



class PaymentConfirmation(models.Model):
    """
    Track payment confirmations from users.
    Stores details when users indicate they have completed payment.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending Verification'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
        ('refunded', 'Refunded'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='payment_confirmations',
        help_text='User who submitted the payment confirmation'
    )
    plan_name = models.CharField(
        max_length=100,
        default='Premium',
        help_text='Name of the plan purchased'
    )
    plan_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Price of the plan'
    )
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=18.00,
        help_text='Tax rate in percentage (e.g., 18.00 for 18% GST)'
    )
    tax_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text='Calculated tax amount'
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text='Total amount including tax'
    )
    currency = models.CharField(
        max_length=3,
        default='INR',
        help_text='Currency code (e.g., INR, USD)'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text='Verification status of the payment'
    )
    
    # Timestamps
    submitted_at = models.DateTimeField(
        auto_now_add=True,
        help_text='When the user submitted the confirmation'
    )
    verified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the payment was verified by admin'
    )
    
    # Admin notes
    admin_notes = models.TextField(
        blank=True,
        help_text='Internal notes from admin about this payment'
    )
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_payments',
        help_text='Admin user who verified this payment'
    )
    
    # Additional tracking
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text='IP address of the user when submitting'
    )
    user_agent = models.TextField(
        blank=True,
        help_text='Browser user agent string'
    )
    
    # Verification token for one-click email verification
    verification_token = models.CharField(
        max_length=64,
        blank=True,
        help_text='Secure token for email verification link'
    )
    token_created_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the verification token was created'
    )
    token_used = models.BooleanField(
        default=False,
        help_text='Whether the verification token has been used'
    )
    
    class Meta:
        verbose_name = 'Payment Confirmation'
        verbose_name_plural = 'Payment Confirmations'
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['submitted_at']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.plan_name} - {self.status}"
    
    def save(self, *args, **kwargs):
        """Calculate tax and total before saving."""
        if not self.tax_amount or self.tax_amount == 0:
            self.tax_amount = (self.plan_price * self.tax_rate) / 100
        if not self.total_amount or self.total_amount == 0:
            self.total_amount = self.plan_price + self.tax_amount
        
        # Generate verification token if not exists
        if not self.verification_token:
            import secrets
            self.verification_token = secrets.token_urlsafe(32)
            self.token_created_at = timezone.now()
        
        super().save(*args, **kwargs)
    
    def is_token_valid(self):
        """Check if verification token is still valid (not expired and not used)."""
        if self.token_used:
            return False
        
        if not self.token_created_at:
            return False
        
        # Token expires after 7 days
        from datetime import timedelta
        expiry_time = self.token_created_at + timedelta(days=7)
        return timezone.now() < expiry_time
    
    def mark_as_verified(self, admin_user=None, payment_id='', payment_method='upi'):
        """Mark payment as verified, activate premium, and create invoice."""
        from datetime import timedelta, datetime
        
        # Generate payment ID if not provided
        if not payment_id:
            date_str = datetime.now().strftime('%d%m%Y')
            payment_id = f'PAYID_{date_str}_{self.id:05d}'
        
        # Set verified timestamp (but don't save yet)
        verified_at = timezone.now()
        
        # Create invoice FIRST (before changing status)
        # This way if invoice creation fails, payment status remains unchanged
        billing_start = timezone.now().date()
        billing_end = billing_start + timedelta(days=30)
        
        invoice = Invoice.objects.create(
            invoice_number=Invoice.generate_invoice_number(),
            user=self.user,
            payment_confirmation=self,
            plan_name=self.plan_name,
            plan_price=self.plan_price,
            tax_rate=self.tax_rate,
            tax_amount=self.tax_amount,
            total_amount=self.total_amount,
            currency=self.currency,
            payment_method=payment_method,
            payment_id=payment_id,
            payment_date=verified_at,
            billing_period_start=billing_start,
            billing_period_end=billing_end,
            billing_name=self.user.get_full_name() or self.user.username,
            billing_email=self.user.email,
        )
        
        # Invoice created successfully, now update payment status
        self.status = 'verified'
        self.verified_at = verified_at
        self.verified_by = admin_user
        self.save()
        
        # Activate premium for user
        self.user.is_premium = True
        self.user.save()
        
        return invoice
    
    def mark_as_rejected(self, reason=''):
        """Mark payment as rejected."""
        self.status = 'rejected'
        if reason:
            self.admin_notes = reason
        self.save()



class Invoice(models.Model):
    """
    Invoice for premium subscriptions.
    Stores complete billing information including GSTN.
    """
    PAYMENT_METHOD_CHOICES = [
        ('upi', 'UPI'),
        ('bank_transfer', 'Bank Transfer'),
        ('card', 'Credit/Debit Card'),
        ('cash', 'Cash'),
        ('other', 'Other'),
    ]
    
    # Invoice identification
    invoice_number = models.CharField(
        max_length=50,
        unique=True,
        help_text='Unique invoice number (e.g., INV-2024-001)'
    )
    
    # Related records
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='invoices',
        help_text='User who made the payment'
    )
    payment_confirmation = models.OneToOneField(
        PaymentConfirmation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invoice',
        help_text='Related payment confirmation'
    )
    
    # Billing details
    plan_name = models.CharField(max_length=100, default='Premium')
    plan_price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='INR')
    
    # Tax information
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=18.00,
        help_text='Tax rate in percentage (e.g., 18.00 for 18% GST)'
    )
    tax_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Calculated tax amount'
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Total amount including tax'
    )
    
    # Company GSTN
    company_gstn = models.CharField(
        max_length=15,
        default='29AFQPV0371Q1ZD',
        help_text='Company GSTN number'
    )
    
    # Payment details
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='upi'
    )
    payment_id = models.CharField(
        max_length=100,
        blank=True,
        help_text='Transaction/Payment ID from payment gateway'
    )
    payment_date = models.DateTimeField(
        help_text='Date when payment was received'
    )
    
    # Billing period
    billing_period_start = models.DateField(
        help_text='Start date of billing period'
    )
    billing_period_end = models.DateField(
        help_text='End date of billing period'
    )
    
    # Customer billing address
    billing_name = models.CharField(max_length=200, blank=True)
    billing_email = models.EmailField()
    billing_phone = models.CharField(max_length=20, blank=True)
    billing_address = models.TextField(blank=True)
    billing_city = models.CharField(max_length=100, blank=True)
    billing_state = models.CharField(max_length=100, blank=True)
    billing_pincode = models.CharField(max_length=10, blank=True)
    billing_country = models.CharField(max_length=100, default='India')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Notes
    notes = models.TextField(blank=True, help_text='Additional notes for invoice')
    
    class Meta:
        verbose_name = 'Invoice'
        verbose_name_plural = 'Invoices'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'payment_date']),
            models.Index(fields=['invoice_number']),
            models.Index(fields=['payment_date']),
        ]
    
    def __str__(self):
        return f"{self.invoice_number} - {self.user.email} - ₹{self.total_amount}"
    
    def save(self, *args, **kwargs):
        """Calculate tax and total before saving."""
        if not self.tax_amount:
            self.tax_amount = (self.plan_price * self.tax_rate) / 100
        if not self.total_amount:
            self.total_amount = self.plan_price + self.tax_amount
        super().save(*args, **kwargs)
    
    @classmethod
    def generate_invoice_number(cls):
        """Generate unique invoice number in format STPDF-ddmmyyyy00001."""
        from datetime import datetime
        from django.db import transaction
        
        now = datetime.now()
        date_str = now.strftime('%d%m%Y')
        
        # Use transaction to prevent race conditions
        with transaction.atomic():
            # Get all invoices for today to find the highest sequence
            today_invoices = cls.objects.filter(
                invoice_number__startswith=f'STPDF-{date_str}'
            ).select_for_update()
            
            if today_invoices.exists():
                # Find the maximum sequence number
                max_seq = 0
                for invoice in today_invoices:
                    try:
                        # Extract last 5 digits as sequence
                        sequence_part = invoice.invoice_number[-5:]
                        seq = int(sequence_part)
                        if seq > max_seq:
                            max_seq = seq
                    except (ValueError, IndexError):
                        continue
                
                new_seq = max_seq + 1
            else:
                new_seq = 1
            
            # Keep trying until we find a unique number
            max_attempts = 100
            for attempt in range(max_attempts):
                invoice_number = f'STPDF-{date_str}{new_seq:05d}'
                
                # Check if this number already exists
                if not cls.objects.filter(invoice_number=invoice_number).exists():
                    return invoice_number
                
                # If it exists, try the next number
                new_seq += 1
            
            # If we couldn't find a unique number after max_attempts, raise an error
            raise ValueError(f"Could not generate unique invoice number after {max_attempts} attempts")

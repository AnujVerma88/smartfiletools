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
    
    def mark_as_verified(self, admin_user=None):
        """Mark payment as verified and activate premium for user."""
        self.status = 'verified'
        self.verified_at = timezone.now()
        self.verified_by = admin_user
        self.save()
        
        # Activate premium for user
        self.user.is_premium = True
        self.user.save()
    
    def mark_as_rejected(self, reason=''):
        """Mark payment as rejected."""
        self.status = 'rejected'
        if reason:
            self.admin_notes = reason
        self.save()

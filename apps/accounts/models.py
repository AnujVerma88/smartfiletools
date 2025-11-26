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

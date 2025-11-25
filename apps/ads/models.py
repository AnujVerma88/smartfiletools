"""
Advertisement models for managing promotional content.
"""
from django.db import models
from django.utils import timezone


class Advertisement(models.Model):
    """
    Model for managing advertisements displayed on the platform.
    """
    POSITION_CHOICES = [
        ('home_top', 'Home Page - Top Banner'),
        ('home_sidebar', 'Home Page - Sidebar'),
        ('tool_top', 'Tool Page - Top Banner'),
        ('tool_bottom', 'Tool Page - Bottom Banner'),
        ('dashboard_sidebar', 'Dashboard - Sidebar'),
        ('result_page', 'Result Page - Bottom'),
    ]

    title = models.CharField(
        max_length=200,
        help_text='Advertisement title'
    )
    description = models.TextField(
        blank=True,
        help_text='Optional description of the advertisement'
    )
    image = models.ImageField(
        upload_to='ads/',
        help_text='Advertisement image'
    )
    link_url = models.URLField(
        help_text='URL to redirect when ad is clicked'
    )
    position = models.CharField(
        max_length=50,
        choices=POSITION_CHOICES,
        help_text='Where the ad should be displayed'
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this ad is currently active'
    )
    
    # Tracking fields
    impression_count = models.IntegerField(
        default=0,
        help_text='Number of times the ad has been displayed'
    )
    click_count = models.IntegerField(
        default=0,
        help_text='Number of times the ad has been clicked'
    )
    
    # Scheduling fields
    start_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the ad should start displaying (optional)'
    )
    end_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the ad should stop displaying (optional)'
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Advertisement'
        verbose_name_plural = 'Advertisements'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.position})"

    def is_scheduled_active(self):
        """
        Check if ad is within its scheduled date range.
        """
        now = timezone.now()
        
        # If no dates set, always active
        if not self.start_date and not self.end_date:
            return True
        
        # Check start date
        if self.start_date and now < self.start_date:
            return False
        
        # Check end date
        if self.end_date and now > self.end_date:
            return False
        
        return True

    def increment_impression(self):
        """Increment impression count."""
        self.impression_count += 1
        self.save(update_fields=['impression_count'])

    def increment_click(self):
        """Increment click count."""
        self.click_count += 1
        self.save(update_fields=['click_count'])

    def get_ctr(self):
        """
        Calculate click-through rate (CTR).
        
        Returns:
            float: CTR as percentage
        """
        if self.impression_count == 0:
            return 0.0
        return (self.click_count / self.impression_count) * 100

    @classmethod
    def get_active_ad(cls, position):
        """
        Get an active ad for a specific position.
        
        Args:
            position: Ad position identifier
            
        Returns:
            Advertisement instance or None
        """
        now = timezone.now()
        
        # Query for active ads in the position
        ads = cls.objects.filter(
            position=position,
            is_active=True
        )
        
        # Filter by date range
        ads = ads.filter(
            models.Q(start_date__isnull=True) | models.Q(start_date__lte=now)
        ).filter(
            models.Q(end_date__isnull=True) | models.Q(end_date__gte=now)
        )
        
        # Return first active ad (could be randomized in future)
        return ads.first()

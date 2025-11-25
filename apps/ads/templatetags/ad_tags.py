"""
Template tags for displaying advertisements.
"""
from django import template
from apps.ads.models import Advertisement

register = template.Library()


@register.inclusion_tag('ads/ad_display.html')
def show_ad(position):
    """
    Display an active advertisement for the given position.
    Automatically tracks impressions.
    
    Usage in templates:
        {% load ad_tags %}
        {% show_ad 'home_top' %}
    
    Args:
        position: Ad position identifier (e.g., 'home_top', 'tool_top')
        
    Returns:
        Context dict with ad data
    """
    ad = Advertisement.get_active_ad(position)
    
    return {
        'ad': ad,
        'position': position,
    }


@register.simple_tag
def get_ad(position):
    """
    Get an active advertisement for the given position without rendering.
    
    Usage in templates:
        {% load ad_tags %}
        {% get_ad 'home_top' as my_ad %}
        {% if my_ad %}
            <!-- Custom ad display -->
        {% endif %}
    
    Args:
        position: Ad position identifier
        
    Returns:
        Advertisement instance or None
    """
    return Advertisement.get_active_ad(position)


@register.filter
def ad_ctr(ad):
    """
    Get click-through rate for an advertisement.
    
    Usage in templates:
        {{ ad|ad_ctr }}
    
    Args:
        ad: Advertisement instance
        
    Returns:
        str: Formatted CTR percentage
    """
    if not ad:
        return "0.00%"
    return f"{ad.get_ctr():.2f}%"

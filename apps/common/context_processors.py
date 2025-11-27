"""
Context processors for making data available in all templates.
"""
from .models import SiteTheme, SiteStatistics


def theme_context(request):
    """
    Add active theme to all template contexts.
    """
    active_theme = SiteTheme.get_active_theme()
    return {
        'active_theme': active_theme,
        'primary_color': active_theme.primary_color if active_theme else '#14B8A6',
        'primary_color_rgb': active_theme.primary_color_rgb if active_theme else '20, 184, 166',
    }


def site_statistics(request):
    """
    Add site statistics to all template contexts with calculated totals.
    """
    stats = SiteStatistics.get_stats()
    return {
        'site_stats': {
            'files_converted': stats.get_total_files_converted(),
            'happy_users': stats.get_total_happy_users(),
            'tools_available': stats.get_total_tools_available(),
            'uptime_percentage': stats.uptime_percentage,
        }
    }

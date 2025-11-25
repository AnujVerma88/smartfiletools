"""
Context processors for the common app.
Provides theme data to all templates.
"""
from .models import SiteTheme


def theme_context(request):
    """
    Add active theme to all template contexts.
    This allows templates to access theme colors and CSS variables.
    """
    theme = SiteTheme.get_active_theme()
    return {
        'site_theme': theme,
        'theme_css_vars': theme.get_css_variables()
    }

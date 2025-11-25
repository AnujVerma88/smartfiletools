"""
SmartFileTools URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/

URL Structure:
    - /admin/ - Django admin interface
    - / - Home page and dashboard
    - /accounts/ - User authentication and profile management
    - /tools/ - File conversion tools
    - /ads/ - Advertisement tracking
    - /api/ - RESTful API endpoints (v1)
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

# Admin site customization
admin.site.site_header = 'SmartFileTools Administration'
admin.site.site_title = 'SmartFileTools Admin'
admin.site.index_title = 'Welcome to SmartFileTools Administration'

urlpatterns = [
    # Admin interface
    path('admin/', admin.site.urls),
    
    # Main application URLs
    path('', include('apps.dashboard.urls')),  # Home, dashboard, static pages
    path('accounts/', include('apps.accounts.urls')),  # Authentication, profile
    path('tools/', include('apps.tools.urls')),  # File conversion tools
    path('ads/', include('apps.ads.urls')),  # Advertisement tracking
    path('api/', include('apps.api.urls')),  # RESTful API (v1)
    
    # Favicon redirect (optional)
    path('favicon.ico', RedirectView.as_view(url=settings.STATIC_URL + 'images/logo/favicon.ico', permanent=True)),
]

# Serve static and media files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Custom error handlers (optional - uncomment to use custom error pages)
# handler404 = 'apps.common.views.custom_404'
# handler500 = 'apps.common.views.custom_500'
# handler403 = 'apps.common.views.custom_403'
# handler400 = 'apps.common.views.custom_400'

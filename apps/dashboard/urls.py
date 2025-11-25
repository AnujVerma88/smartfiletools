"""
URL patterns for home page and dashboard.
"""
from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('search/', views.search_tools_view, name='search'),
    path('upgrade/', views.upgrade_view, name='upgrade'),
    path('billing/', views.billing_view, name='billing'),
    path('privacy/', views.privacy_view, name='privacy'),
    path('terms/', views.terms_view, name='terms'),
    path('about/', views.about_view, name='about'),
    path('pricing/', views.pricing_view, name='pricing'),
    path('contact/', views.contact_view, name='contact'),
    path('help/', views.help_view, name='help'),
    path('faq/', views.faq_view, name='faq'),
    path('security/', views.security_view, name='security'),
]

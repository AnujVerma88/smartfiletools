"""
URL patterns for advertisement tracking.
"""
from django.urls import path
from . import views

app_name = 'ads'

urlpatterns = [
    path('track-impression/<int:ad_id>/', views.track_impression, name='track_impression'),
    path('track-click/<int:ad_id>/', views.track_click, name='track_click'),
]

"""
URL patterns for tools and conversions.
"""
from django.urls import path
from . import views

app_name = 'tools'

urlpatterns = [
    # Tool listing
    path('', views.ToolListView.as_view(), name='tool_list'),
    
    # Conversion history (must come before tool detail to avoid slug conflict)
    path('history/', views.conversion_history_view, name='conversion_history'),
    path('history/<int:conversion_id>/', views.conversion_detail_view, name='conversion_detail'),
    
    # File upload and conversion
    path('upload/<slug:tool_slug>/', views.file_upload_view, name='file_upload'),
    path('conversion/<int:conversion_id>/initiate/', views.conversion_initiate_view, name='conversion_initiate'),
    path('conversion/<int:conversion_id>/status/', views.conversion_status_view, name='conversion_status'),
    path('conversion/<int:conversion_id>/status/api/', views.conversion_status_api, name='conversion_status_api'),
    path('download/<int:conversion_id>/', views.file_download_view, name='file_download'),
    
    # Category and tool detail (must come last due to slug pattern)
    path('category/<slug:slug>/', views.tool_category_view, name='category_detail'),
    path('<slug:slug>/', views.ToolDetailView.as_view(), name='tool_detail'),
]

"""
API URL Configuration.
Provides RESTful API endpoints for file conversion and user management.
"""
from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView
from . import views
from . import views_merchant

app_name = 'api'

# Authentication endpoints
auth_patterns = [
    path('register/', views.UserRegistrationView.as_view(), name='register'),
    path('login/', views.UserLoginView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', views.UserLogoutView.as_view(), name='logout'),
]

# Tool endpoints
tool_patterns = [
    path('', views.ToolListView.as_view(), name='tool-list'),
    path('<slug:slug>/', views.ToolDetailView.as_view(), name='tool-detail'),
]

# Conversion endpoints
conversion_patterns = [
    path('pdf-to-docx/', views.ConvertPDFToDocxView.as_view(), name='convert-pdf-to-docx'),
    path('docx-to-pdf/', views.ConvertDocxToPDFView.as_view(), name='convert-docx-to-pdf'),
    path('xlsx-to-pdf/', views.ConvertXLSXToPDFView.as_view(), name='convert-xlsx-to-pdf'),
    path('pptx-to-pdf/', views.ConvertPPTXToPDFView.as_view(), name='convert-pptx-to-pdf'),
    path('image-to-pdf/', views.ConvertImageToPDFView.as_view(), name='convert-image-to-pdf'),
    path('merge-pdf/', views.MergePDFView.as_view(), name='merge-pdf'),
    path('split-pdf/', views.SplitPDFView.as_view(), name='split-pdf'),
    path('compress-pdf/', views.CompressPDFView.as_view(), name='compress-pdf'),
    path('compress-image/', views.CompressImageView.as_view(), name='compress-image'),
    path('convert-image/', views.ConvertImageView.as_view(), name='convert-image'),
    path('compress-video/', views.CompressVideoView.as_view(), name='compress-video'),
    path('extract-text/', views.ExtractTextView.as_view(), name='extract-text'),
]

# Conversion status and download endpoints
conversion_detail_patterns = [
    path('<int:pk>/', views.ConversionDetailView.as_view(), name='conversion-detail'),
    path('<int:pk>/download/', views.ConversionDownloadView.as_view(), name='conversion-download'),
    path('', views.ConversionHistoryListView.as_view(), name='conversion-list'),
]

# User profile endpoints
user_patterns = [
    path('profile/', views.UserProfileView.as_view(), name='user-profile'),
    path('profile/update/', views.UserProfileUpdateView.as_view(), name='user-profile-update'),
    path('usage/', views.UserUsageStatisticsView.as_view(), name='user-usage'),
    path('history/', views.UserConversionHistoryView.as_view(), name='user-history'),
]

# API Access Request endpoints (web views, not REST API)
api_access_patterns = [
    path('', views.APIAccessRequestView.as_view(), name='api_access_request'),
    path('thank-you/', views.APIAccessThankYouView.as_view(), name='api_access_thank_you'),
]

# Merchant dashboard and API key management endpoints
merchant_patterns = [
    path('dashboard/', views_merchant.MerchantDashboardView.as_view(), name='merchant_dashboard'),
    path('keys/', views_merchant.APIKeyListView.as_view(), name='merchant_api_keys'),
    path('keys/create/', views_merchant.APIKeyCreateView.as_view(), name='merchant_api_key_create'),
    path('keys/<int:key_id>/regenerate/', views_merchant.APIKeyRegenerateView.as_view(), name='merchant_api_key_regenerate'),
    path('keys/<int:key_id>/revoke/', views_merchant.APIKeyRevokeView.as_view(), name='merchant_api_key_revoke'),
    path('keys/<int:key_id>/delete/', views_merchant.APIKeyDeleteView.as_view(), name='merchant_api_key_delete'),
    path('keys/credentials/', views_merchant.APIKeyCredentialsView.as_view(), name='merchant_api_key_credentials'),
    path('usage/', views_merchant.MerchantUsageView.as_view(), name='merchant_usage'),
    path('webhooks/', views_merchant.WebhookConfigurationView.as_view(), name='merchant_webhooks'),
    path('webhooks/update/', views_merchant.WebhookUpdateView.as_view(), name='merchant_webhook_update'),
    path('webhooks/test/', views_merchant.WebhookTestView.as_view(), name='merchant_webhook_test'),
]

# API v1 URL patterns
urlpatterns = [
    path('v1/auth/', include(auth_patterns)),
    path('v1/tools/', include(tool_patterns)),
    path('v1/convert/', include(conversion_patterns)),
    path('v1/conversions/', include(conversion_detail_patterns)),
    path('v1/user/', include(user_patterns)),
    # Web-based API access request form
    path('access/', include(api_access_patterns)),
    # Merchant dashboard and management
    path('merchant/', include(merchant_patterns)),
]

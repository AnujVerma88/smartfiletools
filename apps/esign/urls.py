"""
URL routing for E-Sign app
"""
from django.urls import path
from . import views

app_name = 'esign'

urlpatterns = [
    # Web UI for authenticated users
    path('upload/', views.upload_pdf, name='upload'),
    path('session/<uuid:session_id>/place-fields/', views.place_fields, name='place_fields'),
    
    # Public signing page (no auth required, OTP validates)
    path('sign/<uuid:session_id>/', views.sign_document, name='sign'),
    path('sign/<uuid:session_id>/otp/', views.verify_otp_page, name='verify_otp_page'),
    path('sign/<uuid:session_id>/otp/verify/', views.verify_otp, name='verify_otp'),
    path('sign/<uuid:session_id>/otp/resend/', views.resend_otp, name='resend_otp'),
    path('sign/<uuid:session_id>/signature/save/', views.save_signature, name='save_signature'),
    path('sign/<uuid:session_id>/complete/', views.complete_signing, name='complete'),
    
    
    # Download & Status
    path('status/<uuid:session_id>/', views.status_page, name='status'),
    path('download/<uuid:session_id>/', views.download_signed_pdf, name='download'),
    
    # Status check (AJAX)
    path('session/<uuid:session_id>/status/', views.session_status, name='session_status'),
]

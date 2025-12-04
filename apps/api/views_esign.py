from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from django.http import FileResponse
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from apps.esign.models import SignSession, AuditEvent, OTP
from apps.esign.utils.email import send_otp_email
from .models import APIUsageLog
import random
import string
import logging

logger = logging.getLogger('apps.api')

class ESignCreateSessionView(APIView):
    """
    Create a new E-Sign session.
    POST /api/v1/esign/create/
    """
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        # Ensure request is authenticated via API Key
        if not hasattr(request, 'merchant') or not request.merchant:
            return Response(
                {'success': False, 'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        merchant = request.merchant
        
        # Check quota
        if not merchant.has_quota_remaining():
            return Response(
                {'success': False, 'error': 'Monthly request quota exceeded'},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )

        file_obj = request.FILES.get('file')
        signer_email = request.data.get('signer_email')
        signer_name = request.data.get('signer_name')

        if not file_obj or not signer_email or not signer_name:
            return Response(
                {'success': False, 'error': 'Missing required fields: file, signer_email, signer_name'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not file_obj.name.lower().endswith('.pdf'):
             return Response(
                {'success': False, 'error': 'Only PDF files are allowed'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Create Session
            session = SignSession.objects.create(
                user=merchant.user, # Link to merchant's user account
                signer_email=signer_email,
                signer_name=signer_name,
                original_pdf=file_obj,
                original_filename=file_obj.name,
                original_file_size=file_obj.size,
                expires_at=timezone.now() + timedelta(hours=settings.ESIGN_SESSION_EXPIRY_HOURS),
                status='created',
                metadata={'source': 'api', 'merchant_id': merchant.id}
            )

            # Create Audit Event
            AuditEvent.objects.create(
                session=session,
                event_type='session_created',
                payload={'source': 'api', 'filename': file_obj.name},
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            # Generate and Send OTP (Auto-send for API created sessions too?)
            # Yes, standard flow.
            otp_code = ''.join(random.choices(string.digits, k=settings.ESIGN_OTP_LENGTH))
            OTP.objects.create(
                session=session,
                otp_hash=otp_code,
                expires_at=timezone.now() + timedelta(minutes=settings.ESIGN_OTP_EXPIRY_MINUTES)
            )
            
            email_sent = send_otp_email(session, otp_code)
            if email_sent:
                session.status = 'otp_sent'
                session.save()

            # Log API Usage
            merchant.increment_usage()
            APIUsageLog.objects.create(
                merchant=merchant,
                api_key=request.api_key,
                endpoint=request.path,
                method=request.method,
                status_code=201,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                request_size=file_obj.size,
                tool_type='esign'
            )

            return Response({
                'success': True,
                'session_id': session.id,
                'status': session.status,
                'signing_url': f"{settings.SITE_URL}/esign/sign/{session.id}/",
                'message': 'Session created and OTP sent' if email_sent else 'Session created but OTP email failed'
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"API Session Create Error: {str(e)}")
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ESignStatusView(APIView):
    """
    Get status of an E-Sign session.
    GET /api/v1/esign/status/<session_id>/
    """
    def get(self, request, session_id):
        if not hasattr(request, 'merchant') or not request.merchant:
            return Response({'success': False, 'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        session = get_object_or_404(SignSession, id=session_id)

        # Security: Ensure merchant owns this session
        if session.user != request.merchant.user:
             return Response({'success': False, 'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            'success': True,
            'session_id': session.id,
            'status': session.status,
            'created_at': session.created_at,
            'signed_at': session.signed_at,
            'is_expired': session.is_expired()
        })

class ESignDownloadView(APIView):
    """
    Download signed PDF.
    GET /api/v1/esign/download/<session_id>/
    """
    def get(self, request, session_id):
        if not hasattr(request, 'merchant') or not request.merchant:
            return Response({'success': False, 'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        session = get_object_or_404(SignSession, id=session_id)

        if session.user != request.merchant.user:
             return Response({'success': False, 'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

        if not session.signed_pdf:
            return Response({'success': False, 'error': 'Document not signed yet'}, status=status.HTTP_400_BAD_REQUEST)

        # Log API Usage (Download)
        APIUsageLog.objects.create(
            merchant=request.merchant,
            api_key=request.api_key,
            endpoint=request.path,
            method=request.method,
            status_code=200,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            response_size=session.signed_pdf.size,
            tool_type='esign_download'
        )

        return FileResponse(session.signed_pdf.open('rb'), as_attachment=True, filename=f"signed_{session.original_filename}")

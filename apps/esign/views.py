"""
Views for E-Sign web interface.
Placeholder implementations - will be completed in next phase.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, FileResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from .models import SignSession


@login_required
def upload_pdf(request):
    """Upload PDF for signing"""
    from apps.tools.models import Tool
    from .models import SignSession, AuditEvent, OTP
    from django.conf import settings
    from .utils.email import send_otp_email
    import os
    import random
    import string
    
    # Get or create the E-Sign tool
    try:
        tool = Tool.objects.get(tool_type='esign')
    except Tool.DoesNotExist:
        messages.warning(request, 'E-Sign tool is not configured yet.')
        return redirect('dashboard:home')
    
    if request.method == 'POST':
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            messages.error(request, 'Please select a file.')
            return redirect('esign:upload')
            
        try:
            # Validate file
            if uploaded_file.size > settings.ESIGN_MAX_FILE_SIZE:
                messages.error(request, f'File too large. Max size is {settings.ESIGN_MAX_FILE_SIZE/1024/1024}MB.')
                return redirect('esign:upload')
                
            if not uploaded_file.name.lower().endswith('.pdf'):
                messages.error(request, 'Only PDF files are allowed.')
                return redirect('esign:upload')

            # Create session
            from django.utils import timezone
            from datetime import timedelta
            
            session = SignSession.objects.create(
                user=request.user,
                signer_email=request.user.email,
                signer_name=request.user.get_full_name() or request.user.username,
                original_pdf=uploaded_file,
                original_filename=uploaded_file.name,
                original_file_size=uploaded_file.size,
                expires_at=timezone.now() + timedelta(hours=settings.ESIGN_SESSION_EXPIRY_HOURS),
                status='created'
            )
            
            # Create audit event
            AuditEvent.objects.create(
                session=session,
                event_type='session_created',
                payload={'filename': uploaded_file.name},
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            # Generate and send OTP
            otp_code = ''.join(random.choices(string.digits, k=settings.ESIGN_OTP_LENGTH))
            OTP.objects.create(
                session=session,
                otp_hash=otp_code,  # In a real app, hash this! For MVP, storing plain
                expires_at=timezone.now() + timedelta(minutes=settings.ESIGN_OTP_EXPIRY_MINUTES)
            )
            
            if send_otp_email(session, otp_code):
                session.status = 'otp_sent'
                session.save()
                messages.success(request, f'Verification code sent to {session.signer_email}')
                return redirect('esign:verify_otp_page', session_id=session.id)
            else:
                messages.error(request, 'Failed to send verification email. Please try again.')
                return redirect('esign:upload')
            
        except Exception as e:
            messages.error(request, f'Error processing file: {str(e)}')
            return redirect('esign:upload')
    
    context = {
        'tool': tool,
        'page_title': 'E-Sign PDF - Upload Document',
    }
    return render(request, 'esign/upload.html', context)


@login_required
def place_fields(request, session_id):
    """Place signature fields on PDF pages"""
    session = get_object_or_404(SignSession, id=session_id, user=request.user)
    # TODO: Implement field placement logic
    return render(request, 'esign/place_fields.html', {'session': session})


@login_required
def verify_otp_page(request, session_id):
    """Page to enter OTP"""
    session = get_object_or_404(SignSession, id=session_id)
    
    if session.status == 'otp_verified' or session.status == 'signing':
        return redirect('esign:sign', session_id=session.id)
        
    return render(request, 'esign/verify_otp.html', {'session': session})


@require_http_methods(["POST"])
def verify_otp(request, session_id):
    """Verify OTP code submission"""
    from .models import OTP, AuditEvent
    from django.utils import timezone
    
    session = get_object_or_404(SignSession, id=session_id)
    otp_input = request.POST.get('otp')
    
    if not otp_input:
        messages.error(request, 'Please enter the verification code.')
        return redirect('esign:verify_otp_page', session_id=session.id)
        
    # Find valid OTP
    otp = OTP.objects.filter(
        session=session,
        otp_hash=otp_input,
        is_verified=False,
        expires_at__gt=timezone.now()
    ).first()
    
    if otp:
        otp.is_verified = True
        otp.verified_at = timezone.now()
        otp.save()
        
        session.status = 'otp_verified'
        session.save()
        
        AuditEvent.objects.create(
            session=session,
            event_type='otp_verified',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return redirect('esign:sign', session_id=session.id)
    else:
        # Log failed attempt
        AuditEvent.objects.create(
            session=session,
            event_type='otp_failed',
            payload={'input': '***'},
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        messages.error(request, 'Invalid or expired verification code.')
        return redirect('esign:verify_otp_page', session_id=session.id)


@require_http_methods(["POST"])
def resend_otp(request, session_id):
    """Resend OTP"""
    from .models import OTP, AuditEvent
    from .utils.email import send_otp_email
    from django.utils import timezone
    from datetime import timedelta
    import random
    import string
    from django.conf import settings
    
    session = get_object_or_404(SignSession, id=session_id)
    
    # Generate new OTP
    otp_code = ''.join(random.choices(string.digits, k=settings.ESIGN_OTP_LENGTH))
    OTP.objects.create(
        session=session,
        otp_hash=otp_code,
        expires_at=timezone.now() + timedelta(minutes=settings.ESIGN_OTP_EXPIRY_MINUTES)
    )
    
    if send_otp_email(session, otp_code):
        messages.success(request, 'New verification code sent.')
    else:
        messages.error(request, 'Failed to send email.')
        
    return redirect('esign:verify_otp_page', session_id=session.id)


def sign_document(request, session_id):
    """Public signing page"""
    # For MVP, we assume logged in user is signing their own doc
    if not request.user.is_authenticated:
        return redirect('accounts:login')
        
    session = get_object_or_404(SignSession, id=session_id)
    
    # Check if user owns session
    if session.user != request.user:
        messages.error(request, "You don't have permission to view this session.")
        return redirect('dashboard:home')
        
    # Security check: Must be verified
    if session.status == 'created' or session.status == 'otp_sent':
        return redirect('esign:verify_otp_page', session_id=session.id)
        
    # Generate thumbnails if needed
    from .utils.pdf_processor import PDFProcessor
    from django.conf import settings
    import os
    
    thumbnails_dir = os.path.join(settings.MEDIA_ROOT, 'esign', 'thumbnails', str(session.id))
    # Use forward slashes for URLs
    thumbnails_url = f"{settings.MEDIA_URL}esign/thumbnails/{session.id}/"
    
    if not os.path.exists(thumbnails_dir):
        try:
            processor = PDFProcessor(file_path=session.original_pdf.path)
            thumbnails = processor.generate_thumbnails(thumbnails_dir)
            processor.close()
        except Exception as e:
            messages.error(request, f"Error processing PDF: {str(e)}")
            return redirect('dashboard:home')
    else:
        # List existing thumbnails
        thumbnails = sorted([f for f in os.listdir(thumbnails_dir) if f.endswith('.png')], 
                          key=lambda x: int(x.split('_')[1].split('.')[0]))

    # Prepare page data
    pages = []
    for i, thumb in enumerate(thumbnails):
        pages.append({
            'number': i + 1,
            'url': f"{thumbnails_url}{thumb}"
        })
        
    context = {
        'session': session,
        'pages': pages,
        'fonts': settings.ESIGN_SIGNATURE_FONTS,
    }
    return render(request, 'esign/sign.html', context)


@require_http_methods(["POST"])
def save_signature(request, session_id):
    """Save signature (draw/upload/type)"""
    import json
    from .utils.signature_renderer import SignatureRenderer
    from .models import Signature, SignSession, AuditEvent
    
    session = get_object_or_404(SignSession, id=session_id)
    
    try:
        # Check content type
        if request.content_type == 'application/json':
            data = json.loads(request.body)
            method = data.get('method')
            
            if method == 'draw':
                image = SignatureRenderer.render_drawn_signature(data.get('signature_data'))
            elif method == 'type':
                image = SignatureRenderer.render_typed_signature(
                    data.get('text'),
                    data.get('font')
                )
            else:
                return JsonResponse({'success': False, 'message': 'Invalid method'}, status=400)
                
        elif request.FILES.get('signature_file'):
            method = 'upload'
            image = SignatureRenderer.process_uploaded_signature(request.FILES['signature_file'])
            
        else:
            return JsonResponse({'success': False, 'message': 'No signature data'}, status=400)
            
        # Save signature object with unique filename
        import uuid
        filename = f'signature_{uuid.uuid4().hex[:8]}.png'
        signature_file = SignatureRenderer.save_signature_image(image, filename=filename)
        
        signature = Signature.objects.create(
            session=session,
            method=method,
            signature_image=signature_file,
            signer_name=request.user.get_full_name() or request.user.username,
            signer_email=request.user.email,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        # Audit event
        AuditEvent.objects.create(
            session=session,
            event_type='signature_added',
            payload={'method': method, 'signature_id': str(signature.id)}
        )
        
        return JsonResponse({
            'success': True, 
            'signature_id': str(signature.id),
            'signature_url': signature.signature_image.url
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@require_http_methods(["POST"])
def complete_signing(request, session_id):
    """Complete signing process and trigger PDF generation"""
    import json
    from .models import SignSession, SignatureField, Signature, AuditEvent
    from .tasks import process_signed_pdf
    from .utils.pdf_processor import PDFProcessor
    
    session = get_object_or_404(SignSession, id=session_id)
    
    try:
        data = json.loads(request.body)
        placements = data.get('placements', [])
        signature_id = data.get('signature_id') or (placements[0]['signature_id'] if placements else None)
        
        if not signature_id:
             return JsonResponse({'success': False, 'message': 'No signature provided'}, status=400)

        # If no placements provided, apply to ALL pages at bottom-right
        if not placements:
            try:
                processor = PDFProcessor(file_path=session.original_pdf.path)
                page_count = processor.get_page_count()
                
                master_signature = Signature.objects.get(id=signature_id, session=session)
                
                # Default dimensions for signature
                sig_width = 150
                sig_height = 50
                margin = 20
                
                for i in range(1, page_count + 1):
                    # Get page dimensions
                    page_w, page_h = processor.get_page_dimensions(i)
                    
                    # Calculate bottom-right position
                    # x = width - sig_width - margin
                    # y = height - sig_height - margin
                    x = page_w - sig_width - margin
                    y = page_h - sig_height - margin
                    
                    # Ensure coordinates are valid
                    x = max(0, x)
                    y = max(0, y)
                    
                    # Create field
                    field = SignatureField.objects.create(
                        session=session,
                        page_number=i,
                        x=x,
                        y=y,
                        width=sig_width,
                        height=sig_height,
                        name=f"Signature-Page{i}-Auto",
                        is_signed=True
                    )
                    
                    if i == 1:
                        # Use the master signature for the first page
                        master_signature.field = field
                        master_signature.save()
                    else:
                        # Clone signature for other pages
                        Signature.objects.create(
                            session=session,
                            field=field,
                            method=master_signature.method,
                            signature_image=master_signature.signature_image,
                            signer_name=master_signature.signer_name,
                            signer_email=master_signature.signer_email,
                            ip_address=master_signature.ip_address,
                            user_agent=master_signature.user_agent,
                            font_name=master_signature.font_name
                        )
                
                processor.close()
                
            except Exception as e:
                return JsonResponse({'success': False, 'message': f'Error auto-placing signatures: {str(e)}'}, status=500)
                
        else:
            # Manual placements - need to clone signature for each page
            master_signature = Signature.objects.get(id=signature_id, session=session)
            
            for idx, p in enumerate(placements):
                field = SignatureField.objects.create(
                    session=session,
                    page_number=p['page'],
                    x=p['x'],
                    y=p['y'],
                    width=p['width'],
                    height=p['height'],
                    name=f"Signature-{p['page']}-{p['x']}",
                    is_signed=True
                )
                
                if idx == 0:
                    # Use the master signature for the first placement
                    master_signature.field = field
                    master_signature.save()
                else:
                    # Clone signature for other pages
                    Signature.objects.create(
                        session=session,
                        field=field,
                        method=master_signature.method,
                        signature_image=master_signature.signature_image,
                        signer_name=master_signature.signer_name,
                        signer_email=master_signature.signer_email,
                        ip_address=master_signature.ip_address,
                        user_agent=master_signature.user_agent,
                        font_name=master_signature.font_name
                    )
            
        # Update session status
        session.status = 'signing'
        session.celery_task_id = ''  # Set to empty string to avoid NULL constraint
        session.save()
        
        # Trigger Celery task
        task = process_signed_pdf.delay(session.id)
        session.celery_task_id = task.id if hasattr(task, 'id') else ''
        session.save(update_fields=['celery_task_id'])
        
        # Send completion email
        from .utils.email import send_completion_email
        send_completion_email(session)
        
        return JsonResponse({'success': True, 'message': 'Signing completed'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


def download_signed_pdf(request, session_id):
    """Download signed PDF"""
    session = get_object_or_404(SignSession, id=session_id)
    
    # Check ownership
    if request.user.is_authenticated and session.user != request.user:
        messages.error(request, "You don't have permission to download this file.")
        return redirect('dashboard:home')
    
    # Check if signed PDF exists
    if not session.signed_pdf:
        messages.warning(request, "Signed PDF is not ready yet. Please wait a moment and try again.")
        return redirect('esign:status', session_id=session_id)
    
    # Serve the file
    try:
        response = FileResponse(session.signed_pdf.open('rb'), as_attachment=True, filename=f"signed_{session.original_filename}")
        return response
    except Exception as e:
        messages.error(request, f"Error downloading file: {str(e)}")
        return redirect('esign:status', session_id=session_id)


def status_page(request, session_id):
    """Status page showing signing progress and download link"""
    session = get_object_or_404(SignSession, id=session_id)
    
    # Check ownership
    if request.user.is_authenticated and session.user != request.user:
        messages.error(request, "You don't have permission to view this session.")
        return redirect('dashboard:home')
    
    context = {
        'session': session,
        'page_title': 'Document Status',
    }
    return render(request, 'esign/status.html', context)


def session_status(request, session_id):
    """Get session status (AJAX endpoint)"""
    session = get_object_or_404(SignSession, id=session_id)
    return JsonResponse({
        'session_id': str(session.id),
        'status': session.status,
        'signed_at': session.signed_at.isoformat() if session.signed_at else None,
    })

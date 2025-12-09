"""
Views for home page and user dashboard.
"""
import logging
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta

from apps.tools.models import Tool, ToolCategory, ConversionHistory
from apps.accounts.utils import get_remaining_conversions

logger = logging.getLogger('apps.dashboard')


def home_view(request):
    """
    Home page view with hero section, tool categories, and featured tools.
    Displays:
    - Hero section with search and CTA
    - Tool categories in grid layout
    - Featured/popular tools
    - How It Works section
    - Statistics
    """
    # Get all active categories
    categories = ToolCategory.objects.filter(
        is_active=True
    ).prefetch_related('tools').order_by('display_order')
    
    # Get featured tools (most popular by usage_count)
    featured_tools = Tool.objects.filter(
        is_active=True
    ).order_by('-usage_count')[:6]
    
    # Get statistics
    total_conversions = ConversionHistory.objects.filter(
        status='completed'
    ).count()
    
    total_users = None
    if request.user.is_authenticated:
        from apps.accounts.models import User
        total_users = User.objects.count()
    
    context = {
        'categories': categories,
        'featured_tools': featured_tools,
        'total_conversions': total_conversions,
        'total_users': total_users,
    }
    
    return render(request, 'dashboard/home.html', context)


@login_required
def dashboard_view(request):
    """
    User dashboard view with usage statistics and recent conversions.
    Displays:
    - Usage statistics and remaining credits
    - Recent conversion history
    - Quick access to favorite tools
    - Account information summary
    """
    user = request.user
    
    # Get usage statistics
    total_conversions = user.conversions.count()
    completed_conversions = user.conversions.filter(status='completed').count()
    failed_conversions = user.conversions.filter(status='failed').count()
    processing_conversions = user.conversions.filter(
        status__in=['pending', 'processing']
    ).count()
    
    # Calculate success rate
    if total_conversions > 0:
        success_rate = (completed_conversions / total_conversions) * 100
    else:
        success_rate = 0
    
    # Get remaining conversions
    from django.conf import settings
    remaining_conversions = get_remaining_conversions(user)
    daily_limit = 'Unlimited' if user.is_premium else settings.DAILY_CONVERSION_LIMIT_FREE
    
    # Get recent conversions (last 10)
    conversions = list(user.conversions.order_by('-created_at')[:10])
    
    # Get recent sign sessions
    from apps.esign.models import SignSession
    sign_sessions = user.sign_sessions.order_by('-created_at')[:10]
    
    # Adapt sign sessions to look like conversions
    adapted_sessions = []
    for session in sign_sessions:
        # Create a wrapper object or dict that mimics ConversionHistory
        class SignSessionAdapter:
            def __init__(self, session):
                self.id = session.id
                self.tool_type = 'esign'
                self.status = session.status
                self.created_at = session.created_at
                self.input_file = session.original_pdf
                self.output_file = session.signed_pdf
                self.original_session = session
                
            @property
            def get_tool_type_display(self):
                return "E-Sign PDF"
                
            @property
            def get_status_display(self):
                return self.original_session.get_status_display()
                
            # Helper for template logic that checks status == 'completed'
            @property
            def is_completed(self):
                return self.status == 'signed'
                
            # Helper for status badge class
            @property
            def status_class(self):
                if self.status == 'signed':
                    return 'completed'
                elif self.status in ['signing', 'otp_verified']:
                    return 'processing'
                elif self.status == 'failed':
                    return 'failed'
                else:
                    return 'pending'
            
            @property
            def is_esign(self):
                return True
                
        adapted_sessions.append(SignSessionAdapter(session))
    
    # Combine and sort
    from operator import attrgetter
    combined_history = sorted(
        conversions + adapted_sessions,
        key=attrgetter('created_at'),
        reverse=True
    )[:10]
    
    recent_conversions = combined_history
    
    # Get conversions from last 7 days for chart
    seven_days_ago = timezone.now() - timedelta(days=7)
    recent_activity = user.conversions.filter(
        created_at__gte=seven_days_ago
    ).values('created_at__date').annotate(
        count=Count('id')
    ).order_by('created_at__date')
    
    # Get most used tools
    most_used_tools = user.conversions.values(
        'tool_type'
    ).annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    
    # Get tool names for display
    tool_usage = []
    for item in most_used_tools:
        tool_type = item['tool_type']
        count = item['count']
        # Get display name from choices
        display_name = dict(ConversionHistory.TOOL_CHOICES).get(tool_type, tool_type)
        tool_usage.append({
            'tool_type': tool_type,
            'display_name': display_name,
            'count': count
        })
    
    context = {
        'total_conversions': total_conversions,
        'completed_conversions': completed_conversions,
        'failed_conversions': failed_conversions,
        'processing_conversions': processing_conversions,
        'success_rate': round(success_rate, 1),
        'remaining_conversions': remaining_conversions,
        'daily_limit': daily_limit,
        'daily_usage': user.daily_usage_count,
        'recent_conversions': recent_conversions,
        'recent_activity': recent_activity,
        'tool_usage': tool_usage,
        'is_premium': user.is_premium,
    }
    
    return render(request, 'dashboard/dashboard.html', context)


def search_tools_view(request):
    """
    Search tools by name, description, or category.
    """
    query = request.GET.get('q', '').strip()
    
    if query:
        tools = Tool.objects.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(category__name__icontains=query),
            is_active=True
        ).select_related('category').order_by('category__display_order', 'display_order')
    else:
        tools = Tool.objects.none()
    
    context = {
        'tools': tools,
        'query': query,
    }
    
    return render(request, 'dashboard/search_results.html', context)



def privacy_view(request):
    """
    Privacy Policy page view.
    """
    return render(request, 'privacy.html')


def terms_view(request):
    """
    Terms of Service page view.
    """
    return render(request, 'terms.html')



def about_view(request):
    """
    About Us page view.
    """
    return render(request, 'about.html')


def pricing_view(request):
    """
    Pricing page view.
    """
    return render(request, 'pricing.html')


@login_required
def upgrade_view(request):
    """
    Upgrade to Premium page view.
    """
    context = {
        'user': request.user,
    }
    return render(request, 'dashboard/upgrade.html', context)


@login_required
def checkout_view(request):
    """
    Checkout page for premium subscription.
    """
    from decimal import Decimal
    
    plan_price = Decimal('199.00')
    tax_rate = Decimal('18.00')
    
    # Calculate tax and total
    tax_amount = (plan_price * tax_rate / 100).quantize(Decimal('0.01'))
    total_amount = (plan_price + tax_amount).quantize(Decimal('0.01'))
    
    context = {
        'user': request.user,
        'plan_name': 'Premium',
        'plan_price': plan_price,
        'tax_rate': tax_rate,
        'tax_amount': tax_amount,
        'total_amount': total_amount,
        'plan_currency': 'INR',
    }
    return render(request, 'dashboard/checkout.html', context)


@login_required
def confirm_payment_view(request):
    """
    Handle payment confirmation and send notification emails.
    """
    from django.http import JsonResponse
    from django.core.mail import send_mail
    from django.conf import settings
    from apps.accounts.models import PaymentConfirmation
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)
    
    user = request.user
    plan_name = request.POST.get('plan_name', 'Premium')
    plan_price = request.POST.get('plan_price', '199')
    tax_rate = request.POST.get('tax_rate', '18')
    tax_amount = request.POST.get('tax_amount', '35.82')
    total_amount = request.POST.get('total_amount', '234.82')
    
    try:
        # Get client IP address
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0].strip()
        else:
            ip_address = request.META.get('REMOTE_ADDR')
        
        # Get user agent
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Create payment confirmation record
        payment_confirmation = PaymentConfirmation.objects.create(
            user=user,
            plan_name=plan_name,
            plan_price=plan_price,
            tax_rate=tax_rate,
            tax_amount=tax_amount,
            total_amount=total_amount,
            currency='INR',
            status='pending',
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        logger.info(f"Payment confirmation created: ID {payment_confirmation.id} for user {user.email}")
        
    except Exception as e:
        logger.error(f"Error creating payment confirmation: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'An error occurred while saving your confirmation. Please contact support.'
        }, status=500)
    
    try:
        # Generate verification URL using reverse
        from django.urls import reverse
        verification_path = reverse('dashboard:verify_payment', kwargs={
            'confirmation_id': payment_confirmation.id,
            'token': payment_confirmation.verification_token
        })
        verification_url = request.build_absolute_uri(verification_path)
        
        # Send email to admin
        admin_subject = f'Payment Confirmation Received - {user.email}'
        admin_message = f"""
Payment Confirmation Received

Confirmation ID: {payment_confirmation.id}

User Details:
- Email: {user.email}
- Name: {user.get_full_name() or user.username}
- User ID: {user.id}

Plan Details:
- Plan: {plan_name}
- Price: ₹{plan_price}

The user has indicated they have completed the payment. Please verify and activate their premium account.

🔗 ONE-CLICK VERIFICATION:
Click here to verify and activate: {verification_url}

Or manually verify in Django Admin:
Django Admin > Accounts > Payment Confirmations > ID #{payment_confirmation.id}

User's email for confirmation: {user.email}
"""
        
        send_mail(
            subject=admin_subject,
            message=admin_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.EMAIL_HOST_USER],
            fail_silently=False,
        )
        
        # Send confirmation email to user
        user_subject = 'Payment Confirmation Received - SmartToolPDF'
        user_message = f"""
Dear {user.get_full_name() or user.username},

Thank you for your payment confirmation!

We have received your notification that you have completed the payment for the {plan_name} plan (₹{plan_price}).

Our team will verify your payment and activate your premium account within 24 hours. You will receive a confirmation email once your account has been upgraded.

If you have any questions, please don't hesitate to contact us at {settings.EMAIL_HOST_USER}.

Thank you for choosing SmartToolPDF!

Best regards,
The SmartToolPDF Team
"""
        
        send_mail(
            subject=user_subject,
            message=user_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        
        logger.info(f"Payment confirmation emails sent for user {user.email}")
        
        return JsonResponse({
            'success': True,
            'message': f'Thank you! We will verify your payment and activate your premium account within 24 hours. You will receive a confirmation email at {user.email}'
        })
        
    except Exception as e:
        logger.error(f"Error sending payment confirmation emails: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'An error occurred while processing your confirmation. Please contact support.'
        }, status=500)


@login_required
def billing_view(request):
    """
    Billing and subscription management page.
    """
    from apps.accounts.models import Invoice, PaymentConfirmation
    
    user = request.user
    
    # Get usage statistics
    total_conversions = user.conversions.count()
    completed_conversions = user.conversions.filter(status='completed').count()
    
    # Get conversions this month
    from django.utils import timezone
    from datetime import timedelta
    
    start_of_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    conversions_this_month = user.conversions.filter(
        created_at__gte=start_of_month
    ).count()
    
    # Get invoices
    invoices = Invoice.objects.filter(user=user).order_by('-payment_date')
    
    # Get payment confirmations
    payment_confirmations = PaymentConfirmation.objects.filter(
        user=user
    ).order_by('-submitted_at')
    
    # Get active subscription details (most recent verified payment)
    active_payment = payment_confirmations.filter(status='verified').first()
    
    # Get most recent invoice
    latest_invoice = invoices.first()
    
    context = {
        'user': user,
        'total_conversions': total_conversions,
        'completed_conversions': completed_conversions,
        'conversions_this_month': conversions_this_month,
        'invoices': invoices,
        'payment_confirmations': payment_confirmations,
        'active_payment': active_payment,
        'latest_invoice': latest_invoice,
    }
    
    return render(request, 'dashboard/billing.html', context)


def contact_view(request):
    """
    Contact page view with form handling.
    """
    from django.contrib import messages
    
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        
        # TODO: Send email or save to database
        # For now, just show a success message
        logger.info(f"Contact form submission from {name} ({email}): {subject}")
        
        messages.success(
            request,
            'Thank you for contacting us! We will get back to you within 24 hours.'
        )
        
        # Redirect to avoid form resubmission
        from django.shortcuts import redirect
        return redirect('dashboard:contact')
    
    return render(request, 'contact.html')


def help_view(request):
    """
    Help Center page view.
    """
    return render(request, 'help.html')


def faq_view(request):
    """
    FAQ page view.
    """
    return render(request, 'faq.html')


def security_view(request):
    """
    Security page view.
    """
    return render(request, 'security.html')


@login_required
def download_invoice_view(request, invoice_id):
    """
    Download invoice as PDF.
    """
    from django.http import HttpResponse, Http404
    from apps.accounts.models import Invoice
    from apps.accounts.invoice_generator import generate_invoice_pdf
    
    try:
        if request.user.is_staff:
            invoice = Invoice.objects.get(id=invoice_id)
        else:
            invoice = Invoice.objects.get(id=invoice_id, user=request.user)
    except Invoice.DoesNotExist:
        raise Http404("Invoice not found")
    
    # Generate PDF
    pdf_buffer = generate_invoice_pdf(invoice)
    
    # Create response
    response = HttpResponse(pdf_buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Invoice-{invoice.invoice_number}.pdf"'
    
    return response


def verify_payment_view(request, confirmation_id, token):
    """
    One-click payment verification from email link.
    Verifies the payment confirmation and activates premium account.
    """
    from django.shortcuts import render, redirect
    from django.contrib import messages
    from apps.accounts.models import PaymentConfirmation
    
    try:
        payment_confirmation = PaymentConfirmation.objects.get(id=confirmation_id)
    except PaymentConfirmation.DoesNotExist:
        messages.error(request, 'Payment confirmation not found.')
        return render(request, 'dashboard/verification_error.html', {
            'error_message': 'Payment confirmation not found.',
            'error_details': 'The payment confirmation ID is invalid or does not exist.'
        })
    
    # Check if already verified
    if payment_confirmation.status == 'verified':
        messages.info(request, 'This payment has already been verified.')
        return render(request, 'dashboard/verification_already_done.html', {
            'payment_confirmation': payment_confirmation,
            'user': payment_confirmation.user,
        })
    
    # Validate token
    if payment_confirmation.verification_token != token:
        messages.error(request, 'Invalid verification token.')
        return render(request, 'dashboard/verification_error.html', {
            'error_message': 'Invalid verification token.',
            'error_details': 'The verification link is invalid or has been tampered with.'
        })
    
    # Check if token is expired or used
    if not payment_confirmation.is_token_valid():
        if payment_confirmation.token_used:
            error_details = 'This verification link has already been used.'
        else:
            error_details = 'This verification link has expired (valid for 7 days).'
        
        messages.error(request, 'Verification link is no longer valid.')
        return render(request, 'dashboard/verification_error.html', {
            'error_message': 'Verification link is no longer valid.',
            'error_details': error_details
        })
    
    # Mark token as used
    payment_confirmation.token_used = True
    payment_confirmation.save()
    
    # Verify payment and create invoice
    try:
        invoice = payment_confirmation.mark_as_verified(admin_user=request.user if request.user.is_authenticated else None)
        
        logger.info(f"Payment verified via email link: Confirmation ID {confirmation_id}, User {payment_confirmation.user.email}")
        
        messages.success(request, f'Payment verified successfully! Premium account activated for {payment_confirmation.user.email}')
        
        return render(request, 'dashboard/verification_success.html', {
            'payment_confirmation': payment_confirmation,
            'invoice': invoice,
            'user': payment_confirmation.user,
        })
        
    except Exception as e:
        logger.error(f"Error verifying payment {confirmation_id}: {str(e)}")
        messages.error(request, 'An error occurred while verifying the payment.')
        return render(request, 'dashboard/verification_error.html', {
            'error_message': 'An error occurred while verifying the payment.',
            'error_details': str(e)
        })

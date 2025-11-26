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
    recent_conversions = user.conversions.order_by('-created_at')[:10]
    
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
    context = {
        'user': request.user,
        'plan_name': 'Premium',
        'plan_price': '199',
        'plan_currency': 'INR',
    }
    return render(request, 'dashboard/checkout.html', context)


@login_required
def billing_view(request):
    """
    Billing and subscription management page.
    """
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
    
    context = {
        'user': user,
        'total_conversions': total_conversions,
        'completed_conversions': completed_conversions,
        'conversions_this_month': conversions_this_month,
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

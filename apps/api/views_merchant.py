"""
Views for merchant API key management and dashboard.
"""
from django.views.generic import ListView, CreateView, View, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.utils import timezone
from .models import APIMerchant, APIKey, APIUsageLog
from .utils import (
    generate_api_key,
    generate_api_secret,
    hash_api_credential,
    extract_key_prefix,
    format_api_key_for_display,
)
import logging

logger = logging.getLogger('apps.api')


class MerchantRequiredMixin(LoginRequiredMixin):
    """Mixin to ensure user has a merchant account."""
    
    def dispatch(self, request, *args, **kwargs):
        if not hasattr(request.user, 'api_merchant'):
            messages.error(request, 'You do not have an API merchant account.')
            return redirect('dashboard:home')
        return super().dispatch(request, *args, **kwargs)


class APIKeyListView(MerchantRequiredMixin, ListView):
    """
    View to list all API keys for the current merchant.
    """
    model = APIKey
    template_name = 'api/merchant/api_keys.html'
    context_object_name = 'api_keys'
    
    def get_queryset(self):
        """Get API keys for current merchant."""
        return APIKey.objects.filter(
            merchant=self.request.user.api_merchant
        ).order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        """Add additional context."""
        context = super().get_context_data(**kwargs)
        context['merchant'] = self.request.user.api_merchant
        context['page_title'] = 'API Keys'
        
        # Format keys for display
        context['formatted_keys'] = [
            format_api_key_for_display(key) for key in context['api_keys']
        ]
        
        return context


class APIKeyCreateView(MerchantRequiredMixin, View):
    """
    View to create a new API key.
    """
    
    def post(self, request):
        """Handle API key creation."""
        merchant = request.user.api_merchant
        
        # Get parameters from request
        key_name = request.POST.get('name', 'API Key')
        environment = request.POST.get('environment', 'production')
        
        # Validate environment
        if environment not in ['production', 'sandbox']:
            messages.error(request, 'Invalid environment specified.')
            return redirect('api:merchant_api_keys')
        
        # Check if merchant already has too many keys
        existing_keys = APIKey.objects.filter(merchant=merchant, is_active=True).count()
        if existing_keys >= 10:  # Limit to 10 active keys
            messages.error(
                request,
                'You have reached the maximum number of active API keys (10). '
                'Please revoke an existing key before creating a new one.'
            )
            return redirect('api:merchant_api_keys')
        
        try:
            # Generate credentials
            plain_key = generate_api_key(environment=environment)
            plain_secret = generate_api_secret()
            
            # Create API key
            api_key = APIKey.objects.create(
                merchant=merchant,
                name=key_name,
                environment=environment,
                key=hash_api_credential(plain_key),
                key_prefix=extract_key_prefix(plain_key),
                secret=hash_api_credential(plain_secret),
            )
            
            logger.info(
                f"Created new API key #{api_key.id} for merchant {merchant.company_name} "
                f"(environment: {environment})"
            )
            
            # Store credentials in session for one-time display
            request.session['new_api_key'] = {
                'id': api_key.id,
                'name': key_name,
                'key': plain_key,
                'secret': plain_secret,
                'environment': environment,
            }
            
            messages.success(
                request,
                f'API key "{key_name}" created successfully! '
                'Make sure to copy your credentials now - you won\'t be able to see them again.'
            )
            
        except Exception as e:
            logger.error(f"Failed to create API key for merchant {merchant.id}: {str(e)}")
            messages.error(request, f'Failed to create API key: {str(e)}')
        
        return redirect('api:merchant_api_keys')


class APIKeyRegenerateView(MerchantRequiredMixin, View):
    """
    View to regenerate an existing API key.
    """
    
    def post(self, request, key_id):
        """Handle API key regeneration."""
        merchant = request.user.api_merchant
        
        # Get the API key
        api_key = get_object_or_404(
            APIKey,
            id=key_id,
            merchant=merchant
        )
        
        try:
            # Generate new credentials
            plain_key = generate_api_key(environment=api_key.environment)
            plain_secret = generate_api_secret()
            
            # Update the key
            api_key.key = hash_api_credential(plain_key)
            api_key.key_prefix = extract_key_prefix(plain_key)
            api_key.secret = hash_api_credential(plain_secret)
            api_key.is_active = True
            api_key.revoked_at = None
            api_key.save()
            
            logger.info(
                f"Regenerated API key #{api_key.id} for merchant {merchant.company_name}"
            )
            
            # Store credentials in session for one-time display
            request.session['new_api_key'] = {
                'id': api_key.id,
                'name': api_key.name,
                'key': plain_key,
                'secret': plain_secret,
                'environment': api_key.environment,
                'regenerated': True,
            }
            
            messages.success(
                request,
                f'API key "{api_key.name}" regenerated successfully! '
                'Make sure to copy your new credentials now.'
            )
            
        except Exception as e:
            logger.error(f"Failed to regenerate API key {key_id}: {str(e)}")
            messages.error(request, f'Failed to regenerate API key: {str(e)}')
        
        return redirect('api:merchant_api_keys')


class APIKeyRevokeView(MerchantRequiredMixin, View):
    """
    View to revoke an API key.
    """
    
    def post(self, request, key_id):
        """Handle API key revocation."""
        merchant = request.user.api_merchant
        
        # Get the API key
        api_key = get_object_or_404(
            APIKey,
            id=key_id,
            merchant=merchant
        )
        
        try:
            # Revoke the key
            api_key.revoke()
            
            logger.info(
                f"Revoked API key #{api_key.id} ({api_key.name}) "
                f"for merchant {merchant.company_name}"
            )
            
            messages.success(
                request,
                f'API key "{api_key.name}" has been revoked successfully.'
            )
            
        except Exception as e:
            logger.error(f"Failed to revoke API key {key_id}: {str(e)}")
            messages.error(request, f'Failed to revoke API key: {str(e)}')
        
        return redirect('api:merchant_api_keys')


class APIKeyDeleteView(MerchantRequiredMixin, View):
    """
    View to permanently delete an API key.
    """
    
    def post(self, request, key_id):
        """Handle API key deletion."""
        merchant = request.user.api_merchant
        
        # Get the API key
        api_key = get_object_or_404(
            APIKey,
            id=key_id,
            merchant=merchant
        )
        
        key_name = api_key.name
        
        try:
            # Delete the key
            api_key.delete()
            
            logger.info(
                f"Deleted API key #{key_id} ({key_name}) "
                f"for merchant {merchant.company_name}"
            )
            
            messages.success(
                request,
                f'API key "{key_name}" has been permanently deleted.'
            )
            
        except Exception as e:
            logger.error(f"Failed to delete API key {key_id}: {str(e)}")
            messages.error(request, f'Failed to delete API key: {str(e)}')
        
        return redirect('api:merchant_api_keys')


class MerchantDashboardView(MerchantRequiredMixin, TemplateView):
    """
    Main dashboard for API merchants.
    """
    template_name = 'api/merchant/dashboard.html'
    
    def get_context_data(self, **kwargs):
        """Add merchant data to context."""
        context = super().get_context_data(**kwargs)
        merchant = self.request.user.api_merchant
        
        # Basic merchant info
        context['merchant'] = merchant
        context['page_title'] = 'Merchant Dashboard'
        
        # Usage statistics
        context['usage_percentage'] = merchant.get_usage_percentage()
        context['remaining_requests'] = max(
            0,
            merchant.monthly_request_limit - merchant.current_month_usage
        )
        
        # API keys summary
        context['total_keys'] = APIKey.objects.filter(merchant=merchant).count()
        context['active_keys'] = APIKey.objects.filter(
            merchant=merchant,
            is_active=True
        ).count()
        
        # Recent API usage
        context['recent_usage'] = APIUsageLog.objects.filter(
            merchant=merchant
        ).order_by('-created_at')[:10]
        
        # Usage by status code
        from django.db.models import Count
        context['usage_by_status'] = APIUsageLog.objects.filter(
            merchant=merchant
        ).values('status_code').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        
        return context


class MerchantUsageView(MerchantRequiredMixin, ListView):
    """
    Detailed usage statistics and logs for merchant.
    """
    model = APIUsageLog
    template_name = 'api/merchant/usage.html'
    context_object_name = 'usage_logs'
    paginate_by = 50
    
    def get_queryset(self):
        """Get usage logs for current merchant."""
        queryset = APIUsageLog.objects.filter(
            merchant=self.request.user.api_merchant
        ).select_related('api_key', 'conversion').order_by('-created_at')
        
        # Filter by date range if provided
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
        
        # Filter by status code if provided
        status_code = self.request.GET.get('status_code')
        if status_code:
            queryset = queryset.filter(status_code=status_code)
        
        # Filter by endpoint if provided
        endpoint = self.request.GET.get('endpoint')
        if endpoint:
            queryset = queryset.filter(endpoint__icontains=endpoint)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        """Add additional context."""
        context = super().get_context_data(**kwargs)
        context['merchant'] = self.request.user.api_merchant
        context['page_title'] = 'API Usage'
        
        # Summary statistics
        from django.db.models import Count, Avg, Sum
        merchant = self.request.user.api_merchant
        
        stats = APIUsageLog.objects.filter(merchant=merchant).aggregate(
            total_requests=Count('id'),
            avg_response_time=Avg('response_time'),
            total_data_transferred=Sum('response_size'),
        )
        
        context['stats'] = stats
        
        return context


class APIKeyCredentialsView(MerchantRequiredMixin, TemplateView):
    """
    Display newly created API key credentials (one-time view).
    """
    template_name = 'api/merchant/api_key_credentials.html'
    
    def get_context_data(self, **kwargs):
        """Get credentials from session."""
        context = super().get_context_data(**kwargs)
        
        # Get credentials from session
        credentials = self.request.session.pop('new_api_key', None)
        
        if not credentials:
            messages.warning(
                self.request,
                'No new API key credentials to display.'
            )
            return redirect('api:merchant_api_keys')
        
        context['credentials'] = credentials
        context['page_title'] = 'API Key Credentials'
        
        return context



class WebhookConfigurationView(MerchantRequiredMixin, TemplateView):
    """
    View for configuring webhooks.
    """
    template_name = 'api/merchant/webhooks.html'
    
    def get_context_data(self, **kwargs):
        """Add webhook configuration to context."""
        context = super().get_context_data(**kwargs)
        merchant = self.request.user.api_merchant
        
        context['merchant'] = merchant
        context['page_title'] = 'Webhook Configuration'
        
        # Get recent webhook deliveries
        from .models import WebhookDelivery
        context['recent_webhooks'] = WebhookDelivery.objects.filter(
            merchant=merchant
        ).order_by('-created_at')[:20]
        
        return context


class WebhookUpdateView(MerchantRequiredMixin, View):
    """
    View to update webhook configuration.
    """
    
    def post(self, request):
        """Handle webhook configuration update."""
        merchant = request.user.api_merchant
        
        webhook_url = request.POST.get('webhook_url', '').strip()
        webhook_enabled = request.POST.get('webhook_enabled') == 'on'
        
        try:
            # Update webhook configuration
            merchant.webhook_url = webhook_url if webhook_url else None
            merchant.webhook_enabled = webhook_enabled and bool(webhook_url)
            
            # Generate new secret if URL changed
            if webhook_url and webhook_url != merchant.webhook_url:
                merchant.generate_webhook_secret()
            
            merchant.save()
            
            logger.info(
                f"Updated webhook configuration for {merchant.company_name}: "
                f"enabled={merchant.webhook_enabled}, url={merchant.webhook_url}"
            )
            
            messages.success(
                request,
                'Webhook configuration updated successfully.'
            )
            
        except Exception as e:
            logger.error(f"Failed to update webhook configuration: {str(e)}")
            messages.error(request, f'Failed to update webhook configuration: {str(e)}')
        
        return redirect('api:merchant_webhooks')


class WebhookTestView(MerchantRequiredMixin, View):
    """
    View to test webhook delivery.
    """
    
    def post(self, request):
        """Send test webhook."""
        merchant = request.user.api_merchant
        
        if not merchant.webhook_url:
            messages.error(request, 'Please configure a webhook URL first.')
            return redirect('api:merchant_webhooks')
        
        try:
            from .webhooks import test_webhook
            
            result = test_webhook(merchant)
            
            if result['success']:
                messages.success(
                    request,
                    f"Test webhook delivered successfully! "
                    f"Status: {result['status_code']}"
                )
            else:
                messages.error(
                    request,
                    f"Test webhook failed: {result['error']}"
                )
            
            logger.info(f"Test webhook for {merchant.company_name}: {result}")
            
        except Exception as e:
            logger.error(f"Failed to send test webhook: {str(e)}")
            messages.error(request, f'Failed to send test webhook: {str(e)}')
        
        return redirect('api:merchant_webhooks')



class APIKeyIPWhitelistView(MerchantRequiredMixin, View):
    """
    View to manage IP whitelist for an API key.
    """
    
    def get(self, request, key_id):
        """Display IP whitelist management page."""
        from django.shortcuts import render
        
        merchant = request.user.api_merchant
        api_key = get_object_or_404(APIKey, id=key_id, merchant=merchant)
        
        from .ip_whitelist import get_whitelist_info, get_client_ip_info
        
        whitelist_info = get_whitelist_info(api_key)
        client_ip_info = get_client_ip_info(request)
        
        context = {
            'api_key': api_key,
            'whitelist_info': whitelist_info,
            'client_ip_info': client_ip_info,
            'page_title': f'IP Whitelist - {api_key.name}',
        }
        
        return render(request, 'api/merchant/ip_whitelist.html', context)
    
    def post(self, request, key_id):
        """Handle IP whitelist modifications."""
        from .ip_whitelist import (
            add_ip_to_whitelist,
            remove_ip_from_whitelist,
            clear_whitelist,
            validate_whitelist_format
        )
        
        merchant = request.user.api_merchant
        api_key = get_object_or_404(APIKey, id=key_id, merchant=merchant)
        
        action = request.POST.get('action')
        
        if action == 'add':
            ip_address = request.POST.get('ip_address', '').strip()
            
            if not ip_address:
                messages.error(request, 'Please provide an IP address.')
                return redirect('api:api_key_ip_whitelist', key_id=key_id)
            
            success, message = add_ip_to_whitelist(api_key, ip_address)
            
            if success:
                messages.success(request, message)
            else:
                messages.error(request, message)
        
        elif action == 'remove':
            ip_address = request.POST.get('ip_address', '').strip()
            
            if not ip_address:
                messages.error(request, 'Please provide an IP address to remove.')
                return redirect('api:api_key_ip_whitelist', key_id=key_id)
            
            success, message = remove_ip_from_whitelist(api_key, ip_address)
            
            if success:
                messages.success(request, message)
            else:
                messages.error(request, message)
        
        elif action == 'clear':
            success, message = clear_whitelist(api_key)
            messages.warning(request, message)
        
        elif action == 'bulk_add':
            ip_list_text = request.POST.get('ip_list', '').strip()
            
            if not ip_list_text:
                messages.error(request, 'Please provide a list of IP addresses.')
                return redirect('api:api_key_ip_whitelist', key_id=key_id)
            
            # Split by newlines and commas
            ip_list = []
            for line in ip_list_text.split('\n'):
                for ip in line.split(','):
                    ip = ip.strip()
                    if ip:
                        ip_list.append(ip)
            
            # Validate all IPs first
            is_valid, errors, normalized = validate_whitelist_format(ip_list)
            
            if not is_valid:
                messages.error(
                    request,
                    f'Invalid IP addresses found: {", ".join(errors)}'
                )
                return redirect('api:api_key_ip_whitelist', key_id=key_id)
            
            # Add all valid IPs
            added_count = 0
            for ip in normalized:
                success, message = add_ip_to_whitelist(api_key, ip)
                if success:
                    added_count += 1
            
            messages.success(
                request,
                f'{added_count} IP address(es) added to whitelist.'
            )
        
        else:
            messages.error(request, 'Invalid action.')
        
        return redirect('api:api_key_ip_whitelist', key_id=key_id)


class APIKeyIPWhitelistAPIView(MerchantRequiredMixin, View):
    """
    JSON API endpoint for IP whitelist management.
    """
    
    def get(self, request, key_id):
        """Get current whitelist."""
        from .ip_whitelist import get_whitelist_info
        
        merchant = request.user.api_merchant
        api_key = get_object_or_404(APIKey, id=key_id, merchant=merchant)
        
        whitelist_info = get_whitelist_info(api_key)
        
        return JsonResponse({
            'success': True,
            'data': whitelist_info
        })
    
    def post(self, request, key_id):
        """Add IP to whitelist via JSON API."""
        import json
        from .ip_whitelist import add_ip_to_whitelist
        
        merchant = request.user.api_merchant
        api_key = get_object_or_404(APIKey, id=key_id, merchant=merchant)
        
        try:
            data = json.loads(request.body)
            ip_address = data.get('ip_address', '').strip()
            
            if not ip_address:
                return JsonResponse({
                    'success': False,
                    'message': 'IP address is required'
                }, status=400)
            
            success, message = add_ip_to_whitelist(api_key, ip_address)
            
            return JsonResponse({
                'success': success,
                'message': message
            }, status=200 if success else 400)
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'message': 'Invalid JSON'
            }, status=400)
    
    def delete(self, request, key_id):
        """Remove IP from whitelist via JSON API."""
        import json
        from .ip_whitelist import remove_ip_from_whitelist
        
        merchant = request.user.api_merchant
        api_key = get_object_or_404(APIKey, id=key_id, merchant=merchant)
        
        try:
            data = json.loads(request.body)
            ip_address = data.get('ip_address', '').strip()
            
            if not ip_address:
                return JsonResponse({
                    'success': False,
                    'message': 'IP address is required'
                }, status=400)
            
            success, message = remove_ip_from_whitelist(api_key, ip_address)
            
            return JsonResponse({
                'success': success,
                'message': message
            }, status=200 if success else 400)
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'message': 'Invalid JSON'
            }, status=400)

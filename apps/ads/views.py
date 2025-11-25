"""
Views for advertisement tracking and display.
"""
import logging
from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from .models import Advertisement

logger = logging.getLogger('apps.ads')


@require_POST
@csrf_exempt
def track_impression(request, ad_id):
    """
    AJAX endpoint to track ad impressions.
    
    Args:
        ad_id: Advertisement ID
        
    Returns:
        JsonResponse with success status
    """
    try:
        ad = get_object_or_404(Advertisement, id=ad_id, is_active=True)
        ad.increment_impression()
        
        logger.debug(f"Impression tracked for ad: {ad.title} (ID: {ad_id})")
        
        return JsonResponse({
            'success': True,
            'impression_count': ad.impression_count
        })
    except Exception as e:
        logger.error(f"Error tracking impression for ad {ad_id}: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


def track_click(request, ad_id):
    """
    Track ad click and redirect to target URL.
    
    Args:
        ad_id: Advertisement ID
        
    Returns:
        Redirect to advertisement link URL
    """
    try:
        ad = get_object_or_404(Advertisement, id=ad_id, is_active=True)
        ad.increment_click()
        
        logger.info(
            f"Click tracked for ad: {ad.title} (ID: {ad_id}) - "
            f"Redirecting to: {ad.link_url}"
        )
        
        return redirect(ad.link_url)
    except Exception as e:
        logger.error(f"Error tracking click for ad {ad_id}: {str(e)}")
        # Redirect to home page on error
        return redirect('/')

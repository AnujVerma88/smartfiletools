"""
Subscription Plan Management.
Handles plan upgrades, downgrades, and billing calculations.
"""
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from .models import APIMerchant
from .emails import send_plan_change_confirmation
import logging

logger = logging.getLogger('apps.api')


# Plan pricing (monthly)
PLAN_PRICING = {
    'free': Decimal('0.00'),
    'starter': Decimal('29.00'),
    'professional': Decimal('199.00'),
    'enterprise': Decimal('999.00'),  # Base price, actual is custom
}

# Plan limits
PLAN_LIMITS = {
    'free': {
        'monthly_requests': 1000,
        'per_minute': 10,
        'max_file_size_mb': 10,
    },
    'starter': {
        'monthly_requests': 10000,
        'per_minute': 50,
        'max_file_size_mb': 50,
    },
    'professional': {
        'monthly_requests': 100000,
        'per_minute': 200,
        'max_file_size_mb': 100,
    },
    'enterprise': {
        'monthly_requests': None,  # Unlimited
        'per_minute': 1000,
        'max_file_size_mb': 500,
    },
}


def get_plan_info(plan_name):
    """
    Get plan information including pricing and limits.
    
    Args:
        plan_name: str - Plan name (free, starter, professional, enterprise)
    
    Returns:
        dict: Plan information
    """
    return {
        'name': plan_name,
        'price': PLAN_PRICING.get(plan_name, Decimal('0.00')),
        'limits': PLAN_LIMITS.get(plan_name, PLAN_LIMITS['free']),
    }


def calculate_prorated_amount(merchant, new_plan, billing_cycle='monthly'):
    """
    Calculate prorated amount for plan change.
    
    Args:
        merchant: APIMerchant instance
        new_plan: str - New plan name
        billing_cycle: str - 'monthly' or 'annual'
    
    Returns:
        dict: Prorated billing information
    """
    current_plan = merchant.plan
    current_price = PLAN_PRICING[current_plan]
    new_price = PLAN_PRICING[new_plan]
    
    # Get next billing date
    next_billing = merchant.next_billing_date
    if not next_billing:
        # If no billing date set, use end of current month
        now = timezone.now()
        if now.month == 12:
            next_billing = now.replace(year=now.year + 1, month=1, day=1).date()
        else:
            next_billing = now.replace(month=now.month + 1, day=1).date()
    
    # Calculate days remaining in billing period
    today = timezone.now().date()
    days_remaining = (next_billing - today).days
    days_in_month = 30  # Simplified
    
    # Calculate prorated amounts
    if new_price > current_price:
        # Upgrade: charge difference prorated
        price_difference = new_price - current_price
        prorated_charge = (price_difference / days_in_month) * days_remaining
        credit = Decimal('0.00')
    else:
        # Downgrade: credit difference prorated
        price_difference = current_price - new_price
        prorated_charge = Decimal('0.00')
        credit = (price_difference / days_in_month) * days_remaining
    
    return {
        'current_plan': current_plan,
        'new_plan': new_plan,
        'current_price': float(current_price),
        'new_price': float(new_price),
        'days_remaining': days_remaining,
        'prorated_charge': float(prorated_charge.quantize(Decimal('0.01'))),
        'credit': float(credit.quantize(Decimal('0.01'))),
        'next_billing_date': next_billing.isoformat(),
        'billing_cycle': billing_cycle,
    }


def change_plan(merchant, new_plan, billing_cycle='monthly'):
    """
    Change merchant's subscription plan.
    
    Args:
        merchant: APIMerchant instance
        new_plan: str - New plan name
        billing_cycle: str - 'monthly' or 'annual'
    
    Returns:
        dict: Result with success status and details
    """
    if new_plan not in PLAN_PRICING:
        return {
            'success': False,
            'error': f'Invalid plan: {new_plan}',
        }
    
    if merchant.plan == new_plan:
        return {
            'success': False,
            'error': 'Already on this plan',
        }
    
    try:
        # Calculate prorated billing
        billing_info = calculate_prorated_amount(merchant, new_plan, billing_cycle)
        
        # Store old plan for logging
        old_plan = merchant.plan
        
        # Update merchant plan
        merchant.plan = new_plan
        merchant.billing_cycle = billing_cycle
        
        # Update usage limits
        limits = PLAN_LIMITS[new_plan]
        merchant.monthly_request_limit = limits['monthly_requests'] or 999999999
        
        # Set next billing date if not set
        if not merchant.next_billing_date:
            now = timezone.now()
            if billing_cycle == 'monthly':
                if now.month == 12:
                    merchant.next_billing_date = now.replace(year=now.year + 1, month=1, day=1).date()
                else:
                    merchant.next_billing_date = now.replace(month=now.month + 1, day=1).date()
            else:  # annual
                merchant.next_billing_date = now.replace(year=now.year + 1).date()
        
        merchant.save()
        
        logger.info(
            f"Plan changed for {merchant.company_name}: {old_plan} -> {new_plan} "
            f"(charge: ${billing_info['prorated_charge']}, credit: ${billing_info['credit']})"
        )
        
        # Send confirmation email
        try:
            send_plan_change_confirmation(merchant, old_plan, new_plan, billing_info)
        except Exception as e:
            logger.error(f"Failed to send plan change email: {str(e)}")
        
        return {
            'success': True,
            'message': f'Plan changed from {old_plan} to {new_plan}',
            'billing_info': billing_info,
        }
        
    except Exception as e:
        logger.error(f"Failed to change plan for merchant {merchant.id}: {str(e)}")
        return {
            'success': False,
            'error': str(e),
        }


def upgrade_plan(merchant, new_plan):
    """
    Upgrade merchant to a higher plan.
    
    Args:
        merchant: APIMerchant instance
        new_plan: str - New plan name
    
    Returns:
        dict: Result with success status and details
    """
    plan_order = ['free', 'starter', 'professional', 'enterprise']
    
    current_index = plan_order.index(merchant.plan)
    new_index = plan_order.index(new_plan)
    
    if new_index <= current_index:
        return {
            'success': False,
            'error': 'New plan must be higher than current plan',
        }
    
    return change_plan(merchant, new_plan, merchant.billing_cycle)


def downgrade_plan(merchant, new_plan):
    """
    Downgrade merchant to a lower plan.
    
    Args:
        merchant: APIMerchant instance
        new_plan: str - New plan name
    
    Returns:
        dict: Result with success status and details
    """
    plan_order = ['free', 'starter', 'professional', 'enterprise']
    
    current_index = plan_order.index(merchant.plan)
    new_index = plan_order.index(new_plan)
    
    if new_index >= current_index:
        return {
            'success': False,
            'error': 'New plan must be lower than current plan',
        }
    
    return change_plan(merchant, new_plan, merchant.billing_cycle)


def get_available_plans(merchant):
    """
    Get list of available plans for merchant.
    
    Args:
        merchant: APIMerchant instance
    
    Returns:
        list: Available plans with details
    """
    current_plan = merchant.plan
    plans = []
    
    for plan_name, price in PLAN_PRICING.items():
        limits = PLAN_LIMITS[plan_name]
        
        plans.append({
            'name': plan_name,
            'display_name': plan_name.title(),
            'price': float(price),
            'limits': {
                'monthly_requests': limits['monthly_requests'],
                'per_minute': limits['per_minute'],
                'max_file_size_mb': limits['max_file_size_mb'],
            },
            'is_current': plan_name == current_plan,
            'can_upgrade': plan_name != current_plan,
        })
    
    return plans

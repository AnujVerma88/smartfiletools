import os
import django
import sys

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smartfiletools.settings')
django.setup()

from apps.api.models import APIMerchant, APIKey

def show_merchant_details():
    try:
        merchant = APIMerchant.objects.get(company_name="Sample Merchant Co")
        print("\n" + "="*60)
        print("SAMPLE MERCHANT DETAILS")
        print("="*60)
        print(f"Company:          {merchant.company_name}")
        print(f"Email:            {merchant.contact_email}")
        print(f"Plan:             {merchant.get_plan_display()}")
        print(f"Monthly Limit:    {merchant.monthly_request_limit} requests")
        print(f"Webhook URL:      {merchant.webhook_url}")
        print(f"Webhook Enabled:  {merchant.webhook_enabled}")
        print(f"Webhook Secret:   {merchant.webhook_secret}")
        print("="*60)
        
        # Show API Keys
        api_keys = APIKey.objects.filter(merchant=merchant, is_active=True)
        if api_keys.exists():
            print("\nACTIVE API KEYS:")
            print("-"*60)
            for key in api_keys:
                print(f"Name:        {key.name}")
                print(f"Environment: {key.environment}")
                print(f"Key Prefix:  {key.key_prefix}...")
                print(f"Created:     {key.created_at}")
                print("-"*60)
        else:
            print("\nNo active API keys found.")
            print("Run setup_sample_merchant.py to generate credentials.")
        
        print("\n⚠️  IMPORTANT:")
        print("The full API Key and Secret are only shown once during creation.")
        print("If you need new credentials, delete the existing key and run")
        print("setup_sample_merchant.py again.")
        print("="*60 + "\n")
        
    except APIMerchant.DoesNotExist:
        print("\n❌ Sample merchant not found!")
        print("Run: python setup_sample_merchant.py")
        print()

if __name__ == "__main__":
    show_merchant_details()

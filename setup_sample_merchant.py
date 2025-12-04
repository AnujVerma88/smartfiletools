import os
import django
import sys

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smartfiletools.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.api.models import APIMerchant, APIKey
from apps.api.utils import generate_api_key, generate_api_secret, hash_api_credential, extract_key_prefix

User = get_user_model()

def create_sample_merchant():
    username = "sample_merchant"
    email = "merchant@example.com"
    password = "password123"
    webhook_url = "http://127.0.0.1:8080/merchantesign/getpdfbase64file"

    # 1. Create User
    user, created = User.objects.get_or_create(username=username, email=email)
    if created:
        user.set_password(password)
        user.save()
        print(f"Created user: {username}")
    else:
        print(f"User {username} already exists")

    # 2. Create Merchant
    merchant, created = APIMerchant.objects.get_or_create(user=user)
    merchant.company_name = "Sample Merchant Co"
    merchant.contact_email = email
    merchant.plan = "professional"
    merchant.monthly_request_limit = 1000
    
    # Configure Webhook
    merchant.webhook_url = webhook_url
    merchant.webhook_enabled = True
    if not merchant.webhook_secret:
        merchant.generate_webhook_secret()
    
    merchant.save()
    print(f"Configured merchant: {merchant.company_name}")
    print(f"Webhook URL: {merchant.webhook_url}")
    print(f"Webhook Secret: {merchant.webhook_secret}")

    # 3. Create API Key
    # We need to generate plain credentials to show the user
    plain_key = generate_api_key(environment='sandbox')
    plain_secret = generate_api_secret()

    api_key = APIKey.objects.create(
        merchant=merchant,
        name="Sample Integration Key",
        environment="sandbox",
        key=hash_api_credential(plain_key),
        key_prefix=extract_key_prefix(plain_key),
        secret=hash_api_credential(plain_secret),
        is_active=True
    )

    print("\n" + "="*50)
    print("MERCHANT CREDENTIALS GENERATED")
    print("="*50)
    print(f"API Key:    {plain_key}")
    print(f"API Secret: {plain_secret}")
    print("="*50)

if __name__ == "__main__":
    create_sample_merchant()

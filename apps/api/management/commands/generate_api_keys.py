"""
Management command to generate API keys for existing merchants.
Useful for bulk key generation or regeneration.

Usage:
    python manage.py generate_api_keys
    python manage.py generate_api_keys --merchant-id 123
    python manage.py generate_api_keys --all
"""
from django.core.management.base import BaseCommand
from apps.api.models import APIMerchant, APIKey
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Generate API keys for merchants'

    def add_arguments(self, parser):
        parser.add_argument(
            '--merchant-id',
            type=int,
            help='Generate key for specific merchant ID',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Generate keys for all merchants without active keys',
        )
        parser.add_argument(
            '--environment',
            type=str,
            choices=['production', 'sandbox'],
            default='production',
            help='Environment for the API key (default: production)',
        )
        parser.add_argument(
            '--name',
            type=str,
            default='Primary API Key',
            help='Name for the API key (default: Primary API Key)',
        )

    def handle(self, *args, **options):
        merchant_id = options['merchant_id']
        generate_all = options['all']
        environment = options['environment']
        key_name = options['name']

        self.stdout.write(self.style.SUCCESS('Generating API keys...'))

        if merchant_id:
            # Generate for specific merchant
            self.generate_for_merchant(merchant_id, environment, key_name)
        elif generate_all:
            # Generate for all merchants without keys
            self.generate_for_all_merchants(environment, key_name)
        else:
            self.stdout.write(
                self.style.ERROR(
                    'Please specify --merchant-id or --all'
                )
            )
            return

        self.stdout.write(self.style.SUCCESS('\n✓ API key generation completed!'))

    def generate_for_merchant(self, merchant_id, environment, key_name):
        """Generate API key for a specific merchant."""
        try:
            merchant = APIMerchant.objects.get(id=merchant_id)
        except APIMerchant.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Merchant with ID {merchant_id} not found')
            )
            return

        self.stdout.write(f'\nGenerating key for: {merchant.company_name}')

        # Check if merchant already has an active key
        existing_keys = APIKey.objects.filter(
            merchant=merchant,
            environment=environment,
            is_active=True
        ).count()

        if existing_keys > 0:
            self.stdout.write(
                self.style.WARNING(
                    f'  Merchant already has {existing_keys} active {environment} key(s)'
                )
            )
            
            # Ask for confirmation (in non-interactive mode, skip)
            if not self.confirm('  Generate another key anyway?'):
                return

        # Create API key
        api_key = APIKey.objects.create(
            merchant=merchant,
            name=key_name,
            environment=environment,
        )

        # Generate key pair
        plain_key, plain_secret = api_key.generate_key_pair()
        api_key.save()

        # Display credentials (ONLY TIME THEY'RE SHOWN)
        self.stdout.write(self.style.SUCCESS('\n  ✓ API Key generated successfully!'))
        self.stdout.write('\n  ' + '=' * 60)
        self.stdout.write(self.style.WARNING('  IMPORTANT: Save these credentials now!'))
        self.stdout.write(self.style.WARNING('  They will not be shown again!'))
        self.stdout.write('  ' + '=' * 60)
        self.stdout.write(f'\n  Merchant: {merchant.company_name}')
        self.stdout.write(f'  Key Name: {api_key.name}')
        self.stdout.write(f'  Environment: {api_key.environment}')
        self.stdout.write(f'\n  API Key: {plain_key}')
        self.stdout.write(f'  API Secret: {plain_secret}')
        self.stdout.write('\n  ' + '=' * 60 + '\n')

    def generate_for_all_merchants(self, environment, key_name):
        """Generate API keys for all merchants without active keys."""
        self.stdout.write(f'\nFinding merchants without {environment} keys...')

        # Get all active merchants
        all_merchants = APIMerchant.objects.filter(is_active=True)

        # Filter merchants without active keys in this environment
        merchants_without_keys = []
        for merchant in all_merchants:
            has_key = APIKey.objects.filter(
                merchant=merchant,
                environment=environment,
                is_active=True
            ).exists()
            
            if not has_key:
                merchants_without_keys.append(merchant)

        if not merchants_without_keys:
            self.stdout.write(
                self.style.SUCCESS(
                    f'All active merchants already have {environment} keys'
                )
            )
            return

        self.stdout.write(
            f'Found {len(merchants_without_keys)} merchant(s) without {environment} keys'
        )

        # Confirm
        if not self.confirm(f'\nGenerate keys for {len(merchants_without_keys)} merchant(s)?'):
            return

        # Generate keys
        generated_count = 0
        for merchant in merchants_without_keys:
            try:
                api_key = APIKey.objects.create(
                    merchant=merchant,
                    name=key_name,
                    environment=environment,
                )

                plain_key, plain_secret = api_key.generate_key_pair()
                api_key.save()

                self.stdout.write(
                    self.style.SUCCESS(
                        f'  ✓ Generated key for: {merchant.company_name}'
                    )
                )
                self.stdout.write(f'    Key: {plain_key}')
                self.stdout.write(f'    Secret: {plain_secret}\n')

                generated_count += 1

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'  ✗ Failed to generate key for {merchant.company_name}: {str(e)}'
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nGenerated {generated_count} API key(s)'
            )
        )

    def confirm(self, question):
        """Ask for user confirmation."""
        try:
            response = input(f'{question} (y/N): ').lower().strip()
            return response in ['y', 'yes']
        except:
            # Non-interactive mode
            return False

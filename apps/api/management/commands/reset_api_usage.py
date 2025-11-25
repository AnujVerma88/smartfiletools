"""
Management command to reset monthly usage counters for API merchants.
Useful for manual resets or testing.

Usage:
    python manage.py reset_api_usage
    python manage.py reset_api_usage --merchant-id 123
    python manage.py reset_api_usage --all
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.api.models import APIMerchant
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Reset monthly usage counters for API merchants'

    def add_arguments(self, parser):
        parser.add_argument(
            '--merchant-id',
            type=int,
            help='Reset usage for specific merchant ID',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Reset usage for all active merchants',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without actually resetting',
        )

    def handle(self, *args, **options):
        merchant_id = options['merchant_id']
        reset_all = options['all']
        dry_run = options['dry_run']

        self.stdout.write(self.style.SUCCESS('Resetting API usage counters...'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))

        if merchant_id:
            # Reset for specific merchant
            self.reset_for_merchant(merchant_id, dry_run)
        elif reset_all:
            # Reset for all merchants
            self.reset_for_all_merchants(dry_run)
        else:
            self.stdout.write(
                self.style.ERROR(
                    'Please specify --merchant-id or --all'
                )
            )
            return

        self.stdout.write(self.style.SUCCESS('\n✓ Usage reset completed!'))

    def reset_for_merchant(self, merchant_id, dry_run):
        """Reset usage for a specific merchant."""
        try:
            merchant = APIMerchant.objects.get(id=merchant_id)
        except APIMerchant.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Merchant with ID {merchant_id} not found')
            )
            return

        self.stdout.write(f'\nMerchant: {merchant.company_name}')
        self.stdout.write(f'Current usage: {merchant.current_month_usage}')
        self.stdout.write(f'Monthly limit: {merchant.monthly_request_limit}')
        self.stdout.write(f'Usage percentage: {merchant.get_usage_percentage():.1f}%')

        if dry_run:
            self.stdout.write(
                self.style.WARNING('\n  [DRY RUN] Would reset usage to 0')
            )
        else:
            old_usage = merchant.current_month_usage
            merchant.reset_monthly_usage()
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n  ✓ Reset usage: {old_usage} → 0'
                )
            )

    def reset_for_all_merchants(self, dry_run):
        """Reset usage for all active merchants."""
        merchants = APIMerchant.objects.filter(is_active=True)

        if not merchants.exists():
            self.stdout.write(
                self.style.WARNING('No active merchants found')
            )
            return

        self.stdout.write(f'\nFound {merchants.count()} active merchant(s)')

        # Show summary
        total_usage = sum(m.current_month_usage for m in merchants)
        self.stdout.write(f'Total current usage: {total_usage} requests')

        if not dry_run:
            # Confirm
            try:
                response = input(f'\nReset usage for {merchants.count()} merchant(s)? (y/N): ')
                if response.lower().strip() not in ['y', 'yes']:
                    self.stdout.write('Cancelled')
                    return
            except:
                # Non-interactive mode
                pass

        # Reset each merchant
        reset_count = 0
        error_count = 0

        for merchant in merchants:
            try:
                old_usage = merchant.current_month_usage

                if dry_run:
                    self.stdout.write(
                        f'  [DRY RUN] {merchant.company_name}: {old_usage} → 0'
                    )
                else:
                    merchant.reset_monthly_usage()
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'  ✓ {merchant.company_name}: {old_usage} → 0'
                        )
                    )

                reset_count += 1

            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(
                        f'  ✗ Failed to reset {merchant.company_name}: {str(e)}'
                    )
                )

        # Summary
        self.stdout.write(f'\nReset {reset_count} merchant(s)')
        if error_count > 0:
            self.stdout.write(
                self.style.WARNING(f'Errors: {error_count}')
            )

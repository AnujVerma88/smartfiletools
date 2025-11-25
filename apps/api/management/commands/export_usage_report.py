"""
Management command to export usage reports for API merchants.
Generates CSV or JSON reports for billing and analytics.

Usage:
    python manage.py export_usage_report --merchant-id 123
    python manage.py export_usage_report --all --format csv
    python manage.py export_usage_report --all --format json --output reports/
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.api.models import APIMerchant, APIUsageLog
from apps.api.tasks import generate_monthly_usage_report
from pathlib import Path
import csv
import json
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Export usage reports for API merchants'

    def add_arguments(self, parser):
        parser.add_argument(
            '--merchant-id',
            type=int,
            help='Export report for specific merchant ID',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Export reports for all active merchants',
        )
        parser.add_argument(
            '--format',
            type=str,
            choices=['csv', 'json'],
            default='csv',
            help='Output format (default: csv)',
        )
        parser.add_argument(
            '--output',
            type=str,
            default='.',
            help='Output directory (default: current directory)',
        )
        parser.add_argument(
            '--month',
            type=str,
            help='Month to report (YYYY-MM format, default: current month)',
        )

    def handle(self, *args, **options):
        merchant_id = options['merchant_id']
        export_all = options['all']
        output_format = options['format']
        output_dir = Path(options['output'])
        month = options['month']

        self.stdout.write(self.style.SUCCESS('Exporting usage reports...'))

        # Create output directory if it doesn't exist
        output_dir.mkdir(parents=True, exist_ok=True)

        if merchant_id:
            # Export for specific merchant
            self.export_for_merchant(merchant_id, output_format, output_dir, month)
        elif export_all:
            # Export for all merchants
            self.export_for_all_merchants(output_format, output_dir, month)
        else:
            self.stdout.write(
                self.style.ERROR(
                    'Please specify --merchant-id or --all'
                )
            )
            return

        self.stdout.write(self.style.SUCCESS('\n✓ Export completed!'))

    def export_for_merchant(self, merchant_id, output_format, output_dir, month):
        """Export report for a specific merchant."""
        try:
            merchant = APIMerchant.objects.get(id=merchant_id)
        except APIMerchant.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Merchant with ID {merchant_id} not found')
            )
            return

        self.stdout.write(f'\nGenerating report for: {merchant.company_name}')

        # Generate report data
        report = generate_monthly_usage_report(merchant_id)

        if not report:
            self.stdout.write(
                self.style.ERROR('Failed to generate report')
            )
            return

        # Export to file
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        filename = f'usage_report_{merchant.id}_{timestamp}.{output_format}'
        filepath = output_dir / filename

        if output_format == 'csv':
            self.export_to_csv(report, filepath)
        else:
            self.export_to_json(report, filepath)

        self.stdout.write(
            self.style.SUCCESS(f'  ✓ Report saved to: {filepath}')
        )

    def export_for_all_merchants(self, output_format, output_dir, month):
        """Export reports for all active merchants."""
        merchants = APIMerchant.objects.filter(is_active=True)

        if not merchants.exists():
            self.stdout.write(
                self.style.WARNING('No active merchants found')
            )
            return

        self.stdout.write(f'\nExporting reports for {merchants.count()} merchant(s)...')

        exported_count = 0
        error_count = 0

        for merchant in merchants:
            try:
                # Generate report
                report = generate_monthly_usage_report(merchant.id)

                if not report:
                    raise Exception('Failed to generate report')

                # Export to file
                timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
                filename = f'usage_report_{merchant.id}_{timestamp}.{output_format}'
                filepath = output_dir / filename

                if output_format == 'csv':
                    self.export_to_csv(report, filepath)
                else:
                    self.export_to_json(report, filepath)

                self.stdout.write(
                    self.style.SUCCESS(
                        f'  ✓ {merchant.company_name}: {filepath.name}'
                    )
                )

                exported_count += 1

            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(
                        f'  ✗ Failed to export for {merchant.company_name}: {str(e)}'
                    )
                )

        # Summary
        self.stdout.write(f'\nExported {exported_count} report(s)')
        if error_count > 0:
            self.stdout.write(
                self.style.WARNING(f'Errors: {error_count}')
            )

    def export_to_csv(self, report, filepath):
        """Export report to CSV format."""
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)

            # Header
            writer.writerow(['Usage Report'])
            writer.writerow(['Merchant', report['merchant_name']])
            writer.writerow(['Plan', report['plan']])
            writer.writerow(['Period', f"{report['period_start']} to {report['period_end']}"])
            writer.writerow([])

            # Statistics
            writer.writerow(['Statistics'])
            writer.writerow(['Metric', 'Value'])
            stats = report['statistics']
            writer.writerow(['Total Requests', stats['total_requests']])
            writer.writerow(['Successful Requests', stats['successful_requests']])
            writer.writerow(['Failed Requests', stats['failed_requests']])
            writer.writerow(['Success Rate', f"{stats['success_rate']:.2f}%"])
            writer.writerow(['Avg Response Time', f"{stats['avg_response_time']:.3f}s"])
            writer.writerow(['Total Data Transferred', f"{stats['total_data_transferred']} bytes"])
            writer.writerow([])

            # Quota
            writer.writerow(['Quota'])
            writer.writerow(['Metric', 'Value'])
            quota = report['quota']
            writer.writerow(['Limit', quota['limit']])
            writer.writerow(['Used', quota['used']])
            writer.writerow(['Remaining', quota['remaining']])
            writer.writerow(['Usage Percentage', f"{quota['usage_percentage']:.2f}%"])
            writer.writerow([])

            # Daily usage
            writer.writerow(['Daily Usage'])
            writer.writerow(['Date', 'Requests', 'Successful', 'Failed'])
            for day in report['daily_usage']:
                writer.writerow([
                    day['date'],
                    day['requests'],
                    day['successful'],
                    day['failed']
                ])

    def export_to_json(self, report, filepath):
        """Export report to JSON format."""
        with open(filepath, 'w', encoding='utf-8') as jsonfile:
            json.dump(report, jsonfile, indent=2, ensure_ascii=False)

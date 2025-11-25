"""
Management command to retry pending conversions.
Useful when conversions get stuck due to Celery worker issues.
"""
from django.core.management.base import BaseCommand
from apps.tools.models import ConversionHistory
from apps.tools.tasks import process_conversion


class Command(BaseCommand):
    help = 'Retry all pending conversions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--conversion-id',
            type=int,
            help='Retry a specific conversion by ID',
        )

    def handle(self, *args, **options):
        conversion_id = options.get('conversion_id')

        if conversion_id:
            # Retry specific conversion
            try:
                conversion = ConversionHistory.objects.get(id=conversion_id)
                self.stdout.write(f'Retrying conversion {conversion_id}...')
                
                # Reset status
                conversion.status = 'pending'
                conversion.error_message = None
                conversion.save()
                
                # Trigger task
                task = process_conversion.delay(conversion_id)
                conversion.celery_task_id = task.id
                conversion.save()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Conversion {conversion_id} queued with task {task.id}'
                    )
                )
            except ConversionHistory.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'✗ Conversion {conversion_id} not found')
                )
        else:
            # Retry all pending conversions
            pending_conversions = ConversionHistory.objects.filter(
                status='pending'
            ).order_by('created_at')

            count = pending_conversions.count()
            
            if count == 0:
                self.stdout.write(
                    self.style.WARNING('No pending conversions found')
                )
                return

            self.stdout.write(f'Found {count} pending conversion(s)')

            for conversion in pending_conversions:
                try:
                    self.stdout.write(
                        f'Retrying conversion {conversion.id} '
                        f'({conversion.tool_type})...'
                    )
                    
                    # Reset status
                    conversion.status = 'pending'
                    conversion.error_message = None
                    conversion.save()
                    
                    # Trigger task
                    task = process_conversion.delay(conversion.id)
                    conversion.celery_task_id = task.id
                    conversion.save()
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'  ✓ Queued with task {task.id}'
                        )
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f'  ✗ Error: {str(e)}'
                        )
                    )

            self.stdout.write(
                self.style.SUCCESS(
                    f'\n✓ Completed retrying {count} conversion(s)'
                )
            )

"""
Management command for manual file cleanup.
Deletes old files from temp, uploads, and output directories.

Usage:
    python manage.py cleanup_files
    python manage.py cleanup_files --age 48  # Files older than 48 hours
    python manage.py cleanup_files --dry-run  # Preview without deleting
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Clean up old files from temp, uploads, and output directories'

    def add_arguments(self, parser):
        parser.add_argument(
            '--age',
            type=int,
            default=24,
            help='Delete files older than this many hours (default: 24)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview files to be deleted without actually deleting them',
        )
        parser.add_argument(
            '--directory',
            type=str,
            choices=['temp', 'uploads', 'output', 'all'],
            default='all',
            help='Specific directory to clean (default: all)',
        )

    def handle(self, *args, **options):
        age_hours = options['age']
        dry_run = options['dry_run']
        target_dir = options['directory']

        self.stdout.write(self.style.SUCCESS(f'Starting file cleanup...'))
        self.stdout.write(f'Age threshold: {age_hours} hours')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No files will be deleted'))

        cutoff_time = timezone.now() - timedelta(hours=age_hours)
        self.stdout.write(f'Deleting files older than: {cutoff_time}')

        # Determine directories to clean
        if target_dir == 'all':
            directories = [
                ('temp', Path(settings.MEDIA_ROOT) / 'temp'),
                ('uploads', Path(settings.MEDIA_ROOT) / 'uploads'),
                ('output', Path(settings.MEDIA_ROOT) / 'output'),
            ]
        else:
            directories = [
                (target_dir, Path(settings.MEDIA_ROOT) / target_dir)
            ]

        total_deleted = 0
        total_size = 0
        total_errors = 0

        for dir_name, directory in directories:
            if not directory.exists():
                self.stdout.write(
                    self.style.WARNING(f'  Directory does not exist: {directory}')
                )
                continue

            self.stdout.write(f'\nCleaning directory: {dir_name}/')
            deleted, size, errors = self.clean_directory(
                directory, cutoff_time, dry_run
            )
            
            total_deleted += deleted
            total_size += size
            total_errors += errors

        # Summary
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('Cleanup Summary:'))
        self.stdout.write(f'  Files deleted: {total_deleted}')
        self.stdout.write(f'  Space freed: {self.format_size(total_size)}')
        self.stdout.write(f'  Errors: {total_errors}')
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('\n  This was a DRY RUN - no files were actually deleted')
            )
        else:
            self.stdout.write(self.style.SUCCESS('\n✓ Cleanup completed successfully!'))

    def clean_directory(self, directory, cutoff_time, dry_run):
        """Clean a specific directory."""
        deleted_count = 0
        total_size = 0
        error_count = 0

        # Walk through directory recursively
        for file_path in directory.rglob('*'):
            if not file_path.is_file():
                continue

            try:
                # Check file modification time
                file_mtime = timezone.datetime.fromtimestamp(file_path.stat().st_mtime)
                file_mtime = timezone.make_aware(file_mtime)

                if file_mtime < cutoff_time:
                    file_size = file_path.stat().st_size
                    age = timezone.now() - file_mtime

                    if dry_run:
                        self.stdout.write(
                            f'  [DRY RUN] Would delete: {file_path.name} '
                            f'({self.format_size(file_size)}, {self.format_age(age)} old)'
                        )
                    else:
                        file_path.unlink()
                        self.stdout.write(
                            f'  ✓ Deleted: {file_path.name} '
                            f'({self.format_size(file_size)}, {self.format_age(age)} old)'
                        )

                    deleted_count += 1
                    total_size += file_size

            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f'  ✗ Error deleting {file_path.name}: {str(e)}')
                )

        return deleted_count, total_size, error_count

    def format_size(self, bytes):
        """Format file size for display."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes < 1024.0:
                return f'{bytes:.2f} {unit}'
            bytes /= 1024.0
        return f'{bytes:.2f} TB'

    def format_age(self, timedelta):
        """Format age for display."""
        total_seconds = int(timedelta.total_seconds())
        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60

        if days > 0:
            return f'{days}d {hours}h'
        elif hours > 0:
            return f'{hours}h {minutes}m'
        else:
            return f'{minutes}m'

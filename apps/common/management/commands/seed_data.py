"""
Management command to seed the database with initial data.
Creates default theme, tool categories, tools, and API subscription plans.

Usage:
    python manage.py seed_data
    python manage.py seed_data --clear  # Clear existing data first
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.common.models import SiteTheme
from apps.tools.models import ToolCategory, Tool
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Seed database with initial data (theme, categories, tools, API plans)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before seeding',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting database seeding...'))

        if options['clear']:
            self.clear_data()

        with transaction.atomic():
            self.create_default_theme()
            self.create_tool_categories()
            self.create_tools()

        self.stdout.write(self.style.SUCCESS('✓ Database seeding completed successfully!'))

    def clear_data(self):
        """Clear existing data."""
        self.stdout.write('Clearing existing data...')
        
        Tool.objects.all().delete()
        ToolCategory.objects.all().delete()
        SiteTheme.objects.filter(theme_name='Default Teal').delete()
        
        self.stdout.write(self.style.WARNING('  Existing data cleared'))

    def create_default_theme(self):
        """Create default teal theme."""
        self.stdout.write('Creating default theme...')
        
        theme, created = SiteTheme.objects.get_or_create(
            theme_name='Default Teal',
            defaults={
                'is_active': True,
                'primary_color': '#14B8A6',
                'primary_color_rgb': '20, 184, 166',
                'secondary_color': '#0F766E',
                'accent_color': '#5EEAD4',
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'  ✓ Created theme: {theme.theme_name}'))
        else:
            self.stdout.write(f'  - Theme already exists: {theme.theme_name}')

    def create_tool_categories(self):
        """Create tool categories."""
        self.stdout.write('Creating tool categories...')
        
        categories = [
            {
                'name': 'Convert',
                'slug': 'convert',
                'icon': 'fas fa-exchange-alt',
                'description': 'Convert files between different formats',
                'display_order': 1,
            },
            {
                'name': 'Compress',
                'slug': 'compress',
                'icon': 'fas fa-compress-alt',
                'description': 'Reduce file sizes without losing quality',
                'display_order': 2,
            },
            {
                'name': 'Edit',
                'slug': 'edit',
                'icon': 'fas fa-edit',
                'description': 'Edit and manipulate your files',
                'display_order': 3,
            },
            {
                'name': 'Image Tools',
                'slug': 'image-tools',
                'icon': 'fas fa-image',
                'description': 'Tools for working with images',
                'display_order': 4,
            },
            {
                'name': 'Video Tools',
                'slug': 'video-tools',
                'icon': 'fas fa-video',
                'description': 'Tools for working with videos',
                'display_order': 5,
            },
        ]
        
        for cat_data in categories:
            category, created = ToolCategory.objects.get_or_create(
                slug=cat_data['slug'],
                defaults=cat_data
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'  ✓ Created category: {category.name}'))
            else:
                self.stdout.write(f'  - Category already exists: {category.name}')

    def create_tools(self):
        """Create tools."""
        self.stdout.write('Creating tools...')
        
        # Get categories
        convert_cat = ToolCategory.objects.get(slug='convert')
        compress_cat = ToolCategory.objects.get(slug='compress')
        edit_cat = ToolCategory.objects.get(slug='edit')
        image_cat = ToolCategory.objects.get(slug='image-tools')
        video_cat = ToolCategory.objects.get(slug='video-tools')
        
        tools = [
            # Convert tools
            {
                'category': convert_cat,
                'name': 'PDF to DOCX Converter',
                'slug': 'pdf-to-docx',
                'description': 'Convert PDF files to editable Word documents',
                'icon': 'fas fa-file-word',
                'tool_type': 'pdf_to_docx',
                'max_file_size_mb': 50,
                'supported_formats': ['pdf'],
                'is_premium': False,
                'display_order': 1,
            },
            {
                'category': convert_cat,
                'name': 'DOCX to PDF Converter',
                'slug': 'docx-to-pdf',
                'description': 'Convert Word documents to PDF format',
                'icon': 'fas fa-file-pdf',
                'tool_type': 'docx_to_pdf',
                'max_file_size_mb': 50,
                'supported_formats': ['docx', 'doc'],
                'is_premium': False,
                'display_order': 2,
            },
            {
                'category': convert_cat,
                'name': 'Excel to PDF Converter',
                'slug': 'xlsx-to-pdf',
                'description': 'Convert Excel spreadsheets to PDF',
                'icon': 'fas fa-file-excel',
                'tool_type': 'xlsx_to_pdf',
                'max_file_size_mb': 50,
                'supported_formats': ['xlsx', 'xls'],
                'is_premium': False,
                'display_order': 3,
            },
            {
                'category': convert_cat,
                'name': 'PowerPoint to PDF Converter',
                'slug': 'pptx-to-pdf',
                'description': 'Convert PowerPoint presentations to PDF',
                'icon': 'fas fa-file-powerpoint',
                'tool_type': 'pptx_to_pdf',
                'max_file_size_mb': 50,
                'supported_formats': ['pptx', 'ppt'],
                'is_premium': False,
                'display_order': 4,
            },
            {
                'category': convert_cat,
                'name': 'Image to PDF Converter',
                'slug': 'image-to-pdf',
                'description': 'Convert images to PDF format',
                'icon': 'fas fa-images',
                'tool_type': 'image_to_pdf',
                'max_file_size_mb': 20,
                'supported_formats': ['jpg', 'jpeg', 'png', 'gif', 'bmp'],
                'is_premium': False,
                'display_order': 5,
            },
            
            # Compress tools
            {
                'category': compress_cat,
                'name': 'Compress PDF',
                'slug': 'compress-pdf',
                'description': 'Reduce PDF file size without losing quality',
                'icon': 'fas fa-compress',
                'tool_type': 'compress_pdf',
                'max_file_size_mb': 100,
                'supported_formats': ['pdf'],
                'is_premium': False,
                'display_order': 1,
            },
            {
                'category': compress_cat,
                'name': 'Compress Image',
                'slug': 'compress-image',
                'description': 'Reduce image file size',
                'icon': 'fas fa-compress-arrows-alt',
                'tool_type': 'compress_image',
                'max_file_size_mb': 20,
                'supported_formats': ['jpg', 'jpeg', 'png'],
                'is_premium': False,
                'display_order': 2,
            },
            {
                'category': compress_cat,
                'name': 'Compress Video',
                'slug': 'compress-video',
                'description': 'Reduce video file size (max 100MB)',
                'icon': 'fas fa-video',
                'tool_type': 'compress_video',
                'max_file_size_mb': 100,
                'supported_formats': ['mp4', 'mov', 'avi', 'mkv', 'mpeg', 'mpg'],
                'is_premium': True,
                'display_order': 3,
            },
            
            # Edit tools
            {
                'category': edit_cat,
                'name': 'Merge PDF',
                'slug': 'merge-pdf',
                'description': 'Combine multiple PDF files into one',
                'icon': 'fas fa-object-group',
                'tool_type': 'merge_pdf',
                'max_file_size_mb': 50,
                'supported_formats': ['pdf'],
                'is_premium': False,
                'display_order': 1,
            },
            {
                'category': edit_cat,
                'name': 'Split PDF',
                'slug': 'split-pdf',
                'description': 'Split PDF into multiple files',
                'icon': 'fas fa-cut',
                'tool_type': 'split_pdf',
                'max_file_size_mb': 50,
                'supported_formats': ['pdf'],
                'is_premium': False,
                'display_order': 2,
            },
            {
                'category': edit_cat,
                'name': 'Extract Text from PDF',
                'slug': 'extract-text',
                'description': 'Extract text content from PDF files',
                'icon': 'fas fa-file-alt',
                'tool_type': 'extract_text',
                'max_file_size_mb': 50,
                'supported_formats': ['pdf'],
                'is_premium': True,
                'display_order': 3,
            },
            
            # Image tools
            {
                'category': image_cat,
                'name': 'Convert Image Format',
                'slug': 'convert-image',
                'description': 'Convert images between different formats',
                'icon': 'fas fa-sync-alt',
                'tool_type': 'convert_image',
                'max_file_size_mb': 20,
                'supported_formats': ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp'],
                'is_premium': False,
                'display_order': 1,
            },
        ]
        
        created_count = 0
        for tool_data in tools:
            tool, created = Tool.objects.get_or_create(
                slug=tool_data['slug'],
                defaults=tool_data
            )
            
            if created:
                created_count += 1
                premium_badge = ' [PREMIUM]' if tool.is_premium else ''
                self.stdout.write(self.style.SUCCESS(f'  ✓ Created tool: {tool.name}{premium_badge}'))
            else:
                self.stdout.write(f'  - Tool already exists: {tool.name}')
        
        self.stdout.write(self.style.SUCCESS(f'  Total: {created_count} new tools created'))

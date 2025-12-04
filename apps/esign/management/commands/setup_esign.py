"""
Management command to setup E-Sign tool and category
"""
from django.core.management.base import BaseCommand
from apps.tools.models import Tool, ToolCategory

class Command(BaseCommand):
    help = 'Setup E-Sign tool and category'

    def handle(self, *args, **kwargs):
        # 1. Create E-Sign Category
        category, created = ToolCategory.objects.get_or_create(
            slug='esign',
            defaults={
                'name': 'E-Sign',
                'description': 'Securely sign PDF documents online',
                'icon': 'fa-file-signature',
                'display_order': 4,
                'is_active': True
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS('Created "E-Sign" category'))
        else:
            self.stdout.write('Category "E-Sign" already exists')

        # 2. Create E-Sign Tool
        defaults = {
            'name': 'E-Sign PDF',
            'slug': 'esign-pdf',
            'category': category,
            'description': 'Sign PDF documents securely. Upload your PDF, add your signature, and download the signed document.',
            'icon': 'fa-file-signature',
            'input_format': 'PDF',
            'output_format': 'Signed PDF',
            'max_file_size_mb': 50,
            'is_active': True,
            'is_premium': False,
            'display_order': 1,
            
            # Instructional Content
            'long_description': """Sign your PDF documents online with ease. Our E-Sign tool allows you to add secure digital signatures to your contracts, agreements, and forms. The process is fast, secure, and maintains the quality of your original PDF file.
            
Features:
- Draw, Type, or Upload signatures
- Secure OTP verification
- Comprehensive Audit Trail
- Tamper-proof final document""",
            
            'step_1_title': 'Select Your File',
            'step_1_description': 'Choose the PDF document you want to sign from your device.',
            
            'step_2_title': 'Add Signature',
            'step_2_description': 'Create your signature by drawing, typing, or uploading an image, then place it on the document.',
            
            'step_3_title': 'Download Signed PDF',
            'step_3_description': 'Once you have placed your signature, click Finish to download your signed document instantly.'
        }

        tool, created = Tool.objects.get_or_create(
            tool_type='esign',
            defaults=defaults
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS('Created "E-Sign PDF" tool'))
        else:
            self.stdout.write('Tool "E-Sign PDF" already exists - Updating content')
            for key, value in defaults.items():
                setattr(tool, key, value)
            tool.save()

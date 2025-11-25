"""
Management command to update DOCX to PDF tool to support both .doc and .docx files.
"""
from django.core.management.base import BaseCommand
from apps.tools.models import Tool


class Command(BaseCommand):
    help = 'Update DOCX to PDF tool to support both .doc and .docx files'

    def handle(self, *args, **options):
        try:
            tool = Tool.objects.get(tool_type='docx_to_pdf')
            
            self.stdout.write(f'Found tool: {tool.name}')
            self.stdout.write(f'Current supported formats: {tool.supported_formats}')
            
            # Update supported formats to include both doc and docx
            if 'doc' not in tool.supported_formats:
                tool.supported_formats.append('doc')
                tool.save()
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Added "doc" to supported formats'
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        '"doc" is already in supported formats'
                    )
                )
            
            self.stdout.write(f'Updated supported formats: {tool.supported_formats}')
            self.stdout.write(
                self.style.SUCCESS(
                    '\n✓ Tool updated successfully!'
                )
            )
            
        except Tool.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(
                    '✗ DOCX to PDF tool not found in database'
                )
            )

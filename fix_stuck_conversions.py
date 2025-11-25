#!/usr/bin/env python
"""
Fix conversions that completed but status wasn't updated.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smartfiletools.settings')
django.setup()

from apps.tools.models import ConversionHistory
from django.conf import settings
from django.utils import timezone

# Find pending conversions that have output files
pending = ConversionHistory.objects.filter(status='pending')

print(f"Checking {pending.count()} pending conversions...")

fixed = 0
for conversion in pending:
    if conversion.output_file:
        # Check if output file exists
        output_path = os.path.join(settings.MEDIA_ROOT, str(conversion.output_file))
        if os.path.exists(output_path):
            print(f"✓ Fixing conversion {conversion.id} - file exists")
            conversion.status = 'completed'
            conversion.completed_at = timezone.now()
            if not conversion.processing_time:
                conversion.processing_time = 3.0  # Estimate
            
            # Get file size
            if not conversion.file_size_after:
                conversion.file_size_after = os.path.getsize(output_path)
            
            conversion.save()
            fixed += 1
        else:
            print(f"✗ Conversion {conversion.id} - output file missing")
    else:
        print(f"- Conversion {conversion.id} - no output file")

print(f"\n✓ Fixed {fixed} conversions")

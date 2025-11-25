#!/usr/bin/env python
"""
Utility script to clear rate limiting for development.
Run this when you get blocked during testing.
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smartfiletools.settings')
django.setup()

from django.core.cache import cache

# Clear the entire cache (works with both Redis and LocMemCache)
try:
    cache.clear()
    print("✓ Cache cleared successfully!")
    print("✓ All rate limits have been reset.")
    print("✓ You can now login again.")
except Exception as e:
    print(f"✗ Error clearing cache: {e}")
    print("\nAlternative: Restart your Django server to clear the in-memory cache.")

#!/usr/bin/env python
"""
Script to create superuser and seed initial data.
This script automates the initial setup of the SmartFileTools platform.

Usage:
    python setup_initial_data.py
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smartfiletools.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import transaction

User = get_user_model()


def print_header(text):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(text)
    print("=" * 60)


def create_superuser():
    """Create admin superuser if it doesn't exist."""
    print_header("CREATING ADMIN SUPERUSER")
    
    # Check if superuser already exists
    if User.objects.filter(is_superuser=True).exists():
        print("⚠️  Superuser already exists!")
        superuser = User.objects.filter(is_superuser=True).first()
        print(f"   Username: {superuser.username}")
        print(f"   Email: {superuser.email}")
        return superuser
    
    # Default credentials
    username = os.getenv('ADMIN_USERNAME', 'admin')
    email = os.getenv('ADMIN_EMAIL', 'admin@smartfiletools.com')
    password = os.getenv('ADMIN_PASSWORD', 'admin123')
    
    print(f"Creating superuser: {username}")
    
    try:
        with transaction.atomic():
            superuser = User.objects.create_superuser(
                username=username,
                email=email,
                password=password,
                is_premium=True,
                credits=1000
            )
        
        print("✅ Superuser created successfully!")
        print(f"   Username: {username}")
        print(f"   Email: {email}")
        print(f"   Password: {password}")
        print("\n⚠️  IMPORTANT: Change the default password after first login!")
        
        return superuser
        
    except Exception as e:
        print(f"❌ Error creating superuser: {e}")
        return None


def seed_initial_data():
    """Run the seed_data management command."""
    print_header("SEEDING INITIAL DATA")
    
    try:
        # Run seed_data command
        call_command('seed_data')
        print("\n✅ Initial data seeded successfully!")
        
    except Exception as e:
        print(f"❌ Error seeding data: {e}")
        import traceback
        traceback.print_exc()


def display_summary():
    """Display summary of created data."""
    print_header("SETUP SUMMARY")
    
    from apps.common.models import SiteTheme
    from apps.tools.models import ToolCategory, Tool
    
    # Count records
    users_count = User.objects.count()
    superusers_count = User.objects.filter(is_superuser=True).count()
    themes_count = SiteTheme.objects.count()
    categories_count = ToolCategory.objects.count()
    tools_count = Tool.objects.count()
    premium_tools_count = Tool.objects.filter(is_premium=True).count()
    
    print(f"\n📊 Database Statistics:")
    print(f"   Users: {users_count} (Superusers: {superusers_count})")
    print(f"   Themes: {themes_count}")
    print(f"   Tool Categories: {categories_count}")
    print(f"   Tools: {tools_count} (Premium: {premium_tools_count})")
    
    # List categories and tools
    print(f"\n📁 Tool Categories:")
    for category in ToolCategory.objects.all().order_by('display_order'):
        tools_in_cat = Tool.objects.filter(category=category).count()
        print(f"   • {category.name} ({tools_in_cat} tools)")
    
    print(f"\n🔧 Available Tools:")
    for tool in Tool.objects.all().order_by('category__display_order', 'display_order'):
        premium_badge = " [PREMIUM]" if tool.is_premium else ""
        print(f"   • {tool.name}{premium_badge}")
        print(f"     - Slug: {tool.slug}")
        print(f"     - Type: {tool.tool_type}")
        print(f"     - Max Size: {tool.max_file_size_mb}MB")


def display_next_steps():
    """Display next steps for the user."""
    print_header("NEXT STEPS")
    
    print("\n1. Start the development server:")
    print("   python manage.py runserver")
    
    print("\n2. Access the admin panel:")
    print("   http://localhost:8000/admin/")
    print("   Username: admin")
    print("   Password: admin123")
    
    print("\n3. Access the main site:")
    print("   http://localhost:8000/")
    
    print("\n4. Start Celery worker (in another terminal):")
    print("   celery -A smartfiletools worker --loglevel=info")
    
    print("\n5. Start Celery beat (in another terminal):")
    print("   celery -A smartfiletools beat --loglevel=info")
    
    print("\n6. Using Docker:")
    print("   docker-compose up -d")
    print("   docker-compose exec web python manage.py createsuperuser")
    
    print("\n⚠️  Security Reminders:")
    print("   • Change the default admin password")
    print("   • Update SECRET_KEY in production")
    print("   • Set DEBUG=False in production")
    print("   • Configure proper database credentials")


def save_credentials():
    """Save credentials to a file."""
    credentials_file = '.admin_credentials.txt'
    
    username = os.getenv('ADMIN_USERNAME', 'admin')
    email = os.getenv('ADMIN_EMAIL', 'admin@smartfiletools.com')
    password = os.getenv('ADMIN_PASSWORD', 'admin123')
    
    try:
        with open(credentials_file, 'w') as f:
            f.write("SmartFileTools Admin Credentials\n")
            f.write("=" * 40 + "\n\n")
            f.write(f"Username: {username}\n")
            f.write(f"Email: {email}\n")
            f.write(f"Password: {password}\n")
            f.write("\n" + "=" * 40 + "\n")
            f.write("⚠️  IMPORTANT: Change this password after first login!\n")
            f.write("⚠️  Delete this file after noting the credentials!\n")
        
        print(f"\n📝 Credentials saved to: {credentials_file}")
        print("   ⚠️  Remember to delete this file after noting the credentials!")
        
    except Exception as e:
        print(f"⚠️  Could not save credentials file: {e}")


def main():
    """Main setup function."""
    print("\n🚀 SmartFileTools Initial Setup")
    print("=" * 60)
    
    try:
        # Step 1: Create superuser
        superuser = create_superuser()
        
        if superuser:
            # Save credentials
            save_credentials()
        
        # Step 2: Seed initial data
        seed_initial_data()
        
        # Step 3: Display summary
        display_summary()
        
        # Step 4: Display next steps
        display_next_steps()
        
        print("\n" + "=" * 60)
        print("🎉 Setup completed successfully!")
        print("=" * 60 + "\n")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

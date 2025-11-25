#!/usr/bin/env python
"""
Script to verify database migrations and tables.
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smartfiletools.settings')
django.setup()

from django.db import connection
from django.core.management import call_command

def verify_migrations():
    """Verify all migrations are applied."""
    print("=" * 60)
    print("MIGRATION VERIFICATION")
    print("=" * 60)
    
    # Show migration status
    print("\n📋 Migration Status:")
    print("-" * 60)
    call_command('showmigrations', '--list')
    
    # Check for unapplied migrations
    print("\n🔍 Checking for unapplied migrations...")
    try:
        call_command('migrate', '--check')
        print("✅ All migrations are applied!")
    except SystemExit:
        print("❌ There are unapplied migrations!")
        return False
    
    return True

def verify_tables():
    """Verify database tables exist."""
    print("\n" + "=" * 60)
    print("DATABASE TABLES VERIFICATION")
    print("=" * 60)
    
    with connection.cursor() as cursor:
        # Get all tables (PostgreSQL)
        cursor.execute("""
            SELECT tablename FROM pg_catalog.pg_tables 
            WHERE schemaname = 'public'
            ORDER BY tablename;
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        print(f"\n📊 Total Tables: {len(tables)}")
        print("-" * 60)
        
        # Group tables by app
        app_tables = {
            'accounts': [],
            'tools': [],
            'ads': [],
            'api': [],
            'common': [],
            'django': [],
            'other': []
        }
        
        for table in tables:
            if table.startswith('accounts_'):
                app_tables['accounts'].append(table)
            elif table.startswith('tools_'):
                app_tables['tools'].append(table)
            elif table.startswith('ads_'):
                app_tables['ads'].append(table)
            elif table.startswith('api_'):
                app_tables['api'].append(table)
            elif table.startswith('common_'):
                app_tables['common'].append(table)
            elif table.startswith('django_') or table.startswith('auth_'):
                app_tables['django'].append(table)
            else:
                app_tables['other'].append(table)
        
        # Display tables by app
        for app_name, app_table_list in app_tables.items():
            if app_table_list:
                print(f"\n{app_name.upper()} ({len(app_table_list)} tables):")
                for table in sorted(app_table_list):
                    print(f"  ✓ {table}")
    
    return True

def verify_models():
    """Verify models can be imported."""
    print("\n" + "=" * 60)
    print("MODEL VERIFICATION")
    print("=" * 60)
    
    models_to_check = [
        ('accounts', ['User']),
        ('tools', ['Tool', 'ToolCategory', 'ConversionHistory']),
        ('ads', ['Advertisement']),
        ('api', ['APIMerchant', 'APIKey', 'APIUsageLog', 'APIAccessRequest']),
        ('common', ['SiteTheme', 'ConversionLog']),
    ]
    
    all_models_ok = True
    
    for app_name, model_names in models_to_check:
        print(f"\n{app_name.upper()}:")
        for model_name in model_names:
            try:
                module = __import__(f'apps.{app_name}.models', fromlist=[model_name])
                model = getattr(module, model_name)
                count = model.objects.count()
                print(f"  ✓ {model_name} (table exists, {count} records)")
            except Exception as e:
                print(f"  ✗ {model_name} - Error: {e}")
                all_models_ok = False
    
    return all_models_ok

def main():
    """Main verification function."""
    print("\n🚀 Starting Database Verification...\n")
    
    try:
        # Verify migrations
        migrations_ok = verify_migrations()
        
        # Verify tables
        tables_ok = verify_tables()
        
        # Verify models
        models_ok = verify_models()
        
        # Summary
        print("\n" + "=" * 60)
        print("VERIFICATION SUMMARY")
        print("=" * 60)
        print(f"Migrations: {'✅ PASS' if migrations_ok else '❌ FAIL'}")
        print(f"Tables:     {'✅ PASS' if tables_ok else '❌ FAIL'}")
        print(f"Models:     {'✅ PASS' if models_ok else '❌ FAIL'}")
        
        if migrations_ok and tables_ok and models_ok:
            print("\n🎉 All verifications passed!")
            return 0
        else:
            print("\n⚠️  Some verifications failed!")
            return 1
            
    except Exception as e:
        print(f"\n❌ Error during verification: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())

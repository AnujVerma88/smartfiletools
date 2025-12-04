# Generated manually to fix celery_task_id nullable issue

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('esign', '0001_initial'),  # Adjust this to your latest migration
    ]

    operations = [
        migrations.AlterField(
            model_name='signsession',
            name='celery_task_id',
            field=models.CharField(blank=True, default='', help_text='Celery task ID for async processing', max_length=255),
        ),
    ]

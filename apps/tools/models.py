from django.db import models
from django.conf import settings
from django.utils.text import slugify


class ToolCategory(models.Model):
    """
    Categories for organizing conversion tools (e.g., Convert, Compress, Edit).
    """
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text='Category name (e.g., Convert, Compress, Edit)'
    )
    slug = models.SlugField(
        max_length=100,
        unique=True,
        help_text='URL-friendly version of the name'
    )
    icon = models.CharField(
        max_length=100,
        blank=True,
        help_text='Icon class or SVG path for the category'
    )
    description = models.TextField(
        blank=True,
        help_text='Description of the category'
    )
    display_order = models.IntegerField(
        default=0,
        help_text='Order in which categories are displayed (lower numbers first)'
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this category is visible to users'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Tool Category'
        verbose_name_plural = 'Tool Categories'
        ordering = ['display_order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """Auto-generate slug from name if not provided."""
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Tool(models.Model):
    """
    Individual conversion tools with their configurations and settings.
    """
    TOOL_TYPE_CHOICES = [
        ('pdf_to_docx', 'PDF to DOCX'),
        ('docx_to_pdf', 'DOCX to PDF'),
        ('xlsx_to_pdf', 'XLSX to PDF'),
        ('pptx_to_pdf', 'PPTX to PDF'),
        ('image_to_pdf', 'Image to PDF'),
        ('merge_pdf', 'Merge PDFs'),
        ('split_pdf', 'Split PDF'),
        ('compress_pdf', 'Compress PDF'),
        ('compress_image', 'Compress Image'),
        ('convert_image', 'Convert Image'),
        ('compress_video', 'Compress Video'),
        ('extract_text', 'Extract Text from PDF'),
        ('esign', 'E-Sign PDF'),  # E-Sign functionality
    ]

    category = models.ForeignKey(
        ToolCategory,
        on_delete=models.CASCADE,
        related_name='tools',
        help_text='Category this tool belongs to'
    )
    name = models.CharField(
        max_length=200,
        help_text='Display name of the tool (e.g., "PDF to DOCX Converter")'
    )
    slug = models.SlugField(
        max_length=200,
        unique=True,
        help_text='URL-friendly version of the name'
    )
    description = models.TextField(
        help_text='Short description of what the tool does'
    )
    icon = models.CharField(
        max_length=100,
        blank=True,
        help_text='Icon class or SVG path for the tool'
    )
    tool_type = models.CharField(
        max_length=50,
        choices=TOOL_TYPE_CHOICES,
        unique=True,
        help_text='Internal identifier for the tool type'
    )
    max_file_size_mb = models.IntegerField(
        default=50,
        help_text='Maximum file size allowed in MB'
    )
    supported_formats = models.JSONField(
        default=list,
        help_text='List of supported file extensions (e.g., ["pdf", "docx"])'
    )
    is_premium = models.BooleanField(
        default=False,
        help_text='Whether this tool requires a premium account'
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this tool is available to users'
    )
    usage_count = models.IntegerField(
        default=0,
        help_text='Total number of times this tool has been used'
    )
    display_order = models.IntegerField(
        default=0,
        help_text='Order in which tools are displayed within category'
    )
    
    # Instructional content fields
    input_format = models.CharField(
        max_length=100,
        blank=True,
        help_text='Input file format (e.g., "PDF", "DOCX", "Image")'
    )
    output_format = models.CharField(
        max_length=100,
        blank=True,
        help_text='Output file format (e.g., "DOCX", "PDF", "Compressed PDF")'
    )
    long_description = models.TextField(
        blank=True,
        help_text='Detailed description of the tool and its benefits'
    )
    
    # Custom step fields (optional - if not provided, defaults will be used)
    step_1_title = models.CharField(
        max_length=200,
        blank=True,
        help_text='Custom title for step 1 (default: "Select Your File")'
    )
    step_1_description = models.TextField(
        blank=True,
        help_text='Custom description for step 1'
    )
    step_2_title = models.CharField(
        max_length=200,
        blank=True,
        help_text='Custom title for step 2 (default: "Start Conversion")'
    )
    step_2_description = models.TextField(
        blank=True,
        help_text='Custom description for step 2'
    )
    step_3_title = models.CharField(
        max_length=200,
        blank=True,
        help_text='Custom title for step 3 (default: "Download Your File")'
    )
    step_3_description = models.TextField(
        blank=True,
        help_text='Custom description for step 3'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Tool'
        verbose_name_plural = 'Tools'
        ordering = ['category', 'display_order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """Auto-generate slug from name if not provided."""
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def increment_usage(self):
        """Increment the usage counter for this tool."""
        self.usage_count += 1
        self.save(update_fields=['usage_count'])
    
    def get_step_1(self):
        """Return step 1 content (custom or default)."""
        return {
            'title': self.step_1_title or 'Select Your File',
            'description': self.step_1_description or f'Choose the {self.input_format or "file"} you want to convert from your device.'
        }
    
    def get_step_2(self):
        """Return step 2 content (custom or default)."""
        return {
            'title': self.step_2_title or 'Start Conversion',
            'description': self.step_2_description or f'Click the convert button and our system will process your {self.input_format or "file"} to {self.output_format or "the desired format"}.'
        }
    
    def get_step_3(self):
        """Return step 3 content (custom or default)."""
        return {
            'title': self.step_3_title or 'Download Your File',
            'description': self.step_3_description or f'Once conversion is complete, download your {self.output_format or "converted file"} instantly.'
        }
    
    def get_all_steps(self):
        """Return all steps as a list."""
        return [
            self.get_step_1(),
            self.get_step_2(),
            self.get_step_3()
        ]
    
    def get_tool_description(self):
        """Return long description or generate from short description."""
        if self.long_description:
            return self.long_description
        
        # Generate a default long description if not provided
        if self.input_format and self.output_format:
            return f"Convert your {self.input_format} files to {self.output_format} format quickly and easily. " \
                   f"Our {self.name} tool provides fast, secure, and high-quality conversions. " \
                   f"{self.description}"
        return self.description


class ConversionHistory(models.Model):
    """
    History of file conversions performed by users.
    Tracks input/output files, status, and processing details.
    """
    TOOL_CHOICES = [
        ('pdf_to_docx', 'PDF to DOCX'),
        ('docx_to_pdf', 'DOCX to PDF'),
        ('xlsx_to_pdf', 'XLSX to PDF'),
        ('pptx_to_pdf', 'PPTX to PDF'),
        ('image_to_pdf', 'Image to PDF'),
        ('merge_pdf', 'Merge PDFs'),
        ('split_pdf', 'Split PDF'),
        ('compress_pdf', 'Compress PDF'),
        ('compress_image', 'Compress Image'),
        ('convert_image', 'Convert Image'),
        ('compress_video', 'Compress Video'),
        ('extract_text', 'Extract Text from PDF'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='conversions',
        help_text='User who performed the conversion (null for anonymous)'
    )
    tool_type = models.CharField(
        max_length=50,
        choices=TOOL_CHOICES,
        help_text='Type of conversion tool used'
    )
    input_file = models.FileField(
        upload_to='uploads/%Y/%m/%d/',
        help_text='Original uploaded file'
    )
    output_file = models.FileField(
        upload_to='output/%Y/%m/%d/',
        null=True,
        blank=True,
        help_text='Converted output file'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text='Current status of the conversion'
    )
    error_message = models.TextField(
        null=True,
        blank=True,
        help_text='Error details if conversion failed'
    )
    
    # File size tracking
    file_size_before = models.BigIntegerField(
        default=0,
        help_text='Original file size in bytes'
    )
    file_size_after = models.BigIntegerField(
        null=True,
        blank=True,
        help_text='Converted file size in bytes'
    )
    
    # Processing metrics
    processing_time = models.FloatField(
        null=True,
        blank=True,
        help_text='Time taken for conversion in seconds'
    )
    
    # Celery task tracking
    celery_task_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text='Celery task ID for tracking async processing'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Timestamp when conversion completed'
    )

    class Meta:
        verbose_name = 'Conversion History'
        verbose_name_plural = 'Conversion Histories'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['tool_type', '-created_at']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['celery_task_id']),
        ]

    def __str__(self):
        return f"{self.tool_type} - {self.id}"
    
    def get_compression_ratio(self):
        """Calculate compression ratio if applicable."""
        if self.file_size_before and self.file_size_after:
            ratio = (1 - (self.file_size_after / self.file_size_before)) * 100
            return round(ratio, 2)
        return None
    
    def get_file_size_saved(self):
        """Calculate bytes saved through compression."""
        if self.file_size_before and self.file_size_after:
            return self.file_size_before - self.file_size_after
        return None

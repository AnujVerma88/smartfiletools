"""
Management command to populate instructional content for existing tools.
Usage: python manage.py populate_instructional_content
"""
from django.core.management.base import BaseCommand
from apps.tools.models import Tool


class Command(BaseCommand):
    help = 'Populate instructional content (input_format, output_format, long_description) for existing tools'

    def handle(self, *args, **options):
        """Populate instructional content for all tools."""
        
        # Define instructional content for each tool type
        tool_content = {
            'pdf_to_docx': {
                'input_format': 'PDF',
                'output_format': 'DOCX',
                'long_description': (
                    'Convert your PDF files to editable Microsoft Word (DOCX) documents with ease. '
                    'Our PDF to DOCX converter preserves formatting, images, and text layout, making it '
                    'perfect for editing contracts, reports, and other documents. The conversion process '
                    'is fast, secure, and maintains the quality of your original PDF file.'
                ),
            },
            'docx_to_pdf': {
                'input_format': 'DOCX',
                'output_format': 'PDF',
                'long_description': (
                    'Transform your Microsoft Word documents into professional PDF files instantly. '
                    'Our DOCX to PDF converter ensures that your formatting, fonts, and images remain '
                    'intact. Perfect for sharing documents that need to look the same on any device, '
                    'creating professional reports, or preparing files for printing.'
                ),
            },
            'xlsx_to_pdf': {
                'input_format': 'XLSX',
                'output_format': 'PDF',
                'long_description': (
                    'Convert Excel spreadsheets to PDF format while preserving all your data, formulas, '
                    'and formatting. Our XLSX to PDF converter is ideal for creating shareable reports, '
                    'financial statements, and data presentations that look professional on any device. '
                    'Your spreadsheet layout and styling will be maintained in the PDF output.'
                ),
            },
            'pptx_to_pdf': {
                'input_format': 'PPTX',
                'output_format': 'PDF',
                'long_description': (
                    'Convert PowerPoint presentations to PDF format for easy sharing and distribution. '
                    'Our PPTX to PDF converter maintains your slide layouts, animations metadata, and '
                    'formatting. Perfect for creating handouts, sharing presentations with clients, or '
                    'archiving your slides in a universal format that works on any device.'
                ),
            },
            'image_to_pdf': {
                'input_format': 'Image (JPG, PNG)',
                'output_format': 'PDF',
                'long_description': (
                    'Convert your images to PDF format quickly and easily. Our image to PDF converter '
                    'supports JPG, PNG, and other popular image formats. Perfect for creating photo '
                    'albums, combining multiple images into a single document, or preparing images for '
                    'professional printing. The conversion maintains image quality and resolution.'
                ),
            },
            'merge_pdf': {
                'input_format': 'Multiple PDFs',
                'output_format': 'Single PDF',
                'long_description': (
                    'Combine multiple PDF files into one document effortlessly. Our PDF merger tool '
                    'allows you to arrange pages in any order, making it perfect for combining reports, '
                    'contracts, or presentations. The merged PDF maintains the quality and formatting of '
                    'all original files, creating a professional single document.'
                ),
            },
            'split_pdf': {
                'input_format': 'PDF',
                'output_format': 'Multiple PDFs',
                'long_description': (
                    'Split large PDF files into smaller, more manageable documents. Our PDF splitter '
                    'lets you extract specific pages or divide your PDF into multiple files. Perfect for '
                    'separating chapters, extracting important sections, or sharing only relevant pages. '
                    'Each split PDF maintains the original quality and formatting.'
                ),
            },
            'compress_pdf': {
                'input_format': 'PDF',
                'output_format': 'Compressed PDF',
                'long_description': (
                    'Reduce PDF file size without compromising quality. Our PDF compression tool uses '
                    'advanced algorithms to shrink your files, making them easier to email, upload, and '
                    'store. Perfect for large documents with images, scanned files, or presentations. '
                    'Choose your compression level to balance file size and quality.'
                ),
            },
            'compress_image': {
                'input_format': 'Image (JPG, PNG)',
                'output_format': 'Compressed Image',
                'long_description': (
                    'Optimize your images by reducing file size while maintaining visual quality. Our '
                    'image compression tool supports JPG, PNG, and other formats. Perfect for web '
                    'optimization, faster page loading, email attachments, or saving storage space. '
                    'Advanced compression algorithms ensure your images look great at smaller sizes.'
                ),
            },
            'convert_image': {
                'input_format': 'Image (Various)',
                'output_format': 'Image (Various)',
                'long_description': (
                    'Convert images between different formats including JPG, PNG, GIF, BMP, and more. '
                    'Our image converter maintains quality while transforming your files to the format '
                    'you need. Perfect for web compatibility, graphic design projects, or preparing '
                    'images for specific applications. Fast, reliable, and easy to use.'
                ),
            },
            'compress_video': {
                'input_format': 'Video (MP4, AVI)',
                'output_format': 'Compressed Video',
                'long_description': (
                    'Reduce video file size while preserving quality. Our video compression tool makes '
                    'large video files easier to share, upload, and store. Perfect for social media, '
                    'email attachments, or saving storage space. Choose your compression settings to '
                    'balance file size with video quality for your specific needs.'
                ),
            },
            'extract_text': {
                'input_format': 'PDF',
                'output_format': 'Text (TXT)',
                'long_description': (
                    'Extract text content from PDF files quickly and accurately. Our text extraction '
                    'tool converts PDF documents to plain text format, making it easy to edit, search, '
                    'and reuse content. Perfect for data analysis, content migration, or extracting '
                    'information from scanned documents using OCR technology.'
                ),
            },
        }
        
        updated_count = 0
        skipped_count = 0
        
        self.stdout.write(self.style.SUCCESS('Starting to populate instructional content...'))
        
        for tool in Tool.objects.all():
            if tool.tool_type in tool_content:
                content = tool_content[tool.tool_type]
                
                # Only update if fields are empty
                needs_update = False
                
                if not tool.input_format:
                    tool.input_format = content['input_format']
                    needs_update = True
                
                if not tool.output_format:
                    tool.output_format = content['output_format']
                    needs_update = True
                
                if not tool.long_description:
                    tool.long_description = content['long_description']
                    needs_update = True
                
                if needs_update:
                    tool.save()
                    updated_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Updated: {tool.name}')
                    )
                else:
                    skipped_count += 1
                    self.stdout.write(
                        self.style.WARNING(f'⊘ Skipped (already has content): {tool.name}')
                    )
            else:
                skipped_count += 1
                self.stdout.write(
                    self.style.WARNING(f'⊘ Skipped (no content defined): {tool.name}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ Completed! Updated {updated_count} tools, skipped {skipped_count} tools.'
            )
        )

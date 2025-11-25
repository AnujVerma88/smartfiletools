"""
PDF conversion services.
"""
import time
from pathlib import Path
from pdf2docx import Converter as PDF2DOCXConverter
from docx2pdf import convert as docx2pdf_convert
from openpyxl import load_workbook
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from pptx import Presentation

from apps.tools.utils.base_converter import BaseConverter, ConversionError
from apps.tools.utils.converter_factory import register_converter


@register_converter('pdf_to_docx')
class PDFToDocxConverter(BaseConverter):
    """
    Converter for PDF to DOCX format using pdf2docx library.
    """
    
    ALLOWED_INPUT_TYPES = ['application/pdf']
    ALLOWED_INPUT_EXTENSIONS = ['pdf']
    MAX_FILE_SIZE_MB = 50
    OUTPUT_EXTENSION = 'docx'
    
    def convert(self, input_path, output_path):
        """
        Convert PDF file to DOCX format.
        
        Args:
            input_path: Path to input PDF file
            output_path: Path where output DOCX file should be saved
            
        Returns:
            dict: Conversion result with status and metadata
        """
        start_time = time.time()
        self.log_conversion_start(input_path, output_path)
        
        try:
            # Validate input file
            self.validate_file(input_path)
            
            # Perform conversion
            cv = PDF2DOCXConverter(input_path)
            cv.convert(output_path)
            cv.close()
            
            duration = time.time() - start_time
            self.log_conversion_success(input_path, output_path, duration)
            
            return {
                'status': 'success',
                'output_path': output_path,
                'duration': duration,
                'input_info': self.get_file_info(input_path),
                'output_info': self.get_file_info(output_path),
            }
            
        except Exception as e:
            self.log_conversion_error(input_path, e)
            raise ConversionError(f"PDF to DOCX conversion failed: {str(e)}")


@register_converter('docx_to_pdf')
class DocxToPDFConverter(BaseConverter):
    """
    Converter for DOCX to PDF format using LibreOffice/unoconv or docx2pdf fallback.
    """
    
    ALLOWED_INPUT_TYPES = [
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/msword'  # Support .doc files
    ]
    ALLOWED_INPUT_EXTENSIONS = ['docx', 'doc']
    MAX_FILE_SIZE_MB = 50
    OUTPUT_EXTENSION = 'pdf'
    
    def convert(self, input_path, output_path):
        """
        Convert DOCX/DOC file to PDF format.
        
        Args:
            input_path: Path to input DOCX/DOC file
            output_path: Path where output PDF file should be saved
            
        Returns:
            dict: Conversion result with status and metadata
        """
        import os
        import win32com.client
        
        start_time = time.time()
        self.log_conversion_start(input_path, output_path)
        
        try:
            # Validate input file
            self.validate_file(input_path)
            
            input_path_str = str(input_path)
            
            # Check if file is .doc or .docx
            if input_path_str.lower().endswith('.doc') and not input_path_str.lower().endswith('.docx'):
                # For .doc files, use Word COM automation directly
                # since docx2pdf doesn't support .doc files
                try:
                    word = win32com.client.Dispatch("Word.Application")
                    word.Visible = False
                    
                    # Convert paths to absolute paths
                    abs_input = os.path.abspath(input_path)
                    abs_output = os.path.abspath(output_path)
                    
                    # Open document
                    doc = word.Documents.Open(abs_input)
                    
                    # Save as PDF (format 17 is PDF)
                    doc.SaveAs(abs_output, FileFormat=17)
                    doc.Close()
                    word.Quit()
                    
                except Exception as e:
                    try:
                        word.Quit()
                    except:
                        pass
                    raise ConversionError(f"Failed to convert .doc file: {str(e)}")
            else:
                # For .docx files, use docx2pdf library
                try:
                    docx2pdf_convert(input_path, output_path)
                except Exception as word_error:
                    # If docx2pdf fails, provide helpful error message
                    error_msg = str(word_error)
                    if 'Word.Application' in error_msg or 'Quit' in error_msg:
                        raise ConversionError(
                            "Microsoft Word is not installed or not accessible. "
                            "Please install Microsoft Word or use LibreOffice for DOCX to PDF conversion."
                        )
                    raise
            
            duration = time.time() - start_time
            self.log_conversion_success(input_path, output_path, duration)
            
            return {
                'status': 'success',
                'output_path': output_path,
                'duration': duration,
                'input_info': self.get_file_info(input_path),
                'output_info': self.get_file_info(output_path),
            }
            
        except Exception as e:
            self.log_conversion_error(input_path, e)
            raise ConversionError(f"DOCX to PDF conversion failed: {str(e)}")


@register_converter('xlsx_to_pdf')
class XLSXToPDFConverter(BaseConverter):
    """
    Converter for XLSX to PDF format using openpyxl and ReportLab.
    """
    
    ALLOWED_INPUT_TYPES = [
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    ]
    ALLOWED_INPUT_EXTENSIONS = ['xlsx']
    MAX_FILE_SIZE_MB = 50
    OUTPUT_EXTENSION = 'pdf'
    
    def convert(self, input_path, output_path):
        """
        Convert XLSX file to PDF format.
        
        Args:
            input_path: Path to input XLSX file
            output_path: Path where output PDF file should be saved
            
        Returns:
            dict: Conversion result with status and metadata
        """
        start_time = time.time()
        self.log_conversion_start(input_path, output_path)
        
        try:
            # Validate input file
            self.validate_file(input_path)
            
            # Load workbook
            wb = load_workbook(input_path, data_only=True)
            
            # Create PDF
            doc = SimpleDocTemplate(output_path, pagesize=A4)
            elements = []
            styles = getSampleStyleSheet()
            
            # Process each sheet
            for sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
                
                # Add sheet title
                elements.append(Paragraph(f"<b>{sheet_name}</b>", styles['Heading1']))
                elements.append(Spacer(1, 12))
                
                # Convert sheet data to table
                data = []
                for row in ws.iter_rows(values_only=True):
                    data.append([str(cell) if cell is not None else '' for cell in row])
                
                if data:
                    # Create table
                    table = Table(data)
                    table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 10),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ]))
                    elements.append(table)
                    elements.append(Spacer(1, 20))
            
            # Build PDF
            doc.build(elements)
            
            duration = time.time() - start_time
            self.log_conversion_success(input_path, output_path, duration)
            
            return {
                'status': 'success',
                'output_path': output_path,
                'duration': duration,
                'sheets_processed': len(wb.sheetnames),
                'input_info': self.get_file_info(input_path),
                'output_info': self.get_file_info(output_path),
            }
            
        except Exception as e:
            self.log_conversion_error(input_path, e)
            raise ConversionError(f"XLSX to PDF conversion failed: {str(e)}")


@register_converter('pptx_to_pdf')
class PPTXToPDFConverter(BaseConverter):
    """
    Converter for PPTX to PDF format using PowerPoint COM automation or LibreOffice.
    """
    
    ALLOWED_INPUT_TYPES = [
        'application/vnd.openxmlformats-officedocument.presentationml.presentation'
    ]
    ALLOWED_INPUT_EXTENSIONS = ['pptx']
    MAX_FILE_SIZE_MB = 100
    OUTPUT_EXTENSION = 'pdf'
    
    def _convert_with_powerpoint(self, input_path, output_path):
        """
        Convert PPTX to PDF using PowerPoint COM automation (Windows only).
        
        Args:
            input_path: Path to input PPTX file
            output_path: Path where output PDF file should be saved
            
        Raises:
            ConversionError: If PowerPoint conversion fails
        """
        import os
        import win32com.client
        
        powerpoint = None
        presentation = None
        
        try:
            # Convert to absolute paths (COM requires absolute paths)
            abs_input = os.path.abspath(input_path)
            abs_output = os.path.abspath(output_path)
            
            # Initialize PowerPoint application
            powerpoint = win32com.client.Dispatch("PowerPoint.Application")
            powerpoint.Visible = 0  # Run headless (0 = hidden, 1 = visible)
            
            # Open presentation without window
            presentation = powerpoint.Presentations.Open(
                abs_input,
                ReadOnly=True,
                Untitled=True,
                WithWindow=False
            )
            
            # Save as PDF (FileFormat=32 is PDF)
            presentation.SaveAs(abs_output, FileFormat=32)
            
            self.logger.info(f"PowerPoint COM conversion successful: {input_path} -> {output_path}")
            
        except Exception as e:
            error_msg = f"PowerPoint COM automation failed: {str(e)}"
            self.logger.error(error_msg)
            raise ConversionError(error_msg)
            
        finally:
            # Clean up COM objects
            try:
                if presentation:
                    presentation.Close()
            except Exception as e:
                self.logger.warning(f"Error closing presentation: {str(e)}")
            
            try:
                if powerpoint:
                    powerpoint.Quit()
            except Exception as e:
                self.logger.warning(f"Error quitting PowerPoint: {str(e)}")
    
    def convert(self, input_path, output_path):
        """
        Convert PPTX file to PDF format.
        
        Args:
            input_path: Path to input PPTX file
            output_path: Path where output PDF file should be saved
            
        Returns:
            dict: Conversion result with status and metadata
        """
        start_time = time.time()
        self.log_conversion_start(input_path, output_path)
        
        try:
            # Validate input file
            self.validate_file(input_path)
            
            # Load presentation
            prs = Presentation(input_path)
            
            # Create PDF
            doc = SimpleDocTemplate(output_path, pagesize=letter)
            elements = []
            styles = getSampleStyleSheet()
            
            # Process each slide
            for i, slide in enumerate(prs.slides, 1):
                # Add slide number
                elements.append(Paragraph(f"<b>Slide {i}</b>", styles['Heading1']))
                elements.append(Spacer(1, 12))
                
                # Extract text from shapes
                for shape in slide.shapes:
                    if hasattr(shape, "text") and shape.text:
                        elements.append(Paragraph(shape.text, styles['Normal']))
                        elements.append(Spacer(1, 6))
                
                elements.append(Spacer(1, 20))
            
            # Build PDF
            doc.build(elements)
            
            duration = time.time() - start_time
            self.log_conversion_success(input_path, output_path, duration)
            
            return {
                'status': 'success',
                'output_path': output_path,
                'duration': duration,
                'slides_processed': len(prs.slides),
                'input_info': self.get_file_info(input_path),
                'output_info': self.get_file_info(output_path),
            }
            
        except Exception as e:
            self.log_conversion_error(input_path, e)
            raise ConversionError(f"PPTX to PDF conversion failed: {str(e)}")

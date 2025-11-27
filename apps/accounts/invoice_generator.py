"""
Invoice PDF generation utility.
Generates professional invoices with GSTN and tax details.
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from io import BytesIO


def generate_invoice_pdf(invoice):
    """
    Generate PDF invoice with complete billing details.
    
    Args:
        invoice: Invoice model instance
    
    Returns:
        BytesIO: PDF file buffer
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
    elements = []
    styles = getSampleStyleSheet()
    
    # Company header
    company_style = ParagraphStyle(
        'CompanyHeader',
        parent=styles['Heading1'],
        fontSize=24,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#14B8A6'),
        spaceAfter=6,
        alignment=TA_CENTER
    )
    elements.append(Paragraph('SmartToolPDF', company_style))
    
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#6B7280'),
        alignment=TA_CENTER
    )
    elements.append(Paragraph('File Conversion Platform', subtitle_style))
    elements.append(Paragraph('smarttoolpdf@gmail.com', subtitle_style))
    elements.append(Spacer(1, 0.3*inch))
    
    # Invoice title
    title_style = ParagraphStyle(
        'InvoiceTitle',
        parent=styles['Heading2'],
        fontSize=20,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#111827'),
        alignment=TA_CENTER,
        spaceAfter=12
    )
    elements.append(Paragraph('TAX INVOICE', title_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # Invoice details
    invoice_data = [
        ['Invoice Number:', invoice.invoice_number],
        ['Invoice Date:', invoice.payment_date.strftime('%d %B %Y')],
        ['Payment Method:', invoice.get_payment_method_display()],
        ['Payment ID:', invoice.payment_id or 'N/A'],
        ['Company GSTN:', invoice.company_gstn],
    ]
    
    invoice_table = Table(invoice_data, colWidths=[2*inch, 3.5*inch])
    invoice_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#6B7280')),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#111827')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(invoice_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Billing addresses
    address_header_data = [['From:', 'To:']]
    address_header_table = Table(address_header_data, colWidths=[3*inch, 3*inch])
    address_header_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#111827')),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F3F4F6')),
        ('PADDING', (0, 0), (-1, 0), 8),
    ]))
    elements.append(address_header_table)
    
    # Build from address
    from_address_lines = [
        'SmartToolPDF',
        'smarttoolpdf@gmail.com',
        f'GSTN: {invoice.company_gstn}',
        'India'
    ]
    from_address = '\n'.join(from_address_lines)
    
    # Build to address
    to_address_lines = [
        invoice.billing_name or invoice.user.get_full_name() or invoice.user.username,
        invoice.billing_email
    ]
    if invoice.billing_address:
        to_address_lines.append(invoice.billing_address)
    if invoice.billing_city or invoice.billing_state:
        city_state = f'{invoice.billing_city}, {invoice.billing_state} {invoice.billing_pincode}'.strip()
        to_address_lines.append(city_state)
    to_address_lines.append(invoice.billing_country)
    to_address = '\n'.join(to_address_lines)
    
    address_data = [[from_address, to_address]]
    
    address_table = Table(address_data, colWidths=[3*inch, 3*inch])
    address_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
        ('PADDING', (0, 0), (-1, -1), 12),
    ]))
    elements.append(address_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Items table
    items_data = [
        ['Description', 'Period', 'Amount', 'Tax', 'Total'],
        [
            invoice.plan_name + ' Subscription',
            f"{invoice.billing_period_start.strftime('%d %b %Y')}\nto\n{invoice.billing_period_end.strftime('%d %b %Y')}",
            f"₹{invoice.plan_price:.2f}",
            f"₹{invoice.tax_amount:.2f}\n({invoice.tax_rate}% GST)",
            f"₹{invoice.total_amount:.2f}"
        ]
    ]
    
    items_table = Table(items_data, colWidths=[2.2*inch, 1.5*inch, 1*inch, 1*inch, 1*inch])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#14B8A6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
        ('PADDING', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Total summary
    total_data = [
        ['', '', '', 'Subtotal:', f"₹{invoice.plan_price:.2f}"],
        ['', '', '', f'GST ({invoice.tax_rate}%):', f"₹{invoice.tax_amount:.2f}"],
        ['', '', '', 'Total Amount:', f"₹{invoice.total_amount:.2f}"],
    ]
    
    total_table = Table(total_data, colWidths=[2.2*inch, 1.5*inch, 1*inch, 1*inch, 1*inch])
    total_table.setStyle(TableStyle([
        ('FONTNAME', (3, 0), (3, 1), 'Helvetica'),
        ('FONTNAME', (3, 2), (3, 2), 'Helvetica-Bold'),
        ('FONTNAME', (4, 0), (4, 1), 'Helvetica'),
        ('FONTNAME', (4, 2), (4, 2), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),
        ('LINEABOVE', (3, 2), (-1, 2), 1.5, colors.HexColor('#111827')),
        ('TEXTCOLOR', (3, 2), (-1, 2), colors.HexColor('#14B8A6')),
        ('BOTTOMPADDING', (0, 0), (-1, 1), 6),
        ('TOPPADDING', (0, 2), (-1, 2), 10),
    ]))
    elements.append(total_table)
    elements.append(Spacer(1, 0.5*inch))
    
    # Payment info
    if invoice.payment_id:
        payment_info_data = [['Payment ID:', invoice.payment_id]]
        payment_info_table = Table(payment_info_data, colWidths=[1.5*inch, 4*inch])
        payment_info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, 0), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ]))
        elements.append(payment_info_table)
        elements.append(Spacer(1, 0.2*inch))
    
    # Footer
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#6B7280'),
        alignment=TA_CENTER
    )
    elements.append(Spacer(1, 0.3*inch))
    
    footer_bold_style = ParagraphStyle(
        'FooterBold',
        parent=footer_style,
        fontName='Helvetica-Bold'
    )
    elements.append(Paragraph('Thank you for your business!', footer_bold_style))
    elements.append(Spacer(1, 0.1*inch))
    elements.append(Paragraph('For support and inquiries, contact: smarttoolpdf@gmail.com', footer_style))
    elements.append(Spacer(1, 0.1*inch))
    elements.append(Paragraph('This is a computer-generated invoice and does not require a signature.', footer_style))
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer

import os
from io import BytesIO
from typing import List, Dict, Any
from decimal import Decimal

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Need to register an Arabic Font (Amiri/Cairo/Tajawal, etc.)
# If the exact font TTF isn't in fonts/ directory, you should ideally load one.
# For fallback in reportlab if we don't have an arabic ttf right now we'll use a standard,
# but bidi logic needs to reverse RTL text. We will implement simple bidi via standard python packages if available,
# otherwise we rely on the OS / reportlab capabilities.
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    HAS_BIDI = True
except ImportError:
    HAS_BIDI = False

# A fallback basic RTL method if no packages
def format_arabic(text: str) -> str:
    if not isinstance(text, str):
        return str(text)
    if HAS_BIDI:
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    return text  # It might render LTR without packages

class FinancialReportPDF:
    """Class responsible for generating generic Financial Arabic PDF Reports."""

    def __init__(self, title: str, subtitle: str = ""):
        self.title = title
        self.subtitle = subtitle
        self.buffer = BytesIO()
        self.elements = []
        self._setup_styles()

    def _setup_styles(self):
        self.styles = getSampleStyleSheet()
        # Normal Text Style
        self.styles.add(ParagraphStyle(
            name='ArabicNormal',
            fontName='Helvetica', # Fallback if no Arabic TTF configured globally
            fontSize=10,
            alignment=2, # Right Alignment for RTL
            wordWrap='RTL',
        ))
        
        # Title Style
        self.styles.add(ParagraphStyle(
            name='ArabicTitle',
            fontName='Helvetica-Bold',
            fontSize=16,
            alignment=1, # Center Alignment
            spaceAfter=12,
        ))

        # Subtitle Style
        self.styles.add(ParagraphStyle(
            name='ArabicSubtitle',
            fontName='Helvetica',
            fontSize=12,
            alignment=1,
            spaceAfter=20,
        ))

    def add_header(self):
        title_para = Paragraph(format_arabic(self.title), self.styles['ArabicTitle'])
        self.elements.append(title_para)
        
        if self.subtitle:
            subtitle_para = Paragraph(format_arabic(self.subtitle), self.styles['ArabicSubtitle'])
            self.elements.append(subtitle_para)

    def add_table(self, headers: List[str], data_rows: List[List[Any]]):
        """
        Adds a table to the PDF.
        Args:
            headers: List of column names (Left to Right in coding, but drawn Right to Left usually)
            data_rows: List of lists containing the actual row data
        """
        formatted_headers = [Paragraph(format_arabic(h), self.styles['ArabicTitle']) for h in headers]
        
        # Format rows for Arabic text and Decimals
        formatted_data = []
        for row in data_rows:
            new_row = []
            for item in row:
                if isinstance(item, str):
                    new_row.append(Paragraph(format_arabic(item), self.styles['ArabicNormal']))
                elif isinstance(item, Decimal):
                    new_row.append(f"{item:,.2f}")
                else:
                    new_row.append(str(item))
            formatted_data.append(new_row)

        table_data = [formatted_headers] + formatted_data

        col_widths = [10*cm, 3*cm, 3*cm] if len(headers) == 3 else None  # Dynamic based on actual usual structure. Assume Account, Dr, Cr.
        if len(headers) > 3:
            col_widths = [None] * len(headers)

        table = Table(table_data, colWidths=col_widths, repeatRows=1)
        
        style = TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2C3E50")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 12),
            ('BOTTOMPADDING', (0,0), (-1,0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#ECF0F1")),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('ALIGN', (0,1), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,1), (-1,-1), 10),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ])
        
        table.setStyle(style)
        self.elements.append(table)
        self.elements.append(Spacer(1, 0.5*cm))

    def generate(self) -> bytes:
        """Generates the PDF document and returns as bytes."""
        doc = SimpleDocTemplate(self.buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=18)
        self.add_header()
        doc.build(self.elements)
        pdf_bytes = self.buffer.getvalue()
        self.buffer.close()
        return pdf_bytes

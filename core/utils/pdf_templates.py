from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import cm
from datetime import datetime


class InvoicePDFGenerator:
    """Generate professional invoices in PDF."""
    
    def __init__(self, invoice):
        self.invoice = invoice
        self.styles = getSampleStyleSheet()
    
    def generate(self, buffer):
        """Generate the invoice PDF."""
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        story = []
        
        # Company header
        story.append(self._create_header())
        story.append(Spacer(1, 0.5*cm))
        
        # Invoice info
        story.append(self._create_invoice_info())
        story.append(Spacer(1, 0.5*cm))
        
        # Customer info
        story.append(self._create_customer_info())
        story.append(Spacer(1, 1*cm))
        
        # Items table
        story.append(self._create_items_table())
        story.append(Spacer(1, 1*cm))
        
        # Totals
        story.append(self._create_totals())
        story.append(Spacer(1, 1*cm))
        
        # Footer
        story.append(self._create_footer())
        
        doc.build(story)
    
    def _create_header(self):
        """Create invoice header."""
        data = [
            [Paragraph('<b>SG-STOCK</b>', self.styles['Title']), ''],
            ['Application de Gestion Commerciale', '']
        ]
        table = Table(data, colWidths=[10*cm, 8*cm])
        return table
    
    def _create_invoice_info(self):
        """Create invoice information section."""
        data = [
            ['Facture N°:', self.invoice.invoice_number],
            ['Date:', self.invoice.invoice_date.strftime('%d/%m/%Y')],
            ['Échéance:', self.invoice.due_date.strftime('%d/%m/%Y')],
        ]
        table = Table(data, colWidths=[4*cm, 6*cm])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ]))
        return table
    
    def _create_customer_info(self):
        """Create customer information section."""
        customer = self.invoice.customer
        data = [
            ['Client:', customer.get_display_name()],
            ['Adresse:', customer.address or ''],
            ['Téléphone:', customer.phone or ''],
        ]
        table = Table(data, colWidths=[4*cm, 10*cm])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        return table
    
    def _create_items_table(self):
        """Create items table."""
        data = [['Désignation', 'Qté', 'Prix Unit.', 'TVA', 'Total']]
        
        for line in self.invoice.lines.all():
            data.append([
                line.description,
                str(line.quantity),
                f"{line.unit_price:,.0f} XAF",
                f"{line.tax_rate}%",
                f"{line.total:,.0f} XAF"
            ])
        
        table = Table(data, colWidths=[8*cm, 2*cm, 3*cm, 2*cm, 3*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        return table
    
    def _create_totals(self):
        """Create totals section."""
        data = [
            ['Sous-total:', f"{self.invoice.subtotal:,.0f} XAF"],
            ['TVA:', f"{self.invoice.tax_amount:,.0f} XAF"],
            ['Total:', f"{self.invoice.total_amount:,.0f} XAF"],
        ]
        table = Table(data, colWidths=[12*cm, 6*cm])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 14),
            ('LINEABOVE', (0, -1), (-1, -1), 2, colors.black),
        ]))
        return table
    
    def _create_footer(self):
        """Create invoice footer."""
        text = "Merci pour votre confiance !"
        return Paragraph(text, self.styles['Normal'])
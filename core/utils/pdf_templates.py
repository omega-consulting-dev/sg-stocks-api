from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm, mm
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from datetime import datetime
import os


class InvoicePDFGenerator:
    """Generate professional invoices in PDF with customizable settings."""
    
    def __init__(self, invoice):
        self.invoice = invoice
        self.styles = getSampleStyleSheet()
        
        # Load company settings
        from apps.main.models_settings import CompanySettings
        self.settings = CompanySettings.get_settings()
        
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles based on company settings."""
        primary_color = self.settings.primary_color
        secondary_color = self.settings.secondary_color
        text_color = self.settings.text_color
        
        # Style pour le titre de l'entreprise
        self.styles.add(ParagraphStyle(
            name='CompanyName',
            parent=self.styles['Title'],
            fontSize=24,
            textColor=colors.HexColor(primary_color),
            alignment=TA_LEFT,
            spaceAfter=6,
            fontName='Helvetica-Bold'
        ))
        
        # Style pour le slogan
        self.styles.add(ParagraphStyle(
            name='CompanySlogan',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#666666'),
            alignment=TA_LEFT,
            fontName='Helvetica-Oblique'
        ))
        
        # Style pour "FACTURE"
        self.styles.add(ParagraphStyle(
            name='InvoiceTitle',
            parent=self.styles['Title'],
            fontSize=20,
            textColor=colors.HexColor(secondary_color),
            alignment=TA_RIGHT,
            fontName='Helvetica-Bold'
        ))
    
    def generate(self, buffer):
        """Generate the invoice PDF."""
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        story = []
        
        # En-tête avec logo et info entreprise
        story.append(self._create_header())
        story.append(Spacer(1, 1*cm))
        
        # Ligne de séparation
        story.append(self._create_separator())
        story.append(Spacer(1, 0.8*cm))
        
        # Bloc avec infos facture et client côte à côte
        story.append(self._create_invoice_and_customer_info())
        story.append(Spacer(1, 1*cm))
        
        # Table des produits
        story.append(self._create_items_table())
        story.append(Spacer(1, 0.8*cm))
        
        # Totaux
        story.append(self._create_totals())
        story.append(Spacer(1, 1.5*cm))
        
        # Conditions de paiement
        story.append(self._create_payment_info())
        story.append(Spacer(1, 1*cm))
        
        # Pied de page
        story.append(self._create_footer())
        
        doc.build(story)
    
    def _create_header(self):
        """Create professional invoice header with company settings."""
        # Build company info text
        company_info_text = f'<b>{self.settings.company_name}</b><br/>'
        
        if self.settings.company_slogan:
            company_info_text += f'<font size=9 color="#666666">{self.settings.company_slogan}</font><br/>'
        
        contact_parts = []
        if self.settings.company_phone:
            contact_parts.append(f'Tél: {self.settings.company_phone}')
        if self.settings.company_email:
            contact_parts.append(f'Email: {self.settings.company_email}')
        
        if contact_parts:
            company_info_text += f'<font size=8 color="#999999">{" | ".join(contact_parts)}</font>'
        
        if self.settings.company_address:
            company_info_text += f'<br/><font size=8 color="#999999">{self.settings.company_address}</font>'
        
        if self.settings.invoice_header_text:
            company_info_text += f'<br/><font size=8 color="#666666">{self.settings.invoice_header_text}</font>'
        
        company_info = Paragraph(company_info_text, self.styles['CompanyName'])
        
        invoice_title = Paragraph(
            '<b>FACTURE</b><br/>'
            f'<font size=12>N° {self.invoice.invoice_number}</font>',
            self.styles['InvoiceTitle']
        )
        
        # Check if logo should be shown and exists
        elements = []
        if self.settings.show_logo_on_invoice and self.settings.logo:
            try:
                # Try to load and display logo
                logo_path = self.settings.logo.path
                if os.path.exists(logo_path):
                    logo = Image(logo_path, width=3*cm, height=3*cm, kind='proportional')
                    # Layout: logo | company info | invoice title
                    data = [[logo, company_info, invoice_title]]
                    table = Table(data, colWidths=[3.5*cm, 9*cm, 4.5*cm])
                else:
                    # No logo, just company info and invoice title
                    data = [[company_info, invoice_title]]
                    table = Table(data, colWidths=[10*cm, 7*cm])
            except Exception:
                # If logo fails, fall back to no logo layout
                data = [[company_info, invoice_title]]
                table = Table(data, colWidths=[10*cm, 7*cm])
        else:
            # No logo, just company info and invoice title
            data = [[company_info, invoice_title]]
            table = Table(data, colWidths=[10*cm, 7*cm])
        
        table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (-1, 0), (-1, 0), 'RIGHT'),
        ]))
        return table
    
    def _create_separator(self):
        """Create a horizontal separator line."""
        data = [['']]
        table = Table(data, colWidths=[17*cm])
        table.setStyle(TableStyle([
            ('LINEBELOW', (0, 0), (-1, -1), 2, colors.HexColor(self.settings.primary_color)),
        ]))
        return table
    
    def _create_invoice_and_customer_info(self):
        """Create invoice and customer info side by side."""
        customer = self.invoice.customer
        store = self.invoice.store
        
        # Bloc client (gauche)
        customer_data = [
            [Paragraph('<b>CLIENT</b>', self.styles['Heading3'])],
            [Paragraph(f'<b>{customer.name if customer else "N/A"}</b>', self.styles['Normal'])],
            [Paragraph(f'{customer.address if customer and customer.address else ""}', self.styles['Normal'])],
            [Paragraph(f'Tél: {customer.phone if customer and customer.phone else "N/A"}', self.styles['Normal'])],
            [Paragraph(f'Email: {customer.email if customer and customer.email else "N/A"}', self.styles['Normal'])],
        ]
        
        customer_table = Table(customer_data, colWidths=[8*cm])
        customer_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F5F6FA')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#003FD8')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#EEEEEE')),
        ]))
        
        # Bloc infos facture (droite)
        invoice_data = [
            [Paragraph('<b>INFORMATIONS</b>', self.styles['Heading3'])],
            [Paragraph(f'<b>Date d\'émission:</b> {self.invoice.invoice_date.strftime("%d/%m/%Y")}', self.styles['Normal'])],
            [Paragraph(f'<b>Date d\'échéance:</b> {self.invoice.due_date.strftime("%d/%m/%Y")}', self.styles['Normal'])],
            [Paragraph(f'<b>Magasin:</b> {store.name if store else "N/A"}', self.styles['Normal'])],
            [Paragraph(f'<b>Statut:</b> {self.invoice.get_status_display()}', self.styles['Normal'])],
        ]
        
        invoice_table = Table(invoice_data, colWidths=[8*cm])
        invoice_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F5F6FA')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#003FD8')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#EEEEEE')),
        ]))
        
        # Combiner les deux blocs
        main_data = [[customer_table, invoice_table]]
        main_table = Table(main_data, colWidths=[8.5*cm, 8.5*cm], spaceBefore=0, spaceAfter=0)
        main_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ]))
        
        return main_table
    
    def _create_items_table(self):
        """Create professional items table."""
        # En-tête
        data = [[
            Paragraph('<b>DÉSIGNATION</b>', self.styles['Normal']),
            Paragraph('<b>QTÉ</b>', self.styles['Normal']),
            Paragraph('<b>PRIX UNIT.</b>', self.styles['Normal']),
            Paragraph('<b>TVA</b>', self.styles['Normal']),
            Paragraph('<b>MONTANT HT</b>', self.styles['Normal']),
            Paragraph('<b>MONTANT TTC</b>', self.styles['Normal'])
        ]]
        
        # Lignes de produits
        for line in self.invoice.lines.all():
            subtotal_ht = float(line.subtotal_after_discount)
            total_ttc = float(line.total)
            
            data.append([
                Paragraph(line.description, self.styles['Normal']),
                Paragraph(f'{line.quantity}', self.styles['Normal']),
                Paragraph(f'{float(line.unit_price):,.0f} XAF', self.styles['Normal']),
                Paragraph(f'{line.tax_rate}%', self.styles['Normal']),
                Paragraph(f'{subtotal_ht:,.0f} XAF', self.styles['Normal']),
                Paragraph(f'<b>{total_ttc:,.0f} XAF</b>', self.styles['Normal'])
            ])
        
        table = Table(data, colWidths=[6*cm, 1.8*cm, 2.5*cm, 1.5*cm, 2.6*cm, 2.6*cm])
        table.setStyle(TableStyle([
            # En-tête
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(self.settings.primary_color)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            
            # Corps du tableau
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),      # Désignation à gauche
            ('ALIGN', (1, 1), (-1, -1), 'CENTER'),   # Reste au centre
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            
            # Bordures
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor(self.settings.primary_color)),
            
            # Lignes alternées
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9F9F9')]),
        ]))
        return table
    
    def _create_totals(self):
        """Create professional totals section."""
        discount = float(self.invoice.discount_amount) if self.invoice.discount_amount else 0
        subtotal = float(self.invoice.subtotal)
        tax = float(self.invoice.tax_amount)
        total = float(self.invoice.total_amount)
        paid = float(self.invoice.paid_amount)
        balance = float(self.invoice.balance_due)
        
        data = []
        
        if discount > 0:
            data.append(['Remise:', f'{discount:,.0f} XAF'])
        
        data.extend([
            ['Sous-total HT:', f'{subtotal:,.0f} XAF'],
            ['TVA (19.25%):', f'{tax:,.0f} XAF'],
            ['', ''],  # Ligne vide pour séparation
        ])
        
        # Total avec fond bleu
        total_data = [['TOTAL TTC:', f'{total:,.0f} XAF']]
        
        # Informations de paiement
        payment_data = [
            ['Montant payé:', f'{paid:,.0f} XAF'],
            ['Solde restant:', f'{balance:,.0f} XAF']
        ]
        
        # Table principale des totaux
        totals_table = Table(data, colWidths=[10*cm, 7*cm])
        totals_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        
        # Table du total
        total_table = Table(total_data, colWidths=[10*cm, 7*cm])
        total_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(self.settings.primary_color)),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 14),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ]))
        
        # Table des paiements
        payment_table = Table(payment_data, colWidths=[10*cm, 7*cm])
        payment_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor(self.settings.primary_color)),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 12),
        ]))
        
        # Combiner toutes les tables
        combined_data = [[totals_table], [total_table], [Spacer(1, 0.3*cm)], [payment_table]]
        combined_table = Table(combined_data, colWidths=[17*cm])
        
        return combined_table
    
    def _create_payment_info(self):
        """Create payment information section."""
        payment_term_display = {
            'immediate': 'Comptant',
            '15_days': '15 jours',
            '30_days': '30 jours',
            '60_days': '60 jours'
        }.get(self.invoice.payment_term, 'Comptant')
        
        info_text = f'<b>Conditions de paiement:</b> {payment_term_display}'
        
        if self.invoice.notes:
            info_text += f'<br/><b>Notes:</b> {self.invoice.notes}'
        
        para = Paragraph(info_text, self.styles['Normal'])
        
        data = [[para]]
        table = Table(data, colWidths=[17*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F5F6FA')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#EEEEEE')),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))
        return table
    
    def _create_footer(self):
        """Create professional invoice footer with company settings."""
        footer_text = f'<para alignment="center">'
        footer_text += f'<font size=10 color="{self.settings.primary_color}"><b>{self.settings.invoice_footer_text}</b></font><br/>'
        
        if self.settings.invoice_footer_note:
            footer_text += f'<font size=8 color="#666666">{self.settings.invoice_footer_note}</font><br/>'
        
        footer_text += f'<font size=8 color="#999999">Cette facture est générée électroniquement par {self.settings.company_name}</font><br/>'
        
        if self.settings.company_email:
            footer_text += f'<font size=8 color="#999999">En cas de questions, contactez-nous à {self.settings.company_email}</font>'
        
        footer_text += '</para>'
        return Paragraph(footer_text, self.styles['Normal'])
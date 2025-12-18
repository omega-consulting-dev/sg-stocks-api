from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm, mm
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from datetime import datetime
import os


class ReportPDFGenerator:
    """Generate professional reports in PDF with customizable settings."""
    
    def __init__(self, report_type, start_date, end_date, data):
        self.report_type = report_type
        self.start_date = start_date
        self.end_date = end_date
        self.data = data
        self.styles = getSampleStyleSheet()
        
        # Load company settings
        from apps.main.models_settings import CompanySettings
        self.settings = CompanySettings.get_settings()
        
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles based on company settings."""
        primary_color = self.settings.primary_color
        secondary_color = self.settings.secondary_color
        
        # Style pour le titre de l'entreprise
        self.styles.add(ParagraphStyle(
            name='CompanyName',
            parent=self.styles['Title'],
            fontSize=22,
            textColor=colors.HexColor(primary_color),
            alignment=TA_CENTER,
            spaceAfter=6,
            fontName='Helvetica-Bold'
        ))
        
        # Style pour le titre du rapport
        self.styles.add(ParagraphStyle(
            name='ReportTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor(secondary_color),
            alignment=TA_CENTER,
            spaceAfter=12,
            fontName='Helvetica-Bold'
        ))
        
        # Style pour la période
        self.styles.add(ParagraphStyle(
            name='Period',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#666666'),
            alignment=TA_CENTER,
            spaceAfter=20
        ))
    
    def _create_header(self):
        """Create report header with company info."""
        header_data = []
        
        # Company name
        company_name = Paragraph(self.settings.company_name, self.styles['CompanyName'])
        header_data.append([company_name])
        
        # Company slogan
        if self.settings.company_slogan:
            slogan_style = ParagraphStyle(
                name='Slogan',
                parent=self.styles['Normal'],
                fontSize=10,
                textColor=colors.HexColor('#666666'),
                alignment=TA_CENTER,
                fontName='Helvetica-Oblique'
            )
            slogan = Paragraph(self.settings.company_slogan, slogan_style)
            header_data.append([slogan])
        
        header_table = Table(header_data, colWidths=[17*cm])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        return header_table
    
    def _create_separator(self):
        """Create a visual separator line."""
        separator_data = [['']]
        separator = Table(separator_data, colWidths=[17*cm])
        separator.setStyle(TableStyle([
            ('LINEABOVE', (0, 0), (-1, -1), 2, colors.HexColor(self.settings.primary_color)),
        ]))
        return separator
    
    def _create_report_info(self):
        """Create report title and period info."""
        titles = {
            'profit_loss': 'COMPTE DE RÉSULTAT',
            'sales': 'RAPPORT DES VENTES',
            'expenses': 'RAPPORT DES DÉPENSES',
            'inventory': 'RAPPORT D\'INVENTAIRE'
        }
        
        title_text = titles.get(self.report_type, 'RAPPORT')
        title = Paragraph(title_text, self.styles['ReportTitle'])
        
        period_text = f"Période: du {self.start_date.strftime('%d/%m/%Y')} au {self.end_date.strftime('%d/%m/%Y')}"
        period = Paragraph(period_text, self.styles['Period'])
        
        info_data = [[title], [period]]
        info_table = Table(info_data, colWidths=[17*cm])
        info_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        
        return info_table
    
    def _create_data_table(self):
        """Create the main data table."""
        # Style for table
        table_style = TableStyle([
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563eb')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            
            # Body
            ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
        ])
        
        # Align right for amounts
        if len(self.data) > 0 and len(self.data[0]) > 1:
            table_style.add('ALIGN', (-1, 1), (-1, -1), 'RIGHT')
        
        # Special styling for profit/loss report
        if self.report_type == 'profit_loss' and len(self.data) > 4:
            # Highlight the result row
            table_style.add('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#dbeafe'))
            table_style.add('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold')
            table_style.add('FONTSIZE', (0, -1), (-1, -1), 11)
            table_style.add('TOPPADDING', (0, -1), (-1, -1), 12)
            table_style.add('BOTTOMPADDING', (0, -1), (-1, -1), 12)
        
        table = Table(self.data, repeatRows=1)
        table.setStyle(table_style)
        
        return table
    
    def _create_footer(self):
        """Create footer with generation date."""
        footer_text = f"Rapport généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}"
        footer_style = ParagraphStyle(
            name='Footer',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.grey,
            alignment=TA_CENTER
        )
        footer = Paragraph(footer_text, footer_style)
        
        # Company footer info
        footer_info = []
        if self.settings.company_address:
            footer_info.append(self.settings.company_address)
        if self.settings.company_phone:
            footer_info.append(f"Tél: {self.settings.company_phone}")
        if self.settings.company_email:
            footer_info.append(f"Email: {self.settings.company_email}")
        
        if footer_info:
            footer_info_text = " | ".join(footer_info)
            footer_info_para = Paragraph(footer_info_text, footer_style)
            
            footer_data = [[footer], [Spacer(1, 0.2*cm)], [footer_info_para]]
        else:
            footer_data = [[footer]]
        
        footer_table = Table(footer_data, colWidths=[17*cm])
        footer_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        
        return footer_table
    
    def generate(self, buffer):
        """Generate the report PDF."""
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=1.5*cm,
            bottomMargin=1.5*cm
        )
        story = []
        
        # En-tête avec info entreprise
        story.append(self._create_header())
        story.append(Spacer(1, 0.5*cm))
        
        # Ligne de séparation
        story.append(self._create_separator())
        story.append(Spacer(1, 0.8*cm))
        
        # Info rapport (titre et période)
        story.append(self._create_report_info())
        story.append(Spacer(1, 0.8*cm))
        
        # Table des données
        story.append(self._create_data_table())
        story.append(Spacer(1, 1*cm))
        
        # Pied de page
        story.append(self._create_footer())
        
        doc.build(story)

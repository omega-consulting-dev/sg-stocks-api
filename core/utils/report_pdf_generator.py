"""
Report PDF Generator utility
"""
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER, TA_RIGHT


class ReportPDFGenerator:
    """Generate PDF reports with professional formatting."""
    
    def __init__(self):
        self.buffer = BytesIO()
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles."""
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1e3a8a'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#1e40af'),
            spaceAfter=12,
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='RightAlign',
            parent=self.styles['Normal'],
            alignment=TA_RIGHT
        ))
    
    def generate_report(self, data):
        """Generate a PDF report based on report type."""
        doc = SimpleDocTemplate(
            self.buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        
        story = []
        
        # Title
        title = Paragraph(data.get('type', 'Rapport'), self.styles['CustomTitle'])
        story.append(title)
        story.append(Spacer(1, 12))
        
        # Period
        period = Paragraph(f"<b>Période:</b> {data.get('period', 'N/A')}", self.styles['Normal'])
        story.append(period)
        story.append(Spacer(1, 20))
        
        # Generate table based on report type
        report_type = data.get('type', '')
        
        if 'Compte de Résultat' in report_type or 'Profit' in report_type:
            story.extend(self._generate_profit_loss_table(data))
        elif 'Vente' in report_type or 'Sales' in report_type:
            story.extend(self._generate_sales_table(data))
        elif 'Dépenses' in report_type or 'Expenses' in report_type:
            story.extend(self._generate_expenses_table(data))
        elif 'Inventaire' in report_type or 'Inventory' in report_type:
            story.extend(self._generate_inventory_table(data))
        
        doc.build(story)
        self.buffer.seek(0)
        return self.buffer
    
    def _generate_profit_loss_table(self, data):
        """Generate profit & loss table."""
        elements = []
        
        # Revenue section
        elements.append(Paragraph('Revenus', self.styles['CustomHeading']))
        
        revenue = data.get('revenue', {})
        revenue_data = [
            ['Description', 'Montant (FCFA)'],
            ['Ventes', f"{revenue.get('sales', 0):,.0f}"],
            ['Factures', f"{revenue.get('invoices', 0):,.0f}"],
            ['Total Revenus', f"{revenue.get('total', 0):,.0f}"]
        ]
        
        revenue_table = Table(revenue_data, colWidths=[10*cm, 6*cm])
        revenue_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#3b82f6')),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.whitesmoke),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey)
        ]))
        
        elements.append(revenue_table)
        elements.append(Spacer(1, 20))
        
        # Expenses section
        elements.append(Paragraph('Dépenses', self.styles['CustomHeading']))
        
        expenses_data = [
            ['Description', 'Montant (FCFA)'],
            ['Total Dépenses', f"{data.get('expenses', 0):,.0f}"]
        ]
        
        expenses_table = Table(expenses_data, colWidths=[10*cm, 6*cm])
        expenses_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dc2626')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey)
        ]))
        
        elements.append(expenses_table)
        elements.append(Spacer(1, 20))
        
        # Profit section
        elements.append(Paragraph('Résultat', self.styles['CustomHeading']))
        
        profit = data.get('profit', 0)
        profit_color = colors.HexColor('#10b981') if profit >= 0 else colors.HexColor('#dc2626')
        
        profit_data = [
            ['Description', 'Montant (FCFA)'],
            ['Bénéfice Net' if profit >= 0 else 'Perte Nette', f"{profit:,.0f}"]
        ]
        
        profit_table = Table(profit_data, colWidths=[10*cm, 6*cm])
        profit_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#64748b')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), profit_color),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.whitesmoke),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (-1, -1), 14),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey)
        ]))
        
        elements.append(profit_table)
        
        return elements
    
    def _generate_sales_table(self, data):
        """Generate sales table."""
        elements = []
        
        sales = data.get('sales', [])
        if not sales:
            elements.append(Paragraph('Aucune vente pour cette période', self.styles['Normal']))
            return elements
        
        table_data = [['Date', 'Montant (FCFA)', 'Vendeur', 'Mode Paiement']]
        
        total = 0
        for sale in sales:
            table_data.append([
                sale.get('sale_date', '').strftime('%d/%m/%Y') if isinstance(sale.get('sale_date'), object) else str(sale.get('sale_date', '')),
                f"{sale.get('total_amount', 0):,.0f}",
                sale.get('user__username', 'N/A'),
                sale.get('payment_method', 'N/A')
            ])
            total += sale.get('total_amount', 0)
        
        table_data.append(['TOTAL', f"{total:,.0f}", '', ''])
        
        table = Table(table_data, colWidths=[3*cm, 4*cm, 4*cm, 4*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#3b82f6')),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.whitesmoke),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey)
        ]))
        
        elements.append(table)
        return elements
    
    def _generate_expenses_table(self, data):
        """Generate expenses table."""
        elements = []
        
        expenses = data.get('expenses', [])
        if not expenses:
            elements.append(Paragraph('Aucune dépense pour cette période', self.styles['Normal']))
            return elements
        
        table_data = [['Date', 'Montant (FCFA)', 'Catégorie', 'Description']]
        
        total = 0
        for expense in expenses:
            table_data.append([
                expense.get('expense_date', '').strftime('%d/%m/%Y') if isinstance(expense.get('expense_date'), object) else str(expense.get('expense_date', '')),
                f"{expense.get('amount', 0):,.0f}",
                expense.get('category__name', 'N/A'),
                expense.get('description', '')[:30]
            ])
            total += expense.get('amount', 0)
        
        table_data.append(['TOTAL', f"{total:,.0f}", '', ''])
        
        table = Table(table_data, colWidths=[3*cm, 3.5*cm, 4*cm, 5*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dc2626')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#ef4444')),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.whitesmoke),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey)
        ]))
        
        elements.append(table)
        return elements
    
    def _generate_inventory_table(self, data):
        """Generate inventory table."""
        elements = []
        
        stocks = data.get('stocks', [])
        if not stocks:
            elements.append(Paragraph('Aucun stock disponible', self.styles['Normal']))
            return elements
        
        table_data = [['Produit', 'Quantité', 'Prix Unitaire (FCFA)', 'Valeur Totale (FCFA)']]
        
        total_value = 0
        for stock in stocks:
            quantity = stock.get('quantity', 0)
            unit_price = stock.get('unit_price', 0)
            value = quantity * unit_price
            
            table_data.append([
                stock.get('product__name', 'N/A'),
                str(quantity),
                f"{unit_price:,.0f}",
                f"{value:,.0f}"
            ])
            total_value += value
        
        table_data.append(['TOTAL', '', '', f"{total_value:,.0f}"])
        
        table = Table(table_data, colWidths=[6*cm, 3*cm, 3.5*cm, 3.5*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0891b2')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#06b6d4')),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.whitesmoke),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey)
        ]))
        
        elements.append(table)
        return elements

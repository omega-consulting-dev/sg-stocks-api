from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.db.models import Sum, Count, Avg, F, Q, Case, When, DecimalField
from django.db.models.functions import TruncDate, TruncMonth
from django.utils import timezone
from django.http import HttpResponse
from datetime import timedelta, datetime
from io import BytesIO

# PDF generation
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

# Excel generation
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill

from apps.sales.models import Sale
from apps.products.models import Product
from apps.inventory.models import Stock
from apps.accounts.models import User
from apps.cashbox.models import CashMovement
from apps.loans.models import Loan
from apps.expenses.models import Expense


class DashboardViewSet(viewsets.ViewSet):
    """
    ViewSet for analytics and dashboard data with user-based filtering.
    - Super admin/Manager (access_scope='all'): voit toutes les statistiques
    - Caissier (access_scope='own'): voit uniquement ses propres statistiques
    """
    permission_classes = [IsAuthenticated]
    
    def _get_sales_queryset(self, user):
        """Helper to get filtered sales queryset based on user role."""
        queryset = Sale.objects.all()
        
        # Super admin voit tout
        if user.is_superuser:
            return queryset
        
        # Vérifier le scope d'accès du rôle
        if hasattr(user, 'role') and user.role:
            if user.role.access_scope == 'all':
                return queryset
            elif user.role.access_scope == 'assigned':
                assigned_stores = user.assigned_stores.all()
                if assigned_stores.exists():
                    return queryset.filter(store__in=assigned_stores)
                else:
                    return queryset.none()
            elif user.role.access_scope == 'own':
                return queryset.filter(created_by=user)
        
        # Par défaut, filtrer par créateur
        return queryset.filter(created_by=user)
    
    def _get_expenses_queryset(self, user):
        """Helper to get filtered expenses queryset based on user role."""
        queryset = Expense.objects.all()
        
        if user.is_superuser:
            return queryset
        
        if hasattr(user, 'role') and user.role:
            if user.role.access_scope == 'all':
                return queryset
            elif user.role.access_scope == 'assigned':
                assigned_stores = user.assigned_stores.all()
                if assigned_stores.exists():
                    return queryset.filter(store__in=assigned_stores)
                else:
                    return queryset.none()
            elif user.role.access_scope == 'own':
                return queryset.filter(created_by=user)
        
        return queryset.filter(created_by=user)
    
    @action(detail=False, methods=['get'])
    def overview(self, request):
        """Main dashboard overview with user-specific data."""
        user = request.user
        today = timezone.now().date()
        month_start = today.replace(day=1)
        year_start = today.replace(month=1, day=1)
        
        # Get filtered querysets
        sales_qs = self._get_sales_queryset(user)
        expenses_qs = self._get_expenses_queryset(user)
        
        # Sales statistics
        sales_today = sales_qs.filter(sale_date=today, status='confirmed').aggregate(
            total=Sum('total_amount'),
            count=Count('id')
        )
        
        sales_month = sales_qs.filter(
            sale_date__gte=month_start,
            status='confirmed'
        ).aggregate(
            total=Sum('total_amount'),
            count=Count('id')
        )
        
        sales_year = sales_qs.filter(
            sale_date__gte=year_start,
            status='confirmed'
        ).aggregate(
            total=Sum('total_amount'),
            count=Count('id')
        )
        
        # Stock statistics
        stock_stats = {
            'total_products': Product.objects.filter(is_active=True).count(),
            'low_stock': Stock.objects.filter(
                quantity__lt=F('product__minimum_stock')
            ).distinct().count(),
            'out_of_stock': Stock.objects.filter(quantity=0).count(),
            'total_stock_value': Stock.objects.aggregate(
                total=Sum(F('quantity') * F('product__cost_price'))
            )['total'] or 0,
        }
        
        # Customer statistics
        customer_stats = {
            'total': User.objects.filter(user_type='customer', is_active=True).count(),
            'new_this_month': User.objects.filter(
                user_type='customer',
                date_joined__gte=month_start
            ).count(),
        }
        
        # Cash statistics
        cash_balance = CashMovement.objects.aggregate(
            total=Sum(Case(
                When(movement_type='in', then='amount'),
                When(movement_type='out', then=-F('amount')),
                output_field=DecimalField()
            ))
        )['total'] or 0
        
        # Pending items (filtered by user)
        pending = {
            'sales': sales_qs.filter(status='draft').count(),
            'payments': sales_qs.filter(
                status='confirmed',
                payment_status__in=['unpaid', 'partial']
            ).count(),
            'expenses': expenses_qs.filter(status='pending').count(),
        }
        
        data = {
            'sales': {
                'today': {
                    'amount': float(sales_today['total'] or 0),
                    'count': sales_today['count']
                },
                'this_month': {
                    'amount': float(sales_month['total'] or 0),
                    'count': sales_month['count']
                },
                'this_year': {
                    'amount': float(sales_year['total'] or 0),
                    'count': sales_year['count']
                }
            },
            'stock': stock_stats,
            'customers': customer_stats,
            'cash': {
                'balance': float(cash_balance)
            },
            'pending': pending
        }
        
        return Response(data)
    
    @action(detail=False, methods=['get'])
    def sales_chart(self, request):
        """Sales chart data over time (filtered by user)."""
        user = request.user
        period = request.query_params.get('period', 'month')  # day, week, month, year
        
        today = timezone.now().date()
        
        if period == 'day':
            start_date = today - timedelta(days=30)
            trunc_func = TruncDate
        elif period == 'week':
            start_date = today - timedelta(weeks=12)
            trunc_func = TruncDate
        elif period == 'month':
            start_date = today - timedelta(days=365)
            trunc_func = TruncMonth
        else:
            start_date = today - timedelta(days=365)
            trunc_func = TruncMonth
        
        # Get filtered sales queryset
        sales_qs = self._get_sales_queryset(user)
        
        sales_data = sales_qs.filter(
            sale_date__gte=start_date,
            status='confirmed'
        ).annotate(
            period=trunc_func('sale_date')
        ).values('period').annotate(
            total_amount=Sum('total_amount'),
            total_sales=Count('id')
        ).order_by('period')
        
        return Response(list(sales_data))
    
    @action(detail=False, methods=['get'])
    def top_products(self, request):
        """Top selling products (filtered by user)."""
        user = request.user
        limit = int(request.query_params.get('limit', 10))
        
        from apps.sales.models import SaleLine
        
        # Get filtered sales queryset
        sales_qs = self._get_sales_queryset(user)
        
        top_products = SaleLine.objects.filter(
            sale__in=sales_qs,
            sale__status='confirmed',
            line_type='product'
        ).values(
            'product__id',
            'product__name',
            'product__reference'
        ).annotate(
            total_quantity=Sum('quantity'),
            total_amount=Sum(F('quantity') * F('unit_price')),
            sales_count=Count('sale', distinct=True)
        ).order_by('-total_amount')[:limit]
        
        return Response(list(top_products))
    
    @action(detail=False, methods=['get'])
    def top_customers(self, request):
        """Top customers by revenue (filtered by user)."""
        user = request.user
        limit = int(request.query_params.get('limit', 10))
        
        # Get filtered sales queryset
        sales_qs = self._get_sales_queryset(user)
        
        top_customers = sales_qs.filter(
            status='confirmed'
        ).values(
            'customer__id',
            'customer__username',
            customer_name=F('customer__first_name')
        ).annotate(
            total_amount=Sum('total_amount'),
            sales_count=Count('id'),
            avg_order=Avg('total_amount')
        ).order_by('-total_amount')[:limit]
        
        return Response(list(top_customers))
    
    @action(detail=False, methods=['get'])
    def revenue_by_category(self, request):
        """Revenue breakdown by product category."""
        from apps.sales.models import SaleLine
        
        category_revenue = SaleLine.objects.filter(
            sale__status='confirmed',
            line_type='product'
        ).values(
            'product__category__id',
            'product__category__name'
        ).annotate(
            total_revenue=Sum(F('quantity') * F('unit_price')),
            total_quantity=Sum('quantity')
        ).order_by('-total_revenue')
        
        return Response(list(category_revenue))
    
    @action(detail=False, methods=['get'])
    def cash_flow(self, request):
        """Cash flow analysis."""
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now().date() - timedelta(days=days)
        
        cash_movements = CashMovement.objects.filter(
            created_at__date__gte=start_date
        ).annotate(
            date=TruncDate('created_at')
        ).values('date', 'movement_type').annotate(
            total=Sum('amount')
        ).order_by('date')
        
        # Structure data by date
        result = {}
        for movement in cash_movements:
            date_str = str(movement['date'])
            if date_str not in result:
                result[date_str] = {'date': date_str, 'in': 0, 'out': 0}
            
            if movement['movement_type'] == 'in':
                result[date_str]['in'] = float(movement['total'])
            else:
                result[date_str]['out'] = float(movement['total'])
        
        return Response(list(result.values()))
    
    @action(detail=False, methods=['get'])
    def inventory_value(self, request):
        """Inventory value by store."""
        inventory_by_store = Stock.objects.values(
            'store__id',
            'store__name'
        ).annotate(
            total_value=Sum(F('quantity') * F('product__cost_price')),
            total_products=Count('product', distinct=True),
            total_quantity=Sum('quantity')
        ).order_by('-total_value')
        
        return Response(list(inventory_by_store))
    
    @action(detail=False, methods=['get'])
    def financial_summary(self, request):
        """Financial summary including loans, expenses, etc."""
        month_start = timezone.now().date().replace(day=1)
        
        # Loans
        loans_summary = {
            'total_principal': Loan.objects.aggregate(
                total=Sum('principal_amount')
            )['total'] or 0,
            'total_debt': Loan.objects.filter(
                status='active'
            ).aggregate(
                total=Sum(F('total_amount') - F('paid_amount'))
            )['total'] or 0,
            'monthly_payment': Loan.objects.filter(
                status='active'
            ).aggregate(
                total=Sum(F('total_amount') / F('duration_months'))
            )['total'] or 0,
        }
        
        # Expenses
        expenses_summary = {
            'this_month': Expense.objects.filter(
                expense_date__gte=month_start,
                status='paid'
            ).aggregate(total=Sum('amount'))['total'] or 0,
            'pending': Expense.objects.filter(
                status__in=['pending', 'approved']
            ).aggregate(total=Sum('amount'))['total'] or 0,
        }
        
        # Revenue
        revenue_summary = {
            'this_month': Sale.objects.filter(
                sale_date__gte=month_start,
                status='confirmed'
            ).aggregate(total=Sum('total_amount'))['total'] or 0,
        }
        
        # Calculate profit
        profit = float(revenue_summary['this_month']) - float(expenses_summary['this_month'])
        
        return Response({
            'loans': loans_summary,
            'expenses': expenses_summary,
            'revenue': revenue_summary,
            'profit': profit
        })
    
    @action(detail=False, methods=['get'], url_path='reporting-stats')
    def reporting_stats(self, request):
        """Get statistics for reporting page."""
        from apps.invoicing.models import Invoice
        
        # Total invoices
        total_invoices = Invoice.objects.filter(status='paid').count()
        
        # Total expenses (paid and approved)
        total_expenses = Expense.objects.filter(
            Q(status='paid') | Q(status='approved')
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Total sales
        total_sales = Sale.objects.filter(
            status='confirmed'
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        return Response({
            'total_invoices': total_invoices,
            'total_expenses': float(total_expenses),
            'total_sales': float(total_sales)
        })
    
    @action(detail=False, methods=['get'], url_path='generate-report-data')
    def generate_report_data(self, request):
        """Generate report data with expenses and sales list."""
        from django.db.models import Sum
        
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        
        if not start_date_str or not end_date_str:
            return Response({'error': 'Les dates sont requises'}, status=400)
        
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response({'error': 'Format de date invalide'}, status=400)
        
        # Récupérer les charges
        expenses = Expense.objects.filter(
            expense_date__gte=start_date,
            expense_date__lte=end_date,
            status__in=['paid', 'approved']
        ).select_related('category')
        
        expenses_data = []
        for exp in expenses:
            expenses_data.append({
                'reference': exp.reference if hasattr(exp, 'reference') else f"EXP-{exp.id}",
                'description': exp.description or '',
                'category_name': exp.category.name if exp.category else 'Divers',
                'amount': float(exp.amount),
                'expense_date': exp.expense_date.strftime('%d/%m/%Y')
            })
        
        # Récupérer les ventes
        sales = Sale.objects.filter(
            sale_date__gte=start_date,
            sale_date__lte=end_date,
            status='confirmed'
        ).select_related('customer')
        
        sales_data = []
        for sale in sales:
            # Get product name from sale items
            product_names = []
            if hasattr(sale, 'items'):
                for item in sale.items.all()[:3]:  # Limiter à 3 produits
                    if hasattr(item, 'product') and item.product:
                        product_names.append(item.product.name)
            
            product_display = ', '.join(product_names) if product_names else 'Vente'
            
            sales_data.append({
                'sale_number': sale.sale_number if hasattr(sale, 'sale_number') else f"VNT-{sale.id}",
                'product_name': product_display,
                'description': f"Vente {sale.customer.name if sale.customer else 'client'}",
                'total_amount': float(sale.total_amount),
                'sale_date': sale.sale_date.strftime('%d/%m/%Y')
            })
        
        return Response({
            'expenses': expenses_data,
            'sales': sales_data
        })
    
    @action(detail=False, methods=['post'], url_path='export-report')
    def export_report(self, request):
        """Export report as PDF or Excel file with expenses and sales."""
        start_date_str = request.data.get('start_date')
        end_date_str = request.data.get('end_date')
        format_type = request.data.get('format', 'pdf')
        
        if not start_date_str or not end_date_str:
            return Response({'error': 'Les dates sont requises'}, status=400)
        
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response({'error': 'Format de date invalide'}, status=400)
        
        # Récupérer les charges
        expenses = Expense.objects.filter(
            expense_date__gte=start_date,
            expense_date__lte=end_date,
            status__in=['paid', 'approved']
        ).select_related('category')
        
        expenses_data = []
        total_expenses = 0
        for exp in expenses:
            ref = exp.reference if hasattr(exp, 'reference') else f"EXP-{exp.id}"
            designation = exp.category.name if exp.category else 'Divers'
            amount = float(exp.amount)
            expenses_data.append([ref, designation, amount])
            total_expenses += amount
        
        # Récupérer les ventes
        sales = Sale.objects.filter(
            sale_date__gte=start_date,
            sale_date__lte=end_date,
            status='confirmed'
        ).select_related('customer')
        
        sales_data = []
        total_sales = 0
        for sale in sales:
            numero = sale.sale_number if hasattr(sale, 'sale_number') else f"VNT-{sale.id}"
            
            # Get product names
            product_names = []
            if hasattr(sale, 'items'):
                for item in sale.items.all()[:3]:
                    if hasattr(item, 'product') and item.product:
                        product_names.append(item.product.name)
            ref = ', '.join(product_names) if product_names else 'Vente'
            
            amount = float(sale.total_amount)
            sales_data.append([numero, ref, amount])
            total_sales += amount
        
        # Calculer le résultat
        net_profit = total_sales - total_expenses
        
        period = f"du {start_date.strftime('%d/%m/%Y')} au {end_date.strftime('%d/%m/%Y')}"
        
        # Generate PDF
        if format_type == 'pdf':
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
            elements = []
            
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=20,
                textColor=colors.HexColor('#1a1a1a'),
                spaceAfter=5,
                alignment=1
            )
            subtitle_style = ParagraphStyle(
                'Subtitle',
                parent=styles['Normal'],
                fontSize=12,
                textColor=colors.HexColor('#666666'),
                spaceAfter=20,
                alignment=1
            )
            section_style = ParagraphStyle(
                'Section',
                parent=styles['Heading2'],
                fontSize=14,
                textColor=colors.whitesmoke,
                backColor=colors.HexColor('#1f2937'),
                spaceAfter=10,
                spaceBefore=10,
                leftIndent=10,
                rightIndent=10
            )
            
            # Titre
            elements.append(Paragraph("Reporting Mensuel", title_style))
            elements.append(Paragraph(f"Période {period}", subtitle_style))
            elements.append(Spacer(1, 10))
            
            # Tableau des Charges
            elements.append(Paragraph("Charges", section_style))
            charges_data = [['Réf', 'Désignation', 'Montant']]
            for exp in expenses_data:
                charges_data.append([exp[0], exp[1], f"{exp[2]:,.0f}"])
            charges_data.append(['', 'Total Charges', f"{total_expenses:,.0f}"])
            
            charges_table = Table(charges_data, colWidths=[80, 250, 120])
            charges_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#374151')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('TOPPADDING', (0, 0), (-1, 0), 10),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#1f2937')),
                ('TEXTCOLOR', (0, -1), (-1, -1), colors.whitesmoke),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d1d5db'))
            ]))
            elements.append(charges_table)
            elements.append(Spacer(1, 15))
            
            # Tableau des Ventes
            elements.append(Paragraph("Ventes", section_style))
            ventes_data = [['Numéro', 'Réf', 'Montant']]
            for sale in sales_data:
                ventes_data.append([sale[0], sale[1], f"{sale[2]:,.0f}"])
            ventes_data.append(['', 'Total Produits', f"{total_sales:,.0f}"])
            
            ventes_table = Table(ventes_data, colWidths=[100, 230, 120])
            ventes_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#374151')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('TOPPADDING', (0, 0), (-1, 0), 10),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#1f2937')),
                ('TEXTCOLOR', (0, -1), (-1, -1), colors.whitesmoke),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d1d5db'))
            ]))
            elements.append(ventes_table)
            elements.append(Spacer(1, 15))
            
            # Résultat
            result_color = colors.HexColor('#10b981') if net_profit >= 0 else colors.HexColor('#ef4444')
            result_data = [
                ['Résultat de la période', ''],
                ['Bénéfice', f"{net_profit:,.0f} FCFA"]
            ]
            result_table = Table(result_data, colWidths=[300, 150])
            result_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 14),
                ('FONTNAME', (0, 1), (0, 1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (0, 1), 10),
                ('FONTNAME', (1, 1), (1, 1), 'Helvetica-Bold'),
                ('FONTSIZE', (1, 1), (1, 1), 18),
                ('TEXTCOLOR', (1, 1), (1, 1), result_color),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10)
            ]))
            elements.append(result_table)
            elements.append(Spacer(1, 15))
            
            # Informations complémentaires
            info_data = [
                ['Informations complémentaires'],
                [f"Nombre des charges: {len(expenses_data)}"],
                [f"Services des produits: {len(sales_data)}"],
                [f"Ce rapport est établi pour la période {period}. La période représente un bénéfice de {net_profit:,.0f} FCFA."]
            ]
            info_table = Table(info_data, colWidths=[450])
            info_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#1f2937')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('LEFTPADDING', (0, 0), (-1, -1), 10)
            ]))
            elements.append(info_table)
            
            doc.build(elements)
            buffer.seek(0)
            
            response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="rapport_{start_date}_{end_date}.pdf"'
            return response
        
        # Generate Excel
        else:
            wb = Workbook()
            ws = wb.active
            ws.title = "Reporting"
            
            # Styles
            title_font = Font(name='Arial', size=16, bold=True)
            subtitle_font = Font(name='Arial', size=10, color='666666')
            header_font = Font(name='Arial', size=11, bold=True, color='FFFFFF')
            header_fill = PatternFill(start_color='374151', end_color='374151', fill_type='solid')
            total_fill = PatternFill(start_color='1f2937', end_color='1f2937', fill_type='solid')
            total_font = Font(name='Arial', size=10, bold=True, color='FFFFFF')
            info_fill = PatternFill(start_color='1f2937', end_color='1f2937', fill_type='solid')
            info_font = Font(name='Arial', size=9, color='FFFFFF')
            
            row = 1
            
            # Titre
            ws.merge_cells(f'A{row}:C{row}')
            cell = ws[f'A{row}']
            cell.value = "Reporting Mensuel"
            cell.font = title_font
            cell.alignment = Alignment(horizontal='center')
            row += 1
            
            # Période
            ws.merge_cells(f'A{row}:C{row}')
            cell = ws[f'A{row}']
            cell.value = f"Période {period}"
            cell.font = subtitle_font
            cell.alignment = Alignment(horizontal='center')
            row += 2
            
            # Charges
            ws.merge_cells(f'A{row}:C{row}')
            cell = ws[f'A{row}']
            cell.value = "Charges"
            cell.font = header_font
            cell.fill = header_fill
            row += 1
            
            # Headers Charges
            headers_charges = ['Réf', 'Désignation', 'Montant']
            for col_idx, header in enumerate(headers_charges, start=1):
                cell = ws.cell(row=row, column=col_idx)
                cell.value = header
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal='center')
            row += 1
            
            # Data Charges
            for exp in expenses_data:
                ws.cell(row=row, column=1, value=exp[0])
                ws.cell(row=row, column=2, value=exp[1])
                ws.cell(row=row, column=3, value=exp[2]).number_format = '#,##0'
                row += 1
            
            # Total Charges
            ws.cell(row=row, column=2, value="Total Charges").font = total_font
            ws.cell(row=row, column=2).fill = total_fill
            ws.cell(row=row, column=3, value=total_expenses).number_format = '#,##0'
            ws.cell(row=row, column=3).font = total_font
            ws.cell(row=row, column=3).fill = total_fill
            row += 2
            
            # Ventes
            ws.merge_cells(f'A{row}:C{row}')
            cell = ws[f'A{row}']
            cell.value = "Ventes"
            cell.font = header_font
            cell.fill = header_fill
            row += 1
            
            # Headers Ventes
            headers_ventes = ['Numéro', 'Réf', 'Montant']
            for col_idx, header in enumerate(headers_ventes, start=1):
                cell = ws.cell(row=row, column=col_idx)
                cell.value = header
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal='center')
            row += 1
            
            # Data Ventes
            for sale in sales_data:
                ws.cell(row=row, column=1, value=sale[0])
                ws.cell(row=row, column=2, value=sale[1])
                ws.cell(row=row, column=3, value=sale[2]).number_format = '#,##0'
                row += 1
            
            # Total Ventes
            ws.cell(row=row, column=2, value="Total Produits").font = total_font
            ws.cell(row=row, column=2).fill = total_fill
            ws.cell(row=row, column=3, value=total_sales).number_format = '#,##0'
            ws.cell(row=row, column=3).font = total_font
            ws.cell(row=row, column=3).fill = total_fill
            row += 2
            
            # Résultat
            result_color = '10b981' if net_profit >= 0 else 'ef4444'
            result_fill = PatternFill(start_color=result_color, end_color=result_color, fill_type='solid')
            result_font_styled = Font(name='Arial', size=14, bold=True, color='FFFFFF')
            
            ws.merge_cells(f'A{row}:B{row}')
            cell = ws[f'A{row}']
            cell.value = "Résultat de la période"
            cell.font = Font(name='Arial', size=12, bold=True)
            row += 1
            
            ws.cell(row=row, column=1, value="Bénéfice")
            ws.cell(row=row, column=2, value=f"{net_profit:,.0f} FCFA").font = result_font_styled
            ws.cell(row=row, column=2).fill = result_fill
            row += 2
            
            # Informations complémentaires
            ws.merge_cells(f'A{row}:C{row}')
            cell = ws[f'A{row}']
            cell.value = "Informations complémentaires"
            cell.font = info_font
            cell.fill = info_fill
            row += 1
            
            info_lines = [
                f"Nombre des charges: {len(expenses_data)}",
                f"Services des produits: {len(sales_data)}",
                f"Ce rapport est établi pour la période {period}. La période représente un bénéfice de {net_profit:,.0f} FCFA."
            ]
            for info in info_lines:
                ws.merge_cells(f'A{row}:C{row}')
                cell = ws[f'A{row}']
                cell.value = info
                cell.font = info_font
                cell.fill = info_fill
                row += 1
            
            # Ajuster les largeurs de colonnes
            ws.column_dimensions['A'].width = 15
            ws.column_dimensions['B'].width = 40
            ws.column_dimensions['C'].width = 20
            
            buffer = BytesIO()
            wb.save(buffer)
            buffer.seek(0)
            
            response = HttpResponse(
                buffer.getvalue(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename="rapport_{start_date}_{end_date}.xlsx"'
            return response


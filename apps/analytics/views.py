from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Count, Avg, F, Q, Case, When, DecimalField
from django.db.models.functions import TruncDate, TruncMonth
from django.utils import timezone
from datetime import timedelta, datetime

from apps.sales.models import Sale
from apps.products.models import Product
from apps.inventory.models import Stock
from apps.accounts.models import User
from apps.cashbox.models import CashMovement
from apps.loans.models import Loan
from apps.expenses.models import Expense


class DashboardViewSet(viewsets.ViewSet):
    """
    ViewSet for analytics and dashboard data.
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def overview(self, request):
        """Main dashboard overview."""
        today = timezone.now().date()
        month_start = today.replace(day=1)
        year_start = today.replace(month=1, day=1)
        
        # Sales statistics
        sales_today = Sale.objects.filter(sale_date=today, status='confirmed').aggregate(
            total=Sum('total_amount'),
            count=Count('id')
        )
        
        sales_month = Sale.objects.filter(
            sale_date__gte=month_start,
            status='confirmed'
        ).aggregate(
            total=Sum('total_amount'),
            count=Count('id')
        )
        
        sales_year = Sale.objects.filter(
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
            'total': User.objects.filter(is_customer=True, is_active=True).count(),
            'new_this_month': User.objects.filter(
                is_customer=True,
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
        
        # Pending items
        pending = {
            'sales': Sale.objects.filter(status='draft').count(),
            'payments': Sale.objects.filter(
                status='confirmed',
                payment_status__in=['unpaid', 'partial']
            ).count(),
            'expenses': Expense.objects.filter(status='pending').count(),
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
        """Sales chart data over time."""
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
        
        sales_data = Sale.objects.filter(
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
        """Top selling products."""
        limit = int(request.query_params.get('limit', 10))
        
        from apps.sales.models import SaleLine
        
        top_products = SaleLine.objects.filter(
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
        """Top customers by revenue."""
        limit = int(request.query_params.get('limit', 10))
        
        top_customers = Sale.objects.filter(
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
    
    @action(detail=False, methods=['get'])
    def reports(self, request):
        """Generate various reports."""
        report_type = request.query_params.get('type', 'sales')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        else:
            start_date = timezone.now().date() - timedelta(days=30)
        
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        else:
            end_date = timezone.now().date()
        
        if report_type == 'sales':
            data = Sale.objects.filter(
                sale_date__gte=start_date,
                sale_date__lte=end_date,
                status='confirmed'
            ).values('sale_date').annotate(
                total=Sum('total_amount'),
                count=Count('id')
            ).order_by('sale_date')
        
        elif report_type == 'expenses':
            data = Expense.objects.filter(
                expense_date__gte=start_date,
                expense_date__lte=end_date,
                status='paid'
            ).values('expense_date', 'category__name').annotate(
                total=Sum('amount')
            ).order_by('expense_date')
        
        elif report_type == 'cash':
            data = CashMovement.objects.filter(
                created_at__date__gte=start_date,
                created_at__date__lte=end_date
            ).values('created_at__date', 'movement_type').annotate(
                total=Sum('amount')
            ).order_by('created_at__date')
        
        else:
            return Response({'error': 'Invalid report type'}, status=400)
        
        return Response(list(data))
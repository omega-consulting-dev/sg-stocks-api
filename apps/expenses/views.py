from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from django.db.models import Sum, Count, Q
from drf_spectacular.utils import extend_schema

from core.utils.export_utils import ExcelExporter

from apps.expenses.models import Expense, ExpenseCategory
from apps.expenses.serializers import ExpenseSerializer, ExpenseCategorySerializer
from apps.cashbox.models import Cashbox


class ExpenseCategoryViewSet(viewsets.ModelViewSet):
    queryset = ExpenseCategory.objects.filter(is_active=True)
    serializer_class = ExpenseCategorySerializer


class ExpenseViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Expense model with secure user-based filtering.
    - Super admin: voit toutes les dépenses
    - Manager (access_scope='all'): voit toutes les dépenses
    - Caissier (access_scope='assigned'): voit les dépenses de ses stores assignés
    - Caissier (access_scope='own'): voit uniquement ses propres dépenses
    """
    
    queryset = Expense.objects.select_related('category', 'store')
    serializer_class = ExpenseSerializer
    filterset_fields = ['category', 'store', 'status', 'expense_date']
    
    def get_queryset(self):
        """
        Filtrage sécurisé des dépenses selon le rôle et access_scope.
        Chaque caissier ne voit que ses propres dépenses.
        """
        queryset = super().get_queryset()
        user = self.request.user
        
        # Super admin voit tout
        if user.is_superuser:
            return queryset
        
        # Vérifier le scope d'accès du rôle
        if hasattr(user, 'role') and user.role:
            # Manager avec accès à toutes les dépenses
            if user.role.access_scope == 'all':
                return queryset
            
            # Utilisateur avec accès aux stores assignés
            elif user.role.access_scope == 'assigned':
                assigned_stores = user.assigned_stores.all()
                if assigned_stores.exists():
                    return queryset.filter(store__in=assigned_stores)
                else:
                    return queryset.none()
            
            # Utilisateur avec accès uniquement à ses propres dépenses (caissiers)
            elif user.role.access_scope == 'own':
                return queryset.filter(created_by=user)
        
        # Par défaut, filtrer par créateur (sécurité)
        return queryset.filter(created_by=user)
    
    def perform_create(self, serializer):
        # Générer un numéro unique en récupérant le dernier numéro existant
        last_expense = Expense.objects.order_by('-id').first()
        if last_expense and last_expense.expense_number:
            # Extraire le numéro de la dernière dépense (EXP00000004 -> 4)
            try:
                last_number = int(last_expense.expense_number.replace('EXP', ''))
                next_number = last_number + 1
            except (ValueError, AttributeError):
                # En cas d'erreur, utiliser le count + 1
                next_number = Expense.objects.count() + 1
        else:
            next_number = 1
        
        # Générer le prochain numéro avec un format de 8 chiffres
        expense_number = f"EXP{next_number:08d}"
        
        # Vérifier si le numéro existe déjà (sécurité supplémentaire)
        while Expense.objects.filter(expense_number=expense_number).exists():
            next_number += 1
            expense_number = f"EXP{next_number:08d}"
        
        serializer.save(
            expense_number=expense_number,
            created_by=self.request.user
        )
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve an expense."""
        expense = self.get_object()
        
        # Autoriser l'approbation depuis draft ou pending
        if expense.status not in ['pending', 'draft']:
            return Response(
                {'error': 'Seules les dépenses en brouillon ou en attente peuvent être approuvées.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        expense.status = 'approved'
        expense.approved_by = request.user
        expense.approval_date = timezone.now()
        expense.save()
        
        serializer = self.get_serializer(expense)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject an expense."""
        expense = self.get_object()
        
        # Autoriser le rejet depuis draft ou pending
        if expense.status not in ['pending', 'draft']:
            return Response(
                {'error': 'Seules les dépenses en brouillon ou en attente peuvent être rejetées.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        expense.status = 'rejected'
        expense.save()
        
        serializer = self.get_serializer(expense)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def mark_as_paid(self, request, pk=None):
        """Mark expense as paid."""
        expense = self.get_object()
        
        if expense.status != 'approved':
            return Response(
                {'error': 'Seules les dépenses approuvées peuvent être payées.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Vérifier le solde de la caisse si le paiement est en espèces
        payment_method = request.data.get('payment_method')
        if payment_method == 'cash':
            # Si la dépense n'a pas de point de vente assigné
            if not expense.store:
                return Response(
                    {'error': 'Cette dépense n\'a pas de point de vente assigné. Veuillez d\'abord modifier la dépense et sélectionner un point de vente.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Chercher une caisse active pour ce point de vente
            cashbox = Cashbox.objects.filter(
                store=expense.store,
                is_active=True
            ).first()
            
            if not cashbox:
                return Response(
                    {'error': f'Aucune caisse active n\'est disponible pour le point de vente {expense.store.name}. Veuillez créer ou activer une caisse pour ce point de vente.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Calculer le solde réel de la caisse basé sur les transactions
            from apps.cashbox.utils import get_cashbox_real_balance
            real_balance = get_cashbox_real_balance(store_id=expense.store.id)
            
            if real_balance < expense.amount:
                return Response(
                    {
                        'error': f'Solde insuffisant dans la caisse {cashbox.name}. Solde disponible : {real_balance:,.0f} FCFA, montant requis : {expense.amount:,.0f} FCFA.'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Vérifier le solde bancaire si le paiement est par virement bancaire
        elif payment_method == 'bank_transfer':
            # Si la dépense n'a pas de point de vente assigné
            if not expense.store:
                return Response(
                    {'error': 'Cette dépense n\'a pas de point de vente assigné. Veuillez d\'abord modifier la dépense et sélectionner un point de vente.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Vérifier le solde bancaire
            from apps.cashbox.utils import get_bank_balance
            bank_balance = get_bank_balance(store_id=expense.store.id)
            
            if bank_balance < expense.amount:
                return Response(
                    {
                        'error': f'Solde bancaire insuffisant. Solde disponible : {bank_balance:,.0f} FCFA, montant requis : {expense.amount:,.0f} FCFA.'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        expense.status = 'paid'
        expense.payment_date = timezone.now().date()
        expense.payment_method = payment_method
        expense.payment_reference = request.data.get('payment_reference', '')
        expense.save()
        
        serializer = self.get_serializer(expense)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def export_excel(self, request):
        """Export expenses to Excel."""
        expenses = self.filter_queryset(self.get_queryset())
        
        wb, ws = ExcelExporter.create_workbook("Dépenses")
        
        columns = [
            'N° Dépense', 'Date', 'Catégorie', 'Bénéficiaire',
            'Montant', 'Statut', 'Date Paiement', 'Mode Paiement'
        ]
        ExcelExporter.style_header(ws, columns)
        
        for row_num, expense in enumerate(expenses, 2):
            ws.cell(row=row_num, column=1, value=expense.expense_number)
            ws.cell(row=row_num, column=2, value=expense.expense_date.strftime('%d/%m/%Y'))
            ws.cell(row=row_num, column=3, value=expense.category.name)
            ws.cell(row=row_num, column=4, value=expense.beneficiary)
            ws.cell(row=row_num, column=5, value=float(expense.amount))
            ws.cell(row=row_num, column=6, value=expense.get_status_display())
            ws.cell(row=row_num, column=7, value=expense.payment_date.strftime('%d/%m/%Y') if expense.payment_date else 'N/A')
            ws.cell(row=row_num, column=8, value=expense.get_payment_method_display() if expense.payment_method else 'N/A')
        
        ExcelExporter.auto_adjust_columns(ws)
        
        filename = f"depenses_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return ExcelExporter.generate_response(wb, filename)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get expense statistics grouped by category or individual expenses."""
        # Get filter parameters
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        category_id = request.query_params.get('category')
        group_by = request.query_params.get('group_by', 'category')  # 'category' or 'expense'
        
        # Start with base queryset - only paid and approved expenses
        queryset = Expense.objects.filter(
            Q(status='paid') | Q(status='approved')
        ).select_related('category')
        
        # Apply filters
        if date_from:
            queryset = queryset.filter(expense_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(expense_date__lte=date_to)
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        # Group results
        if group_by == 'category':
            # Group by category, sum amounts and count expenses
            stats = queryset.values('category__name').annotate(
                total_amount=Sum('amount'),
                count=Count('id')
            ).order_by('total_amount')
            
            result = [
                {
                    'category_name': item['category__name'],
                    'total_amount': float(item['total_amount'] or 0),
                    'count': item['count']
                }
                for item in stats
            ]
        else:
            # Return individual expenses
            expenses = queryset.values(
                'id', 'expense_number', 'expense_date', 'description',
                'amount', 'beneficiary', 'category__name'
            ).order_by('expense_date')
            
            result = [
                {
                    'category_name': expense['category__name'],
                    'total_amount': float(expense['amount']),
                    'count': 1,
                    'expense_number': expense['expense_number'],
                    'expense_date': expense['expense_date'],
                    'description': expense['description'],
                    'beneficiary': expense['beneficiary']
                }
                for expense in expenses
            ]
        
        return Response(result)
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get summary statistics for all expenses."""
        user = request.user
        
        # Use get_queryset to respect user permissions
        queryset = self.get_queryset()
        
        # Calculate totals
        total_amount = queryset.aggregate(total=Sum('amount'))['total'] or 0
        total_paid = queryset.filter(status='paid').aggregate(total=Sum('amount'))['total'] or 0
        total_pending = queryset.filter(
            status__in=['draft', 'pending', 'approved']
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Count by status
        counts = {
            'total': queryset.count(),
            'draft': queryset.filter(status='draft').count(),
            'pending': queryset.filter(status='pending').count(),
            'approved': queryset.filter(status='approved').count(),
            'paid': queryset.filter(status='paid').count(),
            'rejected': queryset.filter(status='rejected').count(),
        }
        
        return Response({
            'total_amount': float(total_amount),
            'total_paid': float(total_paid),
            'total_pending': float(total_pending),
            'counts': counts
        })
    
    @action(detail=False, methods=['get'], url_path='stats/export_excel')
    def export_stats_excel(self, request):
        """Export expense statistics to Excel."""
        # Get filter parameters (same as stats)
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        category_id = request.query_params.get('category')
        group_by = request.query_params.get('group_by', 'category')
        
        # Build queryset
        queryset = Expense.objects.filter(
            Q(status='paid') | Q(status='approved')
        ).select_related('category')
        
        if date_from:
            queryset = queryset.filter(expense_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(expense_date__lte=date_to)
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        wb, ws = ExcelExporter.create_workbook("Statistiques Dépenses")
        
        if group_by == 'category':
            columns = ['Catégorie', 'Nombre de Dépenses', 'Montant Total']
            ExcelExporter.style_header(ws, columns)
            
            stats = queryset.values('category__name').annotate(
                total_amount=Sum('amount'),
                count=Count('id')
            ).order_by('total_amount')
            
            for row_num, item in enumerate(stats, 2):
                ws.cell(row=row_num, column=1, value=item['category__name'])
                ws.cell(row=row_num, column=2, value=item['count'])
                ws.cell(row=row_num, column=3, value=float(item['total_amount'] or 0))
        else:
            columns = ['N° Dépense', 'Date', 'Catégorie', 'Bénéficiaire', 'Description', 'Montant']
            ExcelExporter.style_header(ws, columns)
            
            expenses = queryset.order_by('expense_date')
            
            for row_num, expense in enumerate(expenses, 2):
                ws.cell(row=row_num, column=1, value=expense.expense_number)
                ws.cell(row=row_num, column=2, value=expense.expense_date.strftime('%d/%m/%Y'))
                ws.cell(row=row_num, column=3, value=expense.category.name)
                ws.cell(row=row_num, column=4, value=expense.beneficiary)
                ws.cell(row=row_num, column=5, value=expense.description)
                ws.cell(row=row_num, column=6, value=float(expense.amount))
        
        ExcelExporter.auto_adjust_columns(ws)
        
        filename = f"stats_depenses_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return ExcelExporter.generate_response(wb, filename)
    
    @action(detail=False, methods=['get'], url_path='stats/export_pdf')
    def export_stats_pdf(self, request):
        """Export expense statistics to PDF."""
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import inch
        from django.http import HttpResponse
        from io import BytesIO
        
        # Get filter parameters
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        category_id = request.query_params.get('category')
        group_by = request.query_params.get('group_by', 'category')
        
        # Build queryset
        queryset = Expense.objects.filter(
            Q(status='paid') | Q(status='approved')
        ).select_related('category')
        
        if date_from:
            queryset = queryset.filter(expense_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(expense_date__lte=date_to)
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        # Create PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()
        
        # Title
        title = Paragraph("Statistiques des Dépenses", styles['Title'])
        elements.append(title)
        elements.append(Spacer(1, 0.3*inch))
        
        # Data table
        if group_by == 'category':
            data = [['Catégorie', 'Nombre de Dépenses', 'Montant Total']]
            
            stats = queryset.values('category__name').annotate(
                total_amount=Sum('amount'),
                count=Count('id')
            ).order_by('total_amount')
            
            for item in stats:
                data.append([
                    item['category__name'],
                    str(item['count']),
                    f"{float(item['total_amount'] or 0):,.2f} FCFA"
                ])
        else:
            data = [['N° Dépense', 'Date', 'Catégorie', 'Montant']]
            
            expenses = queryset.order_by('expense_date')[:100]  # Limit for PDF
            
            for expense in expenses:
                data.append([
                    expense.expense_number,
                    expense.expense_date.strftime('%d/%m/%Y'),
                    expense.category.name,
                    f"{float(expense.amount):,.2f} FCFA"
                ])
        
        # Create table
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(table)
        doc.build(elements)
        
        buffer.seek(0)
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="stats_depenses_{timezone.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
        
        return response


class ExpenseExportExcelView(APIView):
    """Vue pour exporter les dépenses en Excel."""
    
    def get(self, request):
        """Export expenses to Excel."""
        expenses = Expense.objects.select_related('category', 'store').all()
        
        # Appliquer les filtres si présents
        category = request.query_params.get('category')
        status_filter = request.query_params.get('status')
        date_from = request.query_params.get('expense_date__gte')
        date_to = request.query_params.get('expense_date__lte')
        
        if category:
            expenses = expenses.filter(category_id=category)
        if status_filter:
            expenses = expenses.filter(status=status_filter)
        if date_from:
            expenses = expenses.filter(expense_date__gte=date_from)
        if date_to:
            expenses = expenses.filter(expense_date__lte=date_to)
        
        wb, ws = ExcelExporter.create_workbook("Dépenses")
        
        columns = [
            'N° Dépense', 'Date', 'Catégorie', 'Bénéficiaire',
            'Montant', 'Statut', 'Date Paiement', 'Mode Paiement'
        ]
        ExcelExporter.style_header(ws, columns)
        
        for row_num, expense in enumerate(expenses, 2):
            ws.cell(row=row_num, column=1, value=expense.expense_number)
            ws.cell(row=row_num, column=2, value=expense.expense_date.strftime('%d/%m/%Y'))
            ws.cell(row=row_num, column=3, value=expense.category.name)
            ws.cell(row=row_num, column=4, value=expense.beneficiary)
            ws.cell(row=row_num, column=5, value=float(expense.amount))
            ws.cell(row=row_num, column=6, value=expense.get_status_display())
            ws.cell(row=row_num, column=7, value=expense.payment_date.strftime('%d/%m/%Y') if expense.payment_date else 'N/A')
            ws.cell(row=row_num, column=8, value=expense.get_payment_method_display() if expense.payment_method else 'N/A')
        
        ExcelExporter.auto_adjust_columns(ws)
        
        filename = f"depenses_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return ExcelExporter.generate_response(wb, filename)

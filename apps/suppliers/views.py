from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.db.models import Sum, F, Value, Q, DecimalField
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.utils import timezone
import pandas as pd

from django.contrib.auth import get_user_model
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from datetime import datetime
import io

from apps.accounts.models import User
from apps.accounts.serializers import UserListSerializer, UserDetailSerializer
from apps.suppliers.models import Supplier, SupplierPayment
from apps.suppliers.serializers import SupplierPaymentSerializer


class SupplierViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for suppliers (read-only).
    Uses User model with is_supplier=True
    Supports search and filtering via DjangoFilterBackend
    """
    permission_classes = []
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['supplier__name', 'supplier__supplier_code', 'supplier__email', 'supplier__city', 'first_name', 'email']
    ordering_fields = ['supplier__name', 'supplier__supplier_code', 'created_at']
    ordering = ['supplier__name']
    
    def get_queryset(self):
        return User.objects.filter(is_supplier=True).select_related('supplier')
    
    def get_serializer_class(self):
        if self.action == 'list':
            return UserListSerializer
        return UserDetailSerializer
    
    @action(detail=False, methods=['get'])
    def debts(self, request):
        """
        Liste les fournisseurs avec solde dû pour le tenant courant.
        GET /api/v1/suppliers/debts/
        Retourne les fournisseurs liés à des PurchaseOrder avec un solde non réglé.
        Les données sont automatiquement filtrées par le tenant actuel (django-tenants).
        """
        # Annoter les Suppliers avec total_ordered et total_paid depuis PurchaseOrders confirmées
        # Utiliser output_field=DecimalField pour éviter les erreurs de type mixte
        # Inclure les PO en status 'received' (réception automatique) et 'confirmed'
        statuses = ['confirmed', 'received']
        queryset = Supplier.objects.annotate(
            total_ordered=Coalesce(
                Sum('purchase_orders__total_amount', filter=Q(purchase_orders__status__in=statuses), output_field=DecimalField()), 
                Value(0, output_field=DecimalField())
            ),
            total_paid=Coalesce(
                Sum('purchase_orders__paid_amount', filter=Q(purchase_orders__status__in=statuses), output_field=DecimalField()), 
                Value(0, output_field=DecimalField())
            ),
        ).annotate(
            balance=F('total_ordered') - F('total_paid')
        ).filter(balance__gt=0).order_by('-balance')
        
        # Construire la réponse
        data = [
            {
                'id': s.id,
                'supplier_code': s.supplier_code,
                'name': s.name,
                'email': s.email,
                'phone': s.phone,
                'total_ordered': float(s.total_ordered or 0),
                'total_paid': float(s.total_paid or 0),
                'balance': float(s.balance or 0),
            }
            for s in queryset
        ]
        return Response(data)

    @action(detail=False, methods=['get'])
    def export_excel(self, request):
        """Export suppliers to Excel. Supports filtering via DjangoFilterBackend and SearchFilter."""
        # Utiliser le queryset déjà filtré par les filtres (search, filters, etc.)
        queryset = self.filter_queryset(self.get_queryset())
        
        # Préparer les données
        data = []
        for user in queryset:
            supplier = user.supplier if hasattr(user, 'supplier') else None
            data.append({
                'Code': supplier.supplier_code if supplier else user.username,
                'Nom': supplier.name if supplier else user.first_name,
                'Email': supplier.email if supplier else user.email,
                'Téléphone': supplier.phone if supplier else '',
                'Mobile': supplier.mobile if supplier else '',
                'Ville': supplier.city if supplier else '',
                'Adresse': supplier.address if supplier else '',
                'Actif': 'Oui' if user.is_active else 'Non',
            })
        
        df = pd.DataFrame(data)
        
        # Générer Excel
        response = HttpResponse(content_type='application/vnd.ms-excel')
        filename = f"fournisseurs_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        with pd.ExcelWriter(response, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name="Fournisseurs")
            worksheet = writer.sheets["Fournisseurs"]
            
            # Style header
            for cell in worksheet[1]:
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
                cell.alignment = Alignment(horizontal='center', vertical='center')
            
            # Ajuster les largeurs
            for col_num, col_title in enumerate(df.columns, 1):
                col_letter = get_column_letter(col_num)
                worksheet.column_dimensions[col_letter].width = 20
        
        return response

    @action(detail=False, methods=['get'])
    def export_pdf(self, request):
        """Export suppliers to PDF. Supports filtering via DjangoFilterBackend and SearchFilter."""
        # Utiliser le queryset déjà filtré par les filtres (search, filters, etc.)
        queryset = self.filter_queryset(self.get_queryset())
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            rightMargin=30,
            leftMargin=30,
            topMargin=50,
            bottomMargin=30
        )
        
        elements = []
        styles = getSampleStyleSheet()
        
        # Titre
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#366092'),
            spaceAfter=30,
            alignment=1
        )
        title = Paragraph("Liste des Fournisseurs", title_style)
        elements.append(title)
        
        # Date
        date_style = ParagraphStyle(
            'DateStyle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.grey,
            alignment=1
        )
        date_text = Paragraph(
            f"Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}",
            date_style
        )
        elements.append(date_text)
        elements.append(Spacer(1, 20))
        
        # Données tableau
        data = [['Code', 'Nom', 'Email', 'Téléphone', 'Ville', 'Actif']]
        for user in queryset:
            supplier = user.supplier if hasattr(user, 'supplier') else None
            row = [
                supplier.supplier_code if supplier else user.username,
                supplier.name if supplier else user.first_name,
                supplier.email if supplier else user.email,
                supplier.phone if supplier else '',
                supplier.city if supplier else '',
                'Oui' if user.is_active else 'Non'
            ]
            data.append(row)
        
        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#366092')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        elements.append(table)
        
        # Stats
        elements.append(Spacer(1, 20))
        stats_text = f"Total: {queryset.count()} fournisseur(s) | Actifs: {queryset.filter(is_active=True).count()}"
        stats = Paragraph(stats_text, date_style)
        elements.append(stats)
        
        doc.build(elements)
        buffer.seek(0)
        
        response = HttpResponse(buffer.read(), content_type='application/pdf')
        filename = f'fournisseurs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
    



    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def import_excel(self, request):
        """Import suppliers from Excel."""
        User = get_user_model()
        if 'file' not in request.FILES:
            return Response({'error': 'Aucun fichier fourni'}, status=status.HTTP_400_BAD_REQUEST)
        
        file = request.FILES['file']
    
        try:
            df = pd.read_excel(file)
            
            # ✅ Seuls "Nom" et "Téléphone" sont obligatoires
            required_columns = ['Nom', 'Téléphone']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                return Response(
                    {'error': f'Colonnes manquantes: {", ".join(missing_columns)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            created_count = 0
            updated_count = 0
            errors = []

            for index, row in df.iterrows():
                try:
                    nom = str(row.get('Nom', '')).strip()
                    phone = str(row.get('Téléphone', '')).strip()
                    email = str(row.get('Email', '')).strip() if 'Email' in df.columns else ''

                    # --- USER ---
                    base_username = nom or phone or f"user{index+1}"
                    username = base_username
                    counter = 1
                    while User.objects.filter(username=username).exists():
                        username = f"{base_username}{counter}"
                        counter += 1

                    # --- USER ---
                    user_defaults = {
                        'username': username,
                        'first_name': row.get('Contact', ''),  # si tu veux stocker le contact
                        'last_name': nom,
                        'email': email,
                        'is_supplier': True,  # ⚡ si tu as ce champ dans User
                        'phone': phone,
                    }

                    if email:
                        user, created_user = User.objects.update_or_create(
                            email=email,
                            defaults=user_defaults
                        )
                    else:
                        user, created_user = User.objects.update_or_create(
                            username=username,
                            defaults=user_defaults
                        )

                    if created_user:
                        user.set_password('password123')  # mot de passe par défaut
                        user.save()

                    # --- SUPPLIER ---
                    supplier_defaults = {
                        'name': nom,
                        'contact_person': row.get('Contact', ''),
                        'email': email,
                        'phone': phone,
                        'mobile': row.get('Mobile', ''),
                        'website': row.get('Site web', ''),
                        'address': row.get('Adresse', ''),
                        'city': row.get('Ville', ''),
                        'postal_code': row.get('Code postal', ''),
                        'country': row.get('Pays', 'Cameroun'),
                        'tax_id': row.get('Numéro fiscal', ''),
                        'bank_account': row.get('Compte bancaire', ''),
                        'payment_term': row.get('Conditions de paiement', '30_days'),
                        'rating': row.get('Évaluation', None),
                        'notes': row.get('Notes', ''),
                    }

                    Supplier.objects.update_or_create(
                        user=user,
                        defaults=supplier_defaults
                    )

                    created_count += 1 if created_user else 0
                    updated_count += 0 if created_user else 1

                except Exception as e:
                    errors.append(f"Ligne {index + 2}: {str(e)}")
            
            return Response({
                'message': 'Import terminé',
                'created': created_count,
                'updated': updated_count,
                'errors': errors
            })
            
        except Exception as e:
            return Response(
                {'error': f'Erreur lors de l\'import: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )









class SupplierPaymentViewSet(viewsets.ModelViewSet):
    """Manage supplier payments (create/list/retrieve)."""
    queryset = SupplierPayment.objects.all()
    serializer_class = SupplierPaymentSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        """Return payments for current tenant (django-tenants handles schema isolation)."""
        return SupplierPayment.objects.all()

    def perform_create(self, serializer):
        """Create payment and attach current user as creator."""
        serializer.save(created_by=self.request.user)


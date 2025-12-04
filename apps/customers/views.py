from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from apps.accounts.permissions import HasModulePermission
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth import get_user_model

from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from django.utils import timezone

from core.utils.export_utils import ExcelExporter
import pandas as pd


from apps.accounts.models import User
from apps.accounts.serializers import UserListSerializer, UserDetailSerializer

from apps.customers.models import Customer  

class CustomerViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for customers (read-only).
    Uses User model with is_customer=True
    """
    permission_classes = [IsAuthenticated, HasModulePermission]
    module_name = 'products'
    authentication_classes = [JWTAuthentication]
    filter_backends = [DjangoFilterBackend]
    search_fields = ['customer_code', 'customer_company_name']

    
    def get_queryset(self):
        return User.objects.filter(is_customer=True)
    
    def get_serializer_class(self):
        if self.action == 'list':
            return UserListSerializer
        return UserDetailSerializer
    
    @extend_schema(summary="Exporter les clients en Excel", tags=["Users"])
    @action(detail=False, methods=['get'])
    def export_excel(self, request):
        """Export customers to Excel."""
        customers = User.objects.filter(is_customer=True)
        
        wb, ws = ExcelExporter.create_workbook("Clients")
        
        columns = [
            'Code Client', 'Nom', 'Email', 'Téléphone', 'Adresse',
            'Ville', 'Limite Crédit', 'Date Inscription'
        ]
        ExcelExporter.style_header(ws, columns)
        
        for row_num, customer in enumerate(customers, 2):
            ws.cell(row=row_num, column=1, value=customer.customer_code)
            ws.cell(row=row_num, column=2, value=customer.get_display_name())
            ws.cell(row=row_num, column=3, value=customer.email)
            ws.cell(row=row_num, column=4, value=customer.phone)
            ws.cell(row=row_num, column=5, value=customer.address)
            ws.cell(row=row_num, column=6, value=customer.city)
            ws.cell(row=row_num, column=7, value=float(customer.customer_credit_limit))
            ws.cell(row=row_num, column=8, value=customer.date_joined.strftime('%d/%m/%Y'))
        
        ExcelExporter.auto_adjust_columns(ws)
        
        filename = f"clients_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return ExcelExporter.generate_response(wb, filename)


    @extend_schema(summary="Importer des clients depuis Excel", tags=["Users"])
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def import_excel(self, request):
        """Import customers from Excel."""
        if 'file' not in request.FILES:
            return Response({'error': 'Aucun fichier fourni'}, status=status.HTTP_400_BAD_REQUEST)
        
        file = request.FILES['file']
    
        try:
            df = pd.read_excel(file)
            
           
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

                    # Générer un username unique basé sur nom ou fallback
                    base_username = nom or phone or f"user{index+1}"
                    username = base_username
                    counter = 1
                    while User.objects.filter(username=username).exists():
                        username = f"{base_username}{counter}"
                        counter += 1

                    # --- USER ---
                    defaults = {
                        'username': username,
                        'first_name': row.get('Prénom', ''),
                        'last_name': nom,
                        'is_customer': True,
                        'phone': phone,
                        'address': row.get('Adresse', ''),
                        'city': row.get('Ville', ''),
                        'customer_credit_limit': row.get('Limite Crédit', 0),
                        'customer_company_name': row.get('Entreprise', ''),
                    }

                    if email:
                        user, created = User.objects.update_or_create(
                            email=email,
                            defaults=defaults
                        )
                    else:
                        user, created = User.objects.update_or_create(
                            username=username,
                            defaults=defaults
                        )

                    if created:
                        user.set_password('password123')  # mot de passe par défaut
                        user.save()

                    # --- CUSTOMER ---
                    customer_defaults = {
                        'name': nom or username,
                        'company_name': row.get('Entreprise', ''),
                        'credit_limit': row.get('Limite Crédit', 0),
                        'phone': phone,
                        'address': row.get('Adresse', ''),
                        'city': row.get('Ville', ''),
                    }

                    Customer.objects.update_or_create(
                        user=user,
                        defaults=customer_defaults
                    )

                    created_count += 1 if created else 0
                    updated_count += 0 if created else 1

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
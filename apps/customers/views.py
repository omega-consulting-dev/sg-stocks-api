from rest_framework import viewsets, status
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from django.utils import timezone

from core.utils.export_utils import ExcelExporter
import pandas as pd

from apps.accounts.models import User
from apps.accounts.serializers import UserListSerializer, UserDetailSerializer

class CustomerViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for customers (read-only).
    Uses User model with is_customer=True
    """
    permission_classes = []
    
    def get_queryset(self):
        return User.objects.filter(is_customer=True)
    
    def get_serializer_class(self):
        if self.action == 'list':
            return UserListSerializer
        return UserDetailSerializer
    
    @extend_schema(summary="Exporter les clients en Excel", tags=["Users"])
    @action(detail=False, methods=['get'])
    def export_customers_excel(self, request):
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
    @action(detail=False, methods=['post'])
    def import_customers_excel(self, request):
        """Import customers from Excel."""
        if 'file' not in request.FILES:
            return Response({'error': 'Aucun fichier fourni'}, status=status.HTTP_400_BAD_REQUEST)
        
        file = request.FILES['file']
        
        try:
            df = pd.read_excel(file)
            
            required_columns = ['Nom', 'Email']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                return Response(
                    {'error': f'Colonnes manquantes: {", ".join(missing_columns)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            created_count = 0
            errors = []
            
            for index, row in df.iterrows():
                try:
                    username = row['Email'].split('@')[0]
                    
                    user, created = User.objects.get_or_create(
                        email=row['Email'],
                        defaults={
                            'username': username,
                            'first_name': row.get('Prénom', ''),
                            'last_name': row.get('Nom', ''),
                            'is_customer': True,
                            'phone': row.get('Téléphone', ''),
                            'address': row.get('Adresse', ''),
                            'city': row.get('Ville', ''),
                            'customer_credit_limit': row.get('Limite Crédit', 0),
                            'customer_company_name': row.get('Entreprise', ''),
                        }
                    )
                    
                    if created:
                        user.set_password('password123')  # Default password
                        user.save()
                        created_count += 1
                        
                except Exception as e:
                    errors.append(f"Ligne {index + 2}: {str(e)}")
            
            return Response({
                'message': 'Import terminé',
                'created': created_count,
                'errors': errors
            })
            
        except Exception as e:
            return Response(
                {'error': f'Erreur lors de l\'import: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

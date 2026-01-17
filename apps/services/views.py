"""
Service views for API.
"""

from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.accounts.permissions import HasModulePermission
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from django.db.models import Count, Sum, Q
from django.utils import timezone
from django.http import HttpResponse
import io
import pandas as pd
from reportlab.platypus import Paragraph, Spacer
from reportlab.lib.units import inch

from apps.services.models import Service, ServiceCategory, ServiceIntervention
from apps.services.serializers import (
    ServiceCategorySerializer,
    ServiceListSerializer,
    ServiceDetailSerializer,
    ServiceCreateUpdateSerializer,
    ServiceInterventionListSerializer,
    ServiceInterventionDetailSerializer,
    ServiceInterventionCreateUpdateSerializer,
)
from core.utils.export_utils import ExcelExporter, PDFExporter


@extend_schema_view(
    list=extend_schema(summary="Liste des catégories de services", tags=["Services"]),
    retrieve=extend_schema(summary="Détail d'une catégorie", tags=["Services"]),
    create=extend_schema(summary="Créer une catégorie", tags=["Services"]),
    update=extend_schema(summary="Modifier une catégorie", tags=["Services"]),
)
class ServiceCategoryViewSet(viewsets.ModelViewSet):
    """ViewSet for ServiceCategory model."""
    
    queryset = ServiceCategory.objects.filter(is_active=True).select_related('created_by', 'updated_by').only(
        'id', 'name', 'description', 'is_active', 'created_at', 'updated_at',
        'created_by__id', 'created_by__username', 'updated_by__id', 'updated_by__username'
    )
    serializer_class = ServiceCategorySerializer
    permission_classes = [IsAuthenticated, HasModulePermission]
    module_name = 'services'
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)
    
    @extend_schema(
        summary="Exporter les catégories en Excel",
        tags=["Services"]
    )
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def export_excel(self, request):
        """Export service categories to Excel."""
        # Vérifier que l'utilisateur peut exporter OU voir les services
        if not request.user.has_permission('can_export_data') and not request.user.has_permission('can_view_services'):
            return Response(
                {'detail': "Vous n'avez pas les droits nécessaires pour exporter les données. Veuillez contacter votre supérieur."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        categories = self.filter_queryset(self.get_queryset())
        
        wb, ws = ExcelExporter.create_workbook("Catégories Services")
        
        # Headers
        columns = ['Numéro', 'Nom', 'Description', 'Actif']
        ExcelExporter.style_header(ws, columns)
        
        # Data
        for row_num, category in enumerate(categories, 2):
            ws.cell(row=row_num, column=1, value=category.id)
            ws.cell(row=row_num, column=2, value=category.name)
            ws.cell(row=row_num, column=3, value=category.description or '')
            ws.cell(row=row_num, column=4, value='Oui' if category.is_active else 'Non')
        
        ExcelExporter.auto_adjust_columns(ws)
        
        filename = f"categories_services_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return ExcelExporter.generate_response(wb, filename)
    
    @extend_schema(
        summary="Exporter les catégories en PDF",
        tags=["Services"]
    )
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def export_pdf(self, request):
        """Export service categories to PDF."""
        # Vérifier que l'utilisateur peut exporter OU voir les services
        if not request.user.has_permission('can_export_data') and not request.user.has_permission('can_view_services'):
            return Response(
                {'detail': "Vous n'avez pas les droits nécessaires pour exporter les données. Veuillez contacter votre supérieur."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        categories = self.filter_queryset(self.get_queryset())
        
        buffer = io.BytesIO()
        doc = PDFExporter.create_document(buffer)
        styles = PDFExporter.get_styles()
        story = []
        
        # Title
        story.append(Paragraph("Liste des Catégories de Services", styles['CustomTitle']))
        story.append(Spacer(1, 0.5*inch))
        
        # Date
        date_str = timezone.now().strftime('%d/%m/%Y %H:%M')
        story.append(Paragraph(f"Généré le: {date_str}", styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        # Table
        data = [['Numéro', 'Nom', 'Description']]
        for category in categories[:100]:
            data.append([
                str(category.id),
                category.name,
                category.description or '',
            ])
        
        table = PDFExporter.create_table(data)
        story.append(table)
        
        doc.build(story)
        
        filename = f"categories_services_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        return PDFExporter.generate_response(buffer, filename)
    
    @extend_schema(
        summary="Importer les catégories depuis Excel",
        tags=["Services"],
        request={'multipart/form-data': {'type': 'object', 'properties': {'file': {'type': 'string', 'format': 'binary'}}}}
    )
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def import_excel(self, request):
        """Import service categories from Excel file."""
        if 'file' not in request.FILES:
            return Response({'error': 'Aucun fichier fourni'}, status=status.HTTP_400_BAD_REQUEST)
        
        file = request.FILES['file']
        
        try:
            df = pd.read_excel(file)
            
            # Normalize column names
            columns_map = {c.strip().lower(): c for c in df.columns}
            
            name_col = None
            for candidate in ('nom', 'name'):
                if candidate in columns_map:
                    name_col = columns_map[candidate]
                    break
            
            if not name_col:
                return Response({'error': 'Colonne obligatoire manquante: Nom'}, status=status.HTTP_400_BAD_REQUEST)
            
            desc_col = None
            for candidate in ('description', 'desc'):
                if candidate in columns_map:
                    desc_col = columns_map[candidate]
                    break
            
            active_col = None
            for candidate in ('actif', 'active', 'is_active'):
                if candidate in columns_map:
                    active_col = columns_map[candidate]
                    break
            
            created_count = 0
            updated_count = 0
            errors = []
            
            user = request.user if getattr(request.user, 'is_authenticated', False) else None
            
            for index, row in df.iterrows():
                try:
                    raw_name = row.get(name_col)
                    if pd.isna(raw_name) or str(raw_name).strip() == '':
                        errors.append(f"Ligne {index + 2}: nom vide")
                        continue
                    
                    name = str(raw_name).strip()
                    
                    defaults = {}
                    if desc_col:
                        desc_val = row.get(desc_col)
                        defaults['description'] = '' if pd.isna(desc_val) else str(desc_val)
                    
                    if active_col:
                        raw_active = row.get(active_col)
                        is_active = True
                        if pd.isna(raw_active):
                            is_active = True
                        elif isinstance(raw_active, str):
                            is_active = raw_active.strip().lower() in ('oui', 'yes', 'true', '1')
                        else:
                            try:
                                is_active = bool(int(raw_active))
                            except Exception:
                                is_active = bool(raw_active)
                        defaults['is_active'] = is_active
                    
                    if user:
                        defaults['updated_by_id'] = user.pk
                    
                    category, created = ServiceCategory.objects.update_or_create(
                        name=name,
                        defaults=defaults
                    )
                    
                    if created:
                        if user and getattr(user, 'pk', None):
                            try:
                                category.created_by_id = user.pk
                                category.save()
                            except Exception:
                                pass
                        created_count += 1
                    else:
                        updated_count += 1
                
                except Exception as e:
                    errors.append(f"Ligne {index + 2}: {str(e)}")
            
            return Response({
                'message': 'Import catégories terminé',
                'created': created_count,
                'updated': updated_count,
                'errors': errors
            })
        
        except Exception as e:
            return Response({'error': f"Erreur lors de l'import: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema_view(
    list=extend_schema(summary="Liste des services", tags=["Services"]),
    retrieve=extend_schema(summary="Détail d'un service", tags=["Services"]),
    create=extend_schema(summary="Créer un service", tags=["Services"]),
    update=extend_schema(summary="Modifier un service", tags=["Services"]),
)
class ServiceViewSet(viewsets.ModelViewSet):
    """ViewSet for Service model."""
    
    queryset = Service.objects.select_related('category').prefetch_related('assigned_staff')
    permission_classes = [IsAuthenticated, HasModulePermission]
    module_name = 'services'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'is_active']
    search_fields = ['name', 'reference', 'description']
    ordering_fields = ['name', 'reference', 'unit_price', 'created_at']
    ordering = ['created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ServiceListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return ServiceCreateUpdateSerializer
        return ServiceDetailSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_staff:
            queryset = queryset.filter(is_active=True)
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)
    
    @extend_schema(
        summary="Statistiques des services",
        tags=["Services"]
    )
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get service statistics."""
        stats = {
            'total_services': Service.objects.filter(is_active=True).count(),
            'total_categories': ServiceCategory.objects.filter(is_active=True).count(),
            'total_interventions': ServiceIntervention.objects.count(),
            'pending_interventions': ServiceIntervention.objects.filter(
                status='scheduled'
            ).count(),
            'completed_interventions': ServiceIntervention.objects.filter(
                status='completed'
            ).count(),
        }
        return Response(stats)
    
    @extend_schema(
        summary="Exporter les services en Excel",
        tags=["Services"]
    )
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def export_excel(self, request):
        """Export services to Excel."""
        # Vérifier que l'utilisateur peut exporter OU voir les services
        if not request.user.has_permission('can_export_data') and not request.user.has_permission('can_view_services'):
            return Response(
                {'detail': "Vous n'avez pas les droits nécessaires pour exporter les données. Veuillez contacter votre supérieur."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        services = self.filter_queryset(self.get_queryset())
        
        wb, ws = ExcelExporter.create_workbook("Services")
        
        # Headers
        columns = ['Référence', 'Nom', 'Catégorie', 'Prix Unitaire', 'TVA (%)', 'Durée (min)', 'Actif']
        ExcelExporter.style_header(ws, columns)
        
        # Data
        for row_num, service in enumerate(services, 2):
            ws.cell(row=row_num, column=1, value=service.reference)
            ws.cell(row=row_num, column=2, value=service.name)
            ws.cell(row=row_num, column=3, value=service.category.name)
            ws.cell(row=row_num, column=4, value=float(service.unit_price))
            ws.cell(row=row_num, column=5, value=float(service.tax_rate))
            ws.cell(row=row_num, column=6, value=service.estimated_duration or '')
            ws.cell(row=row_num, column=7, value='Oui' if service.is_active else 'Non')
        
        ExcelExporter.auto_adjust_columns(ws)
        
        filename = f"services_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return ExcelExporter.generate_response(wb, filename)
    
    @extend_schema(
        summary="Exporter les services en PDF",
        tags=["Services"]
    )
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def export_pdf(self, request):
        """Export services to PDF."""
        # Vérifier que l'utilisateur peut exporter OU voir les services
        if not request.user.has_permission('can_export_data') and not request.user.has_permission('can_view_services'):
            return Response(
                {'detail': "Vous n'avez pas les droits nécessaires pour exporter les données. Veuillez contacter votre supérieur."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        services = self.filter_queryset(self.get_queryset())
        
        buffer = io.BytesIO()
        doc = PDFExporter.create_document(buffer)
        styles = PDFExporter.get_styles()
        story = []
        
        # Title
        story.append(Paragraph("Liste des Services", styles['CustomTitle']))
        story.append(Spacer(1, 0.5*inch))
        
        # Date
        date_str = timezone.now().strftime('%d/%m/%Y %H:%M')
        story.append(Paragraph(f"Généré le: {date_str}", styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        # Table
        data = [['Réf.', 'Nom', 'Catégorie', 'Prix', 'TVA %']]
        for service in services[:100]:
            data.append([
                service.reference,
                service.name[:30],
                service.category.name,
                f"{service.unit_price:,.0f}",
                f"{service.tax_rate}%",
            ])
        
        table = PDFExporter.create_table(data)
        story.append(table)
        
        doc.build(story)
        
        filename = f"services_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        return PDFExporter.generate_response(buffer, filename)
    
    @extend_schema(
        summary="Importer les services depuis Excel",
        tags=["Services"],
        request={'multipart/form-data': {'type': 'object', 'properties': {'file': {'type': 'string', 'format': 'binary'}}}}
    )
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def import_excel(self, request):
        """Import services from Excel file."""
        if 'file' not in request.FILES:
            return Response({'error': 'Aucun fichier fourni'}, status=status.HTTP_400_BAD_REQUEST)
        
        file = request.FILES['file']
        
        try:
            df = pd.read_excel(file)
            
            # Normalize column names
            columns_map = {c.strip().lower(): c for c in df.columns}
            
            # Required columns
            ref_col = None
            for candidate in ('référence', 'reference', 'ref'):
                if candidate in columns_map:
                    ref_col = columns_map[candidate]
                    break
            
            name_col = None
            for candidate in ('nom', 'name'):
                if candidate in columns_map:
                    name_col = columns_map[candidate]
                    break
            
            cat_col = None
            for candidate in ('catégorie', 'category', 'cat'):
                if candidate in columns_map:
                    cat_col = columns_map[candidate]
                    break
            
            if not ref_col or not name_col or not cat_col:
                missing = []
                if not ref_col: missing.append('Référence')
                if not name_col: missing.append('Nom')
                if not cat_col: missing.append('Catégorie')
                return Response(
                    {'error': f'Colonnes obligatoires manquantes: {", ".join(missing)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            price_col = None
            for candidate in ('prix unitaire', 'prix', 'price', 'unit_price'):
                if candidate in columns_map:
                    price_col = columns_map[candidate]
                    break
            
            created_count = 0
            updated_count = 0
            errors = []
            
            user = request.user if getattr(request.user, 'is_authenticated', False) else None
            
            for index, row in df.iterrows():
                try:
                    ref = str(row.get(ref_col, '')).strip()
                    name = str(row.get(name_col, '')).strip()
                    cat_name = str(row.get(cat_col, '')).strip()
                    
                    if not ref or not name or not cat_name:
                        errors.append(f"Ligne {index + 2}: référence, nom ou catégorie manquant")
                        continue
                    
                    # Get or create category
                    category, _ = ServiceCategory.objects.get_or_create(
                        name=cat_name,
                        defaults={'created_by_id': user.pk if user else None}
                    )
                    
                    defaults = {
                        'name': name,
                        'category': category,
                        'description': str(row.get('description', '')).strip() if 'description' in columns_map else '',
                        'unit_price': float(row.get(price_col, 0)) if price_col else 0,
                        'tax_rate': float(row.get('tva (%)', 19.25)) if 'tva (%)' in columns_map else 19.25,
                    }
                    
                    if user:
                        defaults['updated_by_id'] = user.pk
                    
                    service, created = Service.objects.update_or_create(
                        reference=ref,
                        defaults=defaults
                    )
                    
                    if created:
                        if user:
                            try:
                                service.created_by_id = user.pk
                                service.save()
                            except Exception:
                                pass
                        created_count += 1
                    else:
                        updated_count += 1
                
                except Exception as e:
                    errors.append(f"Ligne {index + 2}: {str(e)}")
            
            return Response({
                'message': 'Import services terminé',
                'created': created_count,
                'updated': updated_count,
                'errors': errors
            })
        
        except Exception as e:
            return Response({'error': f"Erreur lors de l'import: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema_view(
    list=extend_schema(summary="Liste des interventions", tags=["Interventions"]),
    retrieve=extend_schema(summary="Détail d'une intervention", tags=["Interventions"]),
    create=extend_schema(summary="Créer une intervention", tags=["Interventions"]),
    update=extend_schema(summary="Modifier une intervention", tags=["Interventions"]),
)
class ServiceInterventionViewSet(viewsets.ModelViewSet):
    """ViewSet for ServiceIntervention model."""
    
    queryset = ServiceIntervention.objects.select_related(
        'service', 'customer', 'assigned_to'
    )
    permission_classes = [IsAuthenticated, HasModulePermission]
    module_name = 'services'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['service', 'customer', 'assigned_to', 'status', 'scheduled_date']
    search_fields = ['service__name', 'customer__username', 'notes']
    ordering_fields = ['scheduled_date', 'created_at']
    ordering = ['scheduled_date']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        if user.is_superuser:
            return queryset
        
        if hasattr(user, 'role') and user.role:
            if user.role.access_scope == 'all':
                return queryset
            elif user.role.access_scope == 'own':
                # Voir les interventions créées par soi OU assignées à soi
                from django.db.models import Q
                return queryset.filter(Q(created_by=user) | Q(assigned_to=user))
        
        return queryset.filter(Q(created_by=user) | Q(assigned_to=user))
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ServiceInterventionListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return ServiceInterventionCreateUpdateSerializer
        return ServiceInterventionDetailSerializer
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)
    
    @extend_schema(
        summary="Démarrer une intervention",
        tags=["Interventions"]
    )
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start an intervention."""
        from django.utils import timezone
        intervention = self.get_object()
        
        if intervention.status != 'scheduled':
            return Response(
                {'error': 'Seules les interventions planifiées peuvent être démarrées.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        intervention.status = 'in_progress'
        intervention.actual_start = timezone.now()
        intervention.save()
        
        serializer = self.get_serializer(intervention)
        return Response(serializer.data)
    
    @extend_schema(
        summary="Terminer une intervention",
        tags=["Interventions"]
    )
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Complete an intervention."""
        from django.utils import timezone
        intervention = self.get_object()
        
        if intervention.status not in ['scheduled', 'in_progress']:
            return Response(
                {'error': 'Cette intervention ne peut pas être terminée.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        intervention.status = 'completed'
        intervention.actual_end = timezone.now()
        if not intervention.actual_start:
            intervention.actual_start = intervention.actual_end
        intervention.save()
        
        serializer = self.get_serializer(intervention)
        return Response(serializer.data)
    
    @extend_schema(
        summary="Annuler une intervention",
        tags=["Interventions"]
    )
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel an intervention."""
        intervention = self.get_object()
        
        if intervention.status == 'completed':
            return Response(
                {'error': 'Une intervention terminée ne peut pas être annulée.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        intervention.status = 'cancelled'
        intervention.save()
        
        serializer = self.get_serializer(intervention)
        return Response(serializer.data)
"""
Service views for API.
"""

from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from django.db.models import Count, Sum

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


@extend_schema_view(
    list=extend_schema(summary="Liste des catégories de services", tags=["Services"]),
    retrieve=extend_schema(summary="Détail d'une catégorie", tags=["Services"]),
    create=extend_schema(summary="Créer une catégorie", tags=["Services"]),
    update=extend_schema(summary="Modifier une catégorie", tags=["Services"]),
)
class ServiceCategoryViewSet(viewsets.ModelViewSet):
    """ViewSet for ServiceCategory model."""
    
    queryset = ServiceCategory.objects.filter(is_active=True)
    serializer_class = ServiceCategorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


@extend_schema_view(
    list=extend_schema(summary="Liste des services", tags=["Services"]),
    retrieve=extend_schema(summary="Détail d'un service", tags=["Services"]),
    create=extend_schema(summary="Créer un service", tags=["Services"]),
    update=extend_schema(summary="Modifier un service", tags=["Services"]),
)
class ServiceViewSet(viewsets.ModelViewSet):
    """ViewSet for Service model."""
    
    queryset = Service.objects.select_related('category').prefetch_related('assigned_staff')
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'is_active']
    search_fields = ['name', 'reference', 'description']
    ordering_fields = ['name', 'reference', 'unit_price', 'created_at']
    ordering = ['-created_at']
    
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
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['service', 'customer', 'assigned_to', 'status', 'scheduled_date']
    search_fields = ['service__name', 'customer__username', 'notes']
    ordering_fields = ['scheduled_date', 'created_at']
    ordering = ['-scheduled_date']
    
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
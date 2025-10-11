"""
Product views/viewsets for API.
"""

from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view

from apps.products.models import Product, ProductCategory, ProductImage
from apps.products.serializers import (
    ProductListSerializer,
    ProductDetailSerializer,
    ProductCreateUpdateSerializer,
    ProductCategorySerializer,
    ProductImageSerializer,
)
from apps.products.filters import ProductFilter


@extend_schema_view(
    list=extend_schema(
        summary="Liste des produits",
        description="Récupère la liste de tous les produits avec filtres et recherche.",
        tags=["Produits"]
    ),
    retrieve=extend_schema(
        summary="Détail d'un produit",
        description="Récupère les détails complets d'un produit.",
        tags=["Produits"]
    ),
    create=extend_schema(
        summary="Créer un produit",
        description="Crée un nouveau produit.",
        tags=["Produits"]
    ),
    update=extend_schema(
        summary="Modifier un produit",
        description="Modifie un produit existant.",
        tags=["Produits"]
    ),
    destroy=extend_schema(
        summary="Supprimer un produit",
        description="Supprime un produit (soft delete).",
        tags=["Produits"]
    ),
)
class ProductViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Product model.
    Provides CRUD operations for products.
    """
    
    queryset = Product.objects.select_related('category').prefetch_related('images')
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ['name', 'reference', 'barcode', 'description']
    ordering_fields = ['name', 'reference', 'selling_price', 'created_at']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return ProductListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return ProductCreateUpdateSerializer
        return ProductDetailSerializer
    
    def get_queryset(self):
        """Filter queryset based on user permissions."""
        queryset = super().get_queryset()
        
        # Filter by active status for non-admin users
        if not self.request.user.is_staff:
            queryset = queryset.filter(is_active=True)
        
        return queryset
    
    def perform_create(self, serializer):
        """Set created_by when creating product."""
        serializer.save(created_by=self.request.user)
    
    def perform_update(self, serializer):
        """Set updated_by when updating product."""
        serializer.save(updated_by=self.request.user)
    
    def destroy(self, request, *args, **kwargs):
        """Soft delete: mark as inactive instead of deleting."""
        instance = self.get_object()
        instance.is_active = False
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @extend_schema(
        summary="Produits en rupture de stock",
        description="Récupère la liste des produits en rupture de stock.",
        tags=["Produits"]
    )
    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """Get products with low stock."""
        products = self.get_queryset().filter(
            stocks__quantity__lt=models.F('minimum_stock')
        ).distinct()
        
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        summary="Ajouter une image",
        description="Ajoute une image à un produit.",
        tags=["Produits"]
    )
    @action(detail=True, methods=['post'])
    def add_image(self, request, pk=None):
        """Add image to product."""
        product = self.get_object()
        serializer = ProductImageSerializer(data=request.data)
        
        if serializer.is_valid():
            serializer.save(product=product)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="Exporter les produits",
        description="Exporte la liste des produits au format CSV.",
        tags=["Produits"]
    )
    @action(detail=False, methods=['get'])
    def export(self, request):
        """Export products to CSV."""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="produits.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Référence', 'Nom', 'Catégorie', 'Prix d\'achat',
            'Prix de vente', 'Stock minimum', 'Stock optimal', 'Actif'
        ])
        
        for product in self.get_queryset():
            writer.writerow([
                product.reference,
                product.name,
                product.category.name,
                product.cost_price,
                product.selling_price,
                product.minimum_stock,
                product.optimal_stock,
                'Oui' if product.is_active else 'Non',
            ])
        
        return response


@extend_schema_view(
    list=extend_schema(
        summary="Liste des catégories",
        description="Récupère la liste de toutes les catégories de produits.",
        tags=["Catégories"]
    ),
)
class ProductCategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for ProductCategory model.
    """
    
    queryset = ProductCategory.objects.filter(is_active=True)
    serializer_class = ProductCategorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def perform_create(self, serializer):
        """Set created_by when creating category."""
        serializer.save(created_by=self.request.user)
    
    def perform_update(self, serializer):
        """Set updated_by when updating category."""
        serializer.save(updated_by=self.request.user)
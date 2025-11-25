"""
Product views/viewsets for API.
"""

import io
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from django.utils import timezone
from django.db import models

from core.utils.export_utils import ExcelExporter, PDFExporter
import pandas as pd
from reportlab.platypus import Paragraph, Spacer
from reportlab.lib.units import inch
import csv
from django.http import HttpResponse

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
        """Set created_by when creating product if user is authenticated."""
        user = getattr(self.request, 'user', None)
        # Only assign when user is authenticated and has a primary key
        if user is not None and getattr(user, 'is_authenticated', False) and getattr(user, 'pk', None):
            # assign by id to avoid assigning AnonymousUser proxy objects
            serializer.save(created_by_id=user.pk)
        else:
            serializer.save()
    
    def perform_update(self, serializer):
        """Set updated_by when updating product if user is authenticated."""
        user = getattr(self.request, 'user', None)
        # Only assign when user is authenticated and has a primary key
        if user is not None and getattr(user, 'is_authenticated', False) and getattr(user, 'pk', None):
            try:
                serializer.save(updated_by_id=user.pk)
            except ValueError:
                # In case a non-User id slips through, fallback to saving without updated_by
                serializer.save()
        else:
            serializer.save()
    
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
        """Liste des produits où le stock est inférieur au stock minimum.."""
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
        """Upload d’une image pour un produit."""
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
    def export_csv(self, request, *args, **kwargs):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="produits.csv"'

        writer = csv.writer(response, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        
        # Headers
        writer.writerow([
            'Référence', 'Nom', 'Catégorie', 'Prix d\'achat',
            'Prix de vente', 'Stock min', 'Stock optimal', 'Actif'
        ])
        
        for product in Product.objects.all():
            writer.writerow([
                product.reference.ljust(15),
                product.name.ljust(30),
                product.category.name.ljust(20),
                f"{product.cost_price:,.2f}".rjust(10),
                f"{product.selling_price:,.2f}".rjust(10),
                str(product.minimum_stock).rjust(5),
                str(product.optimal_stock).rjust(5),
                ('Oui' if product.is_active else 'Non').ljust(5)
            ])
    
        return response
    
    @extend_schema(
        summary="Exporter les produits en Excel",
        tags=["Products"]
    )
    @action(detail=False, methods=['get'])
    def export_excel(self, request):
        """Export products to Excel."""
        products = self.filter_queryset(self.get_queryset())
        
        wb, ws = ExcelExporter.create_workbook("Produits")
        
        # Headers
        columns = [
            'Référence', 'Nom', 'Catégorie', 'Prix Achat', 'Prix Vente',
            'TVA (%)', 'Stock Min', 'Stock Optimal', 'Actif'
        ]
        ExcelExporter.style_header(ws, columns)
        
        # Data
        for row_num, product in enumerate(products, 2):
            ws.cell(row=row_num, column=1, value=product.reference)
            ws.cell(row=row_num, column=2, value=product.name)
            ws.cell(row=row_num, column=3, value=product.category.name)
            ws.cell(row=row_num, column=4, value=float(product.cost_price))
            ws.cell(row=row_num, column=5, value=float(product.selling_price))
            ws.cell(row=row_num, column=6, value=float(product.tax_rate))
            ws.cell(row=row_num, column=7, value=product.minimum_stock)
            ws.cell(row=row_num, column=8, value=product.optimal_stock)
            ws.cell(row=row_num, column=9, value='Oui' if product.is_active else 'Non')
        
        ExcelExporter.auto_adjust_columns(ws)
        
        filename = f"produits_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return ExcelExporter.generate_response(wb, filename)


    @extend_schema(
        summary="Exporter les produits en PDF",
        tags=["Products"]
    )
    @action(detail=False, methods=['get'])
    def export_pdf(self, request):
        """Export products to PDF."""
        products = self.filter_queryset(self.get_queryset())
        
        buffer = io.BytesIO()
        doc = PDFExporter.create_document(buffer)
        styles = PDFExporter.get_styles()
        story = []
        
        # Title
        story.append(Paragraph("Liste des Produits", styles['CustomTitle']))
        story.append(Spacer(1, 0.5*inch))
        
        # Date
        date_str = timezone.now().strftime('%d/%m/%Y %H:%M')
        story.append(Paragraph(f"Généré le: {date_str}", styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        # Table
        data = [['Réf.', 'Nom', 'Catégorie', 'Prix Vente', 'Stock']]
        for product in products[:100]:  # Limit to 100 for PDF
            data.append([
                product.reference,
                product.name[:30],
                product.category.name,
                f"{product.selling_price:,.0f}",
                str(product.get_current_stock())
            ])
        
        table = PDFExporter.create_table(data)
        story.append(table)
        
        doc.build(story)
        
        filename = f"produits_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        return PDFExporter.generate_response(buffer, filename)


    @extend_schema(
        summary="Importer des produits depuis Excel",
        tags=["Products"],
        request={'multipart/form-data': {'type': 'object', 'properties': {'file': {'type': 'string', 'format': 'binary'}}}}
    )
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def import_excel(self, request):
        """Import products from Excel file."""
        if 'file' not in request.FILES:
            return Response({'error': 'Aucun fichier fourni'}, status=status.HTTP_400_BAD_REQUEST)
        
        file = request.FILES['file']
        
        try:
            df = pd.read_excel(file)
            
            required_columns = ['Référence', 'Nom', 'Catégorie', 'Prix Vente']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                return Response(
                    {'error': f'Colonnes manquantes: {", ".join(missing_columns)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            created_count = 0
            updated_count = 0
            errors = []

            # 🔥 On garde uniquement un user authentifié avec un ID
            user_id = request.user.pk if (getattr(request.user, 'is_authenticated', False) and getattr(request.user, 'pk', None)) else None

            for index, row in df.iterrows():
                try:
                    # --- CATEGORY ---
                    category, created_cat = ProductCategory.objects.get_or_create(
                        name=row['Catégorie'],
                        defaults={'created_by_id': user_id}
                    )
                    if not created_cat and user_id:
                        category.updated_by_id = user_id
                        category.save()

                    # --- PRODUCT ---
                    defaults = {
                        'name': row['Nom'],
                        'category': category,
                        'selling_price': row.get('Prix Vente', 0),
                        'cost_price': row.get('Prix Achat', 0),
                        'tax_rate': row.get('TVA (%)', 19.25),
                        'minimum_stock': row.get('Stock Min', 0),
                        'optimal_stock': row.get('Stock Optimal', 0)
                    }

                    if user_id:
                        defaults['updated_by_id'] = user_id

                    product, created = Product.objects.update_or_create(
                        reference=row['Référence'],
                        defaults=defaults
                    )

                    if created and user_id:
                        product.created_by_id = user_id
                        product.save()

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


    

@extend_schema_view(
    list=extend_schema(
        summary="Liste des catégories",
        description="Récupère la liste de toutes les catégories de produits.",
        tags=["Catégories"]
    ),
)


class ProductCategoryViewSet(viewsets.ModelViewSet):
    queryset = ProductCategory.objects.filter(is_active=True)
    serializer_class = ProductCategorySerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def perform_create(self, serializer):
        user = getattr(self.request, 'user', None)
        if user is not None and getattr(user, 'is_authenticated', False):
            try:
                serializer.save(created_by=user)
            except ValueError:
                # Defensive: if created_by can't be assigned (AnonymousUser or wrong instance), save without it
                serializer.save()
        else:
            serializer.save()

    
    def perform_update(self, serializer):
        user = getattr(self.request, 'user', None)
        if user is not None and getattr(user, 'is_authenticated', False):
            try:
                serializer.save(updated_by=user)
            except ValueError:
                serializer.save()
        else:
            serializer.save()


    @extend_schema(
        summary="Exporter les categosries de produit en Excel",
        tags=["Categories"]
    )
    @action(detail=False, methods=['get'])
    def export_excel(self, request):
        """Export products to Excel."""
        productscategories = self.filter_queryset(self.get_queryset())
        
        wb, ws = ExcelExporter.create_workbook("Categories")
        
        # Headers
        columns = [
            'Numero','Nom', 'description','Actif'
        ]
        ExcelExporter.style_header(ws, columns)
        
        # Data
        for row_num, category in enumerate(productscategories, 2):
            ws.cell(row=row_num, column=1, value=category.id)
            ws.cell(row=row_num, column=2, value=category.name)
            ws.cell(row=row_num, column=3, value=(category.description or ''))
            ws.cell(row=row_num, column=4, value='Oui' if category.is_active else 'Non')
        
        ExcelExporter.auto_adjust_columns(ws)
        
        filename = f"categorie_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return ExcelExporter.generate_response(wb, filename)



    @extend_schema(
        summary="Exporter les categories en PDF",
        tags=["Productscategories"]
    )
    @action(detail=False, methods=['get'])
    def export_pdf(self, request):
        """Export categories to PDF."""
        categories = self.filter_queryset(self.get_queryset())
        
        buffer = io.BytesIO()
        doc = PDFExporter.create_document(buffer)
        styles = PDFExporter.get_styles()
        story = []
        
        # Title
        story.append(Paragraph("Liste des categories", styles['CustomTitle']))
        story.append(Spacer(1, 0.5*inch))
        
        # Date
        date_str = timezone.now().strftime('%d/%m/%Y %H:%M')
        story.append(Paragraph(f"Généré le: {date_str}", styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        # Table
        data = [['Numero.', 'Nom', 'Description']]
        for category in categories[:100]:  # Limit to 100 for PDF
            data.append([
                category.id,
                category.name,
                category.description,

            ])
        
        table = PDFExporter.create_table(data)
        story.append(table)
        
        doc.build(story)
        
        filename = f"Categories_produits_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        return PDFExporter.generate_response(buffer, filename)


    @extend_schema(
        summary="Importer les catégories depuis Excel",
        tags=["Categories"],
        request={'multipart/form-data': {'type': 'object', 'properties': {'file': {'type': 'string', 'format': 'binary'}}}}
    )
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def import_excel(self, request):
        """Import product categories from an Excel file.

        Expected headers (flexible): 'Nom' or 'Name' (required), 'Description' (optional), 'Actif'/'Active' (optional).
        """
        if 'file' not in request.FILES:
            return Response({'error': 'Aucun fichier fourni'}, status=status.HTTP_400_BAD_REQUEST)

        file = request.FILES['file']

        try:
            df = pd.read_excel(file)

            # Normalize column names to find relevant columns
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
                        errors.append(f"Ligne {index + 2}: nom de catégorie vide")
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
                        # assign by id to avoid assigning AnonymousUser proxy objects
                        defaults['updated_by_id'] = user.pk

                    category, created = ProductCategory.objects.update_or_create(
                        name=name,
                        defaults=defaults
                    )

                    if created:
                        if user and getattr(user, 'pk', None):
                            try:
                                category.created_by_id = user.pk
                                category.save()
                            except Exception:
                                # ignore assignment errors and keep created object
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


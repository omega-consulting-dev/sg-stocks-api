"""
Product serializers for API.
"""

from rest_framework import serializers
from apps.products.models import Product, ProductCategory, ProductImage


class ProductCategorySerializer(serializers.ModelSerializer):
    """Serializer for product categories."""
    
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    full_path = serializers.CharField(read_only=True)
    
    class Meta:
        model = ProductCategory
        fields = [
            'id', 'name', 'description', 'parent', 'parent_name',
            'full_path', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class ProductImageSerializer(serializers.ModelSerializer):
    """Serializer for product images."""
    
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'is_primary', 'order', 'created_at']
        read_only_fields = ['created_at']


class ProductListSerializer(serializers.ModelSerializer):
    """Serializer for product list view (minimal data)."""
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    primary_image = serializers.SerializerMethodField()
    current_stock = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'reference', 'name', 'category_name', 'selling_price',
            'primary_image', 'current_stock', 'is_active', 'is_for_sale'
        ]
    
    def get_primary_image(self, obj):
        """Get primary image URL."""
        primary = obj.images.filter(is_primary=True).first()
        if primary:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(primary.image.url)
        return None


class ProductDetailSerializer(serializers.ModelSerializer):
    """Serializer for product detail view (complete data)."""
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    margin = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    selling_price_with_tax = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    current_stock = serializers.IntegerField(read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'reference', 'barcode', 'name', 'description',
            'category', 'category_name', 'cost_price', 'selling_price',
            'tax_rate', 'selling_price_with_tax', 'margin',
            'minimum_stock', 'optimal_stock', 'current_stock', 'is_low_stock',
            'product_type', 'is_for_sale', 'is_for_purchase', 'is_active',
            'weight', 'volume', 'images',
            'created_at', 'updated_at', 'created_by', 'updated_by'
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']


class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for product creation and update."""
    
    class Meta:
        model = Product
        fields = [
            'reference', 'barcode', 'name', 'description', 'category',
            'cost_price', 'selling_price', 'tax_rate',
            'minimum_stock', 'optimal_stock', 'product_type',
            'is_for_sale', 'is_for_purchase', 'is_active',
            'weight', 'volume'
        ]
    
    def validate_reference(self, value):
        """Validate that reference is unique."""
        instance = self.instance
        if Product.objects.exclude(pk=instance.pk if instance else None).filter(reference=value).exists():
            raise serializers.ValidationError("Un produit avec cette référence existe déjà.")
        return value
    
    def validate(self, data):
        """Validate product data."""
        # Validate cost price <= selling price
        cost_price = data.get('cost_price', 0)
        selling_price = data.get('selling_price', 0)
        
        if cost_price > selling_price:
            raise serializers.ValidationError({
                'selling_price': 'Le prix de vente doit être supérieur au prix d\'achat.'
            })
        
        # Validate minimum stock <= optimal stock
        minimum_stock = data.get('minimum_stock', 0)
        optimal_stock = data.get('optimal_stock', 0)
        
        if minimum_stock > optimal_stock:
            raise serializers.ValidationError({
                'optimal_stock': 'Le stock optimal doit être supérieur au stock minimum.'
            })
        
        return data
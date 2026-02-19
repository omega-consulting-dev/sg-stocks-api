"""
Product and category models.
"""

from django.db import models
from django.core.validators import MinValueValidator
from core.models import TimeStampedModel, ActiveModel, AuditModel
from django.db.models import UniqueConstraint
from django.db.models.functions import Lower

class ProductCategory(ActiveModel, AuditModel):
    """
    Product category/family model.
    """
    name = models.CharField(max_length=100, verbose_name="Désignation")
    description = models.TextField(blank=True, verbose_name="Description")
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name="Catégorie parente"
    )
    
    class Meta:
        constraints = [
        UniqueConstraint(
            Lower('name'),
            'parent',
            name='unique_lower_name_parent'
            ),
        ]
        verbose_name = "Catégorie de produit"
        verbose_name_plural = "Catégories de produits"
        ordering = ['name']
        indexes = [
            models.Index(fields=['is_active', 'name']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return self.name
    
    def get_full_path(self):
        """Get full category path."""
        if self.parent:
            return f"{self.parent.get_full_path()} > {self.name}"
        return self.name


class Product(ActiveModel, AuditModel):
    """
    Product model representing items for sale.
    """
    # Basic information
    name = models.CharField(max_length=200, verbose_name="Nom")
    description = models.TextField(blank=True, verbose_name="Description")
    reference = models.CharField(
        max_length=50,
        verbose_name="Référence"
    )
    barcode = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="Code-barres"
    )
    
    # Category
    category = models.ForeignKey(
        ProductCategory,
        on_delete=models.PROTECT,
        related_name='products',
        verbose_name="Catégorie"
    )
    
    # Pricing
    cost_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Prix d'achat"
    )
    selling_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Prix de vente"
    )
    
    # Tax
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=19.25,
        validators=[MinValueValidator(0)],
        verbose_name="Taux de TVA (%)"
    )
    
    # Stock thresholds
    minimum_stock = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Stock minimum"
    )
    optimal_stock = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Stock optimal"
    )
    
    # Product type
    PRODUCT_TYPE_CHOICES = [
        ('storable', 'Stockable'),
        ('consumable', 'Consommable'),
        ('service', 'Service'),
    ]
    product_type = models.CharField(
        max_length=20,
        choices=PRODUCT_TYPE_CHOICES,
        default='storable',
        verbose_name="Type de produit"
    )
    
    # Status
    is_for_sale = models.BooleanField(default=True, verbose_name="En vente")
    is_for_purchase = models.BooleanField(default=True, verbose_name="Achetable")
    
    # Additional information
    weight = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Poids (kg)"
    )
    volume = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Volume (m³)"
    )
    
    class Meta:
        verbose_name = "Produit"
        verbose_name_plural = "Produits"
        ordering = ['name']
        indexes = [
            models.Index(fields=['is_active', 'category']),
            models.Index(fields=['is_active', 'name']),
            models.Index(fields=['reference']),
            models.Index(fields=['barcode']),
            models.Index(fields=['created_at']),
            models.Index(fields=['is_for_sale', 'is_active']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['reference'],
                condition=models.Q(is_active=True),
                name='unique_active_product_reference'
            ),
            models.UniqueConstraint(
                fields=['barcode'],
                condition=models.Q(is_active=True, barcode__isnull=False),
                name='unique_active_product_barcode'
            )
        ]
    
    def __str__(self):
        return f"{self.reference} - {self.name}"
    
    @property
    def margin(self):
        """Calculate profit margin."""
        if self.cost_price > 0:
            return ((self.selling_price - self.cost_price) / self.cost_price) * 100
        return 0
    
    @property
    def selling_price_with_tax(self):
        """Calculate selling price including tax."""
        return self.selling_price * (1 + self.tax_rate / 100)
    
    def get_current_stock(self):
        """Get current total stock across all warehouses."""
        from apps.inventory.models import Stock
        total = Stock.objects.filter(product=self).aggregate(
            total=models.Sum('quantity')
        )['total']
        return total or 0
    
    def is_low_stock(self):
        """Check if product is below minimum stock."""
        return self.get_current_stock() < self.minimum_stock


class ProductImage(TimeStampedModel):
    """
    Product images model for multiple images per product.
    """
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name="Produit"
    )
    image = models.ImageField(
        upload_to='products/%Y/%m/',
        verbose_name="Image"
    )
    is_primary = models.BooleanField(default=False, verbose_name="Image principale")
    order = models.PositiveIntegerField(default=0, verbose_name="Ordre")
    
    class Meta:
        verbose_name = "Image de produit"
        verbose_name_plural = "Images de produits"
        ordering = ['order', '-is_primary']
    
    def __str__(self):
        return f"Image de {self.product.name}"
    
    def save(self, *args, **kwargs):
        """Ensure only one primary image per product."""
        if self.is_primary:
            ProductImage.objects.filter(
                product=self.product,
                is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)
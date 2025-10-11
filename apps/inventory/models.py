"""
Inventory management models for multi-store stock tracking.
"""

from django.db import models
from django.core.validators import MinValueValidator
from core.models import TimeStampedModel, ActiveModel, AuditModel


class Store(ActiveModel, AuditModel):
    """
    Store/Point of Sale model.
    """
    name = models.CharField(max_length=100, verbose_name="Nom")
    code = models.CharField(max_length=20, unique=True, verbose_name="Code")
    
    # Location
    address = models.TextField(verbose_name="Adresse")
    city = models.CharField(max_length=100, verbose_name="Ville")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Téléphone")
    email = models.EmailField(blank=True, verbose_name="Email")
    
    # Manager
    manager = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_stores',
        verbose_name="Responsable"
    )
    
    # Type
    STORE_TYPE_CHOICES = [
        ('retail', 'Point de vente'),
        ('warehouse', 'Entrepôt'),
        ('both', 'Les deux'),
    ]
    store_type = models.CharField(
        max_length=20,
        choices=STORE_TYPE_CHOICES,
        default='retail',
        verbose_name="Type"
    )
    
    class Meta:
        verbose_name = "Point de vente/Magasin"
        verbose_name_plural = "Points de vente/Magasins"
        ordering = ['name']
    
    def __str__(self):
        return f"{self.code} - {self.name}"


class Stock(AuditModel):
    """
    Stock level model tracking product quantities per store.
    """
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        related_name='stocks',
        verbose_name="Produit"
    )
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name='stocks',
        verbose_name="Magasin"
    )
    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Quantité"
    )
    reserved_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Quantité réservée"
    )
    
    class Meta:
        verbose_name = "Stock"
        verbose_name_plural = "Stocks"
        unique_together = [['product', 'store']]
        ordering = ['store', 'product']
    
    def __str__(self):
        return f"{self.product.name} @ {self.store.name}: {self.quantity}"
    
    @property
    def available_quantity(self):
        """Calculate available quantity (total - reserved)."""
        return self.quantity - self.reserved_quantity


class StockMovement(AuditModel):
    """
    Stock movement tracking model.
    """
    MOVEMENT_TYPE_CHOICES = [
        ('in', 'Entrée'),
        ('out', 'Sortie'),
        ('transfer', 'Transfert'),
        ('adjustment', 'Ajustement'),
        ('return', 'Retour'),
    ]
    
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.PROTECT,
        related_name='movements',
        verbose_name="Produit"
    )
    store = models.ForeignKey(
        Store,
        on_delete=models.PROTECT,
        related_name='movements',
        verbose_name="Magasin"
    )
    movement_type = models.CharField(
        max_length=20,
        choices=MOVEMENT_TYPE_CHOICES,
        verbose_name="Type de mouvement"
    )
    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Quantité"
    )
    
    # Reference to source document
    reference = models.CharField(max_length=100, blank=True, verbose_name="Référence")
    
    # For transfers
    destination_store = models.ForeignKey(
        Store,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='incoming_transfers',
        verbose_name="Magasin destination"
    )
    
    # Notes
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    class Meta:
        verbose_name = "Mouvement de stock"
        verbose_name_plural = "Mouvements de stock"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_movement_type_display()} - {self.product.name} ({self.quantity})"


class StockTransfer(AuditModel):
    """
    Stock transfer between stores.
    """
    STATUS_CHOICES = [
        ('draft', 'Brouillon'),
        ('pending', 'En attente'),
        ('in_transit', 'En transit'),
        ('received', 'Reçu'),
        ('cancelled', 'Annulé'),
    ]
    
    transfer_number = models.CharField(max_length=50, unique=True, verbose_name="Numéro de transfert")
    source_store = models.ForeignKey(
        Store,
        on_delete=models.PROTECT,
        related_name='outgoing_transfers',
        verbose_name="Magasin source"
    )
    destination_store = models.ForeignKey(
        Store,
        on_delete=models.PROTECT,
        related_name='incoming_stock_transfers',
        verbose_name="Magasin destination"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name="Statut"
    )
    
    # Dates
    transfer_date = models.DateField(verbose_name="Date de transfert")
    expected_arrival = models.DateField(null=True, blank=True, verbose_name="Arrivée prévue")
    actual_arrival = models.DateField(null=True, blank=True, verbose_name="Arrivée réelle")
    
    # Validation
    validated_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='validated_transfers',
        verbose_name="Validé par"
    )
    received_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='received_transfers',
        verbose_name="Reçu par"
    )
    
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    class Meta:
        verbose_name = "Transfert de stock"
        verbose_name_plural = "Transferts de stock"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.transfer_number} - {self.source_store} → {self.destination_store}"


class StockTransferLine(TimeStampedModel):
    """
    Stock transfer line items.
    """
    transfer = models.ForeignKey(
        StockTransfer,
        on_delete=models.CASCADE,
        related_name='lines',
        verbose_name="Transfert"
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.PROTECT,
        verbose_name="Produit"
    )
    quantity_requested = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Quantité demandée"
    )
    quantity_sent = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Quantité envoyée"
    )
    quantity_received = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Quantité reçue"
    )
    
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    class Meta:
        verbose_name = "Ligne de transfert"
        verbose_name_plural = "Lignes de transfert"
    
    def __str__(self):
        return f"{self.product.name} - {self.quantity_requested}"


class Inventory(AuditModel):
    """
    Physical inventory count model.
    """
    STATUS_CHOICES = [
        ('draft', 'Brouillon'),
        ('in_progress', 'En cours'),
        ('completed', 'Terminé'),
        ('validated', 'Validé'),
        ('cancelled', 'Annulé'),
    ]
    
    inventory_number = models.CharField(max_length=50, unique=True, verbose_name="Numéro d'inventaire")
    store = models.ForeignKey(
        Store,
        on_delete=models.PROTECT,
        related_name='inventories',
        verbose_name="Magasin"
    )
    inventory_date = models.DateField(verbose_name="Date d'inventaire")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name="Statut"
    )
    
    # Validation
    validated_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='validated_inventories',
        verbose_name="Validé par"
    )
    validation_date = models.DateTimeField(null=True, blank=True, verbose_name="Date de validation")
    
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    class Meta:
        verbose_name = "Inventaire"
        verbose_name_plural = "Inventaires"
        ordering = ['-inventory_date']
    
    def __str__(self):
        return f"{self.inventory_number} - {self.store.name} ({self.inventory_date})"


class InventoryLine(TimeStampedModel):
    """
    Inventory line items for counted products.
    """
    inventory = models.ForeignKey(
        Inventory,
        on_delete=models.CASCADE,
        related_name='lines',
        verbose_name="Inventaire"
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.PROTECT,
        verbose_name="Produit"
    )
    theoretical_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Quantité théorique"
    )
    counted_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Quantité comptée"
    )
    
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    class Meta:
        verbose_name = "Ligne d'inventaire"
        verbose_name_plural = "Lignes d'inventaire"
        unique_together = [['inventory', 'product']]
    
    def __str__(self):
        return f"{self.product.name} - Théo: {self.theoretical_quantity}, Compté: {self.counted_quantity}"
    
    @property
    def difference(self):
        """Calculate difference between theoretical and counted."""
        return self.counted_quantity - self.theoretical_quantity
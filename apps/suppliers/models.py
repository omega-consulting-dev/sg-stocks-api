"""
Supplier management models.
"""

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from core.models import TimeStampedModel, ActiveModel, AuditModel


class Supplier(ActiveModel, AuditModel):
    """
    Supplier/Vendor model.
    """
    # Basic information
    # Link to auth user (optional)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='supplier',
        verbose_name="Utilisateur lié"
    )

    name = models.CharField(max_length=200, verbose_name="Raison sociale")
    supplier_code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Code fournisseur"
    )
    
    # Contact information
    contact_person = models.CharField(max_length=200, blank=True, verbose_name="Contact principal")
    email = models.EmailField(blank=True, verbose_name="Email")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Téléphone")
    mobile = models.CharField(max_length=20, blank=True, verbose_name="Mobile")
    website = models.URLField(blank=True, verbose_name="Site web")
    
    # Address
    address = models.TextField(blank=True, verbose_name="Adresse")
    city = models.CharField(max_length=100, blank=True, verbose_name="Ville")
    postal_code = models.CharField(max_length=20, blank=True, verbose_name="Code postal")
    country = models.CharField(max_length=100, default='Cameroun', verbose_name="Pays")
    
    # Financial information
    tax_id = models.CharField(max_length=50, blank=True, verbose_name="Numéro fiscal")
    bank_account = models.CharField(max_length=50, blank=True, verbose_name="Compte bancaire")
    
    # Payment terms
    PAYMENT_TERM_CHOICES = [
        ('immediate', 'Comptant'),
        ('15_days', '15 jours'),
        ('30_days', '30 jours'),
        ('60_days', '60 jours'),
        ('90_days', '90 jours'),
    ]
    payment_term = models.CharField(
        max_length=20,
        choices=PAYMENT_TERM_CHOICES,
        default='30_days',
        verbose_name="Conditions de paiement"
    )
    
    # Rating
    rating = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
        help_text="Note de 1 à 5",
        verbose_name="Évaluation"
    )
    
    # Notes
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    class Meta:
        verbose_name = "Fournisseur"
        verbose_name_plural = "Fournisseurs"
        ordering = ['name']
    
    def __str__(self):
        return f"{self.supplier_code} - {self.name}"
    
    def get_balance(self):
        """Calculate supplier account balance (what we owe)."""
        from apps.suppliers.models import PurchaseOrder
        from django.db.models import Sum, F
        
        # Inclure les commandes confirmées ET reçues (entrées en stock)
        # Filtrer uniquement celles avec un solde impayé (balance_due > 0)
        orders = PurchaseOrder.objects.filter(
            supplier=self,
            status__in=['confirmed', 'received']
        ).annotate(
            balance_due_calc=F('total_amount') - F('paid_amount')
        ).filter(balance_due_calc__gt=0)
        
        # Sommer les balances dues uniquement (ignorer les sur-paiements)
        total_balance = orders.aggregate(
            total=Sum(F('total_amount') - F('paid_amount'))
        )['total'] or 0
        
        return total_balance


class PurchaseOrder(AuditModel):
    """
    Purchase order model for ordering from suppliers.
    """
    STATUS_CHOICES = [
        ('draft', 'Brouillon'),
        ('sent', 'Envoyé'),
        ('confirmed', 'Confirmé'),
        ('received', 'Reçu'),
        ('cancelled', 'Annulé'),
    ]
    
    order_number = models.CharField(max_length=50, unique=True, verbose_name="Numéro de commande")
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name='purchase_orders',
        verbose_name="Fournisseur"
    )
    store = models.ForeignKey(
        'inventory.Store',
        on_delete=models.PROTECT,
        related_name='purchase_orders',
        verbose_name="Magasin de destination"
    )
    
    # Dates
    order_date = models.DateField(verbose_name="Date de commande")
    expected_delivery = models.DateField(null=True, blank=True, verbose_name="Livraison prévue")
    actual_delivery = models.DateField(null=True, blank=True, verbose_name="Livraison réelle")
    # Date d'échéance de paiement pour cette commande
    due_date = models.DateField(null=True, blank=True, verbose_name="Date d'échéance")
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name="Statut"
    )
    
    # Financial
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Sous-total"
    )
    tax_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Montant TVA"
    )
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Montant total"
    )
    paid_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Montant payé",
        help_text="Montant déjà versé au fournisseur pour cette commande"
    )
    
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    class Meta:
        verbose_name = "Bon de commande"
        verbose_name_plural = "Bons de commande"
        ordering = ['-order_date']
    
    def __str__(self):
        return f"{self.order_number} - {self.supplier.name}"
    
    @property
    def balance_due(self):
        """Calculate remaining balance."""
        return self.total_amount - self.paid_amount
    
    @property
    def is_fully_paid(self):
        """Check if order is fully paid."""
        return self.paid_amount >= self.total_amount


class PurchaseOrderLine(TimeStampedModel):
    """
    Purchase order line items.
    """
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name='lines',
        verbose_name="Bon de commande"
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.PROTECT,
        verbose_name="Produit"
    )
    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Quantité"
    )
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Prix unitaire"
    )
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=19.25,
        verbose_name="Taux TVA (%)"
    )
    
    # Reception
    quantity_received = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Quantité reçue"
    )
    
    class Meta:
        verbose_name = "Ligne de commande"
        verbose_name_plural = "Lignes de commande"
    
    def __str__(self):
        return f"{self.product.name} - {self.quantity}"
    
    @property
    def subtotal(self):
        """Calculate line subtotal."""
        return self.quantity * self.unit_price
    
    @property
    def tax_amount(self):
        """Calculate tax amount."""
        return self.subtotal * (self.tax_rate / 100)
    
    @property
    def total(self):
        """Calculate line total including tax."""
        return self.subtotal + self.tax_amount


class SupplierPayment(AuditModel):
    """
    Supplier payment tracking.
    """
    payment_number = models.CharField(max_length=50, unique=True, verbose_name="Numéro de paiement")
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name='payments',
        verbose_name="Fournisseur"
    )
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.PROTECT,
        related_name='payments',
        null=True,
        blank=True,
        verbose_name="Bon de commande"
    )
    
    # Payment details
    payment_date = models.DateField(verbose_name="Date de paiement")
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Montant"
    )
    
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Espèces'),
        ('bank_transfer', 'Virement bancaire'),
        ('check', 'Chèque'),
        ('mobile_money', 'Mobile Money'),
    ]
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        verbose_name="Mode de paiement"
    )
    
    reference = models.CharField(max_length=100, blank=True, verbose_name="Référence")
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    class Meta:
        verbose_name = "Paiement fournisseur"
        verbose_name_plural = "Paiements fournisseurs"
        ordering = ['-payment_date']
    
    def __str__(self):
        return f"{self.payment_number} - {self.supplier.name} ({self.amount})"
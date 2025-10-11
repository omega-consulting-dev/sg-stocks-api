"""
Sales management models.
"""

from django.db import models
from django.core.validators import MinValueValidator
from core.models import TimeStampedModel, AuditModel


class Sale(AuditModel):
    """
    Sale/Order model representing a sale transaction.
    """
    STATUS_CHOICES = [
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmé'),
        ('completed', 'Terminé'),
        ('cancelled', 'Annulé'),
    ]
    
    sale_number = models.CharField(max_length=50, unique=True, verbose_name="Numéro de vente")
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.PROTECT,
        related_name='sales',
        null=True,
        blank=True,
        verbose_name="Client"
    )
    store = models.ForeignKey(
        'inventory.Store',
        on_delete=models.PROTECT,
        related_name='sales',
        verbose_name="Point de vente"
    )
    
    # Dates
    sale_date = models.DateField(verbose_name="Date de vente")
    
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
    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Montant remise"
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
    
    # Payment
    PAYMENT_STATUS_CHOICES = [
        ('unpaid', 'Non payé'),
        ('partial', 'Partiellement payé'),
        ('paid', 'Payé'),
    ]
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='unpaid',
        verbose_name="Statut paiement"
    )
    paid_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Montant payé"
    )
    
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    class Meta:
        verbose_name = "Vente"
        verbose_name_plural = "Ventes"
        ordering = ['-sale_date', '-created_at']
    
    def __str__(self):
        return f"{self.sale_number} - {self.sale_date}"
    
    @property
    def balance_due(self):
        """Calculate remaining balance."""
        return self.total_amount - self.paid_amount
    
    @property
    def is_fully_paid(self):
        """Check if sale is fully paid."""
        return self.paid_amount >= self.total_amount
    
    def calculate_totals(self):
        """Calculate sale totals from lines."""
        lines = self.lines.all()
        self.subtotal = sum(line.subtotal for line in lines)
        self.tax_amount = sum(line.tax_amount for line in lines)
        self.total_amount = self.subtotal + self.tax_amount - self.discount_amount
        
        # Update payment status
        if self.paid_amount == 0:
            self.payment_status = 'unpaid'
        elif self.paid_amount >= self.total_amount:
            self.payment_status = 'paid'
        else:
            self.payment_status = 'partial'


class SaleLine(TimeStampedModel):
    """
    Sale line items for products and services.
    """
    LINE_TYPE_CHOICES = [
        ('product', 'Produit'),
        ('service', 'Service'),
    ]
    
    sale = models.ForeignKey(
        Sale,
        on_delete=models.CASCADE,
        related_name='lines',
        verbose_name="Vente"
    )
    line_type = models.CharField(
        max_length=20,
        choices=LINE_TYPE_CHOICES,
        verbose_name="Type"
    )
    
    # Product or Service
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name="Produit"
    )
    service = models.ForeignKey(
        'services.Service',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name="Service"
    )
    
    description = models.CharField(max_length=200, blank=True, verbose_name="Description")
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
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Remise (%)"
    )
    
    class Meta:
        verbose_name = "Ligne de vente"
        verbose_name_plural = "Lignes de vente"
    
    def __str__(self):
        item_name = self.product.name if self.product else self.service.name
        return f"{item_name} - {self.quantity}"
    
    @property
    def subtotal(self):
        """Calculate line subtotal before tax and discount."""
        return self.quantity * self.unit_price
    
    @property
    def discount_amount(self):
        """Calculate discount amount."""
        return self.subtotal * (self.discount_percentage / 100)
    
    @property
    def subtotal_after_discount(self):
        """Calculate subtotal after discount."""
        return self.subtotal - self.discount_amount
    
    @property
    def tax_amount(self):
        """Calculate tax amount."""
        return self.subtotal_after_discount * (self.tax_rate / 100)
    
    @property
    def total(self):
        """Calculate line total including tax."""
        return self.subtotal_after_discount + self.tax_amount


class Quote(AuditModel):
    """
    Quote/Proforma model for customer quotations.
    """
    STATUS_CHOICES = [
        ('draft', 'Brouillon'),
        ('sent', 'Envoyé'),
        ('accepted', 'Accepté'),
        ('rejected', 'Rejeté'),
        ('expired', 'Expiré'),
    ]
    
    quote_number = models.CharField(max_length=50, unique=True, verbose_name="Numéro de devis")
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.PROTECT,
        related_name='quotes',
        verbose_name="Client"
    )
    store = models.ForeignKey(
        'inventory.Store',
        on_delete=models.PROTECT,
        related_name='quotes',
        verbose_name="Point de vente"
    )
    
    # Dates
    quote_date = models.DateField(verbose_name="Date du devis")
    valid_until = models.DateField(verbose_name="Valide jusqu'au")
    
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
    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Montant remise"
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
    
    # Linked sale
    sale = models.OneToOneField(
        Sale,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='quote',
        verbose_name="Vente associée"
    )
    
    notes = models.TextField(blank=True, verbose_name="Notes")
    terms_and_conditions = models.TextField(blank=True, verbose_name="Conditions générales")
    
    class Meta:
        verbose_name = "Devis"
        verbose_name_plural = "Devis"
        ordering = ['-quote_date']
    
    def __str__(self):
        return f"{self.quote_number} - {self.customer.name}"


class QuoteLine(TimeStampedModel):
    """
    Quote line items.
    """
    LINE_TYPE_CHOICES = [
        ('product', 'Produit'),
        ('service', 'Service'),
    ]
    
    quote = models.ForeignKey(
        Quote,
        on_delete=models.CASCADE,
        related_name='lines',
        verbose_name="Devis"
    )
    line_type = models.CharField(
        max_length=20,
        choices=LINE_TYPE_CHOICES,
        verbose_name="Type"
    )
    
    # Product or Service
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name="Produit"
    )
    service = models.ForeignKey(
        'services.Service',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name="Service"
    )
    
    description = models.CharField(max_length=200, blank=True, verbose_name="Description")
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
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Remise (%)"
    )
    
    class Meta:
        verbose_name = "Ligne de devis"
        verbose_name_plural = "Lignes de devis"
    
    def __str__(self):
        item_name = self.product.name if self.product else self.service.name
        return f"{item_name} - {self.quantity}"
    
    @property
    def subtotal(self):
        """Calculate line subtotal."""
        return self.quantity * self.unit_price
    
    @property
    def discount_amount(self):
        """Calculate discount amount."""
        return self.subtotal * (self.discount_percentage / 100)
    
    @property
    def subtotal_after_discount(self):
        """Calculate subtotal after discount."""
        return self.subtotal - self.discount_amount
    
    @property
    def tax_amount(self):
        """Calculate tax amount."""
        return self.subtotal_after_discount * (self.tax_rate / 100)
    
    @property
    def total(self):
        """Calculate line total."""
        return self.subtotal_after_discount + self.tax_amount
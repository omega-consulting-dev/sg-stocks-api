from django.db import models
from django.core.validators import MinValueValidator
from core.models import TimeStampedModel, AuditModel


class Invoice(AuditModel):
    """Invoice model for billing customers."""
    
    STATUS_CHOICES = [
        ('draft', 'Brouillon'),
        ('sent', 'Envoyée'),
        ('paid', 'Payée'),
        ('overdue', 'En retard'),
        ('cancelled', 'Annulée'),
    ]
    
    invoice_number = models.CharField(max_length=50, unique=True, verbose_name="Numéro de facture")
    customer = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='invoices',
        limit_choices_to={'is_customer': True},
        verbose_name="Client"
    )
    sale = models.OneToOneField(
        'sales.Sale',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invoice',
        verbose_name="Vente"
    )
    
    # Dates
    invoice_date = models.DateField(verbose_name="Date de facture")
    due_date = models.DateField(verbose_name="Date d'échéance")
    
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
    paid_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Montant payé"
    )
    
    # Payment terms
    payment_term = models.CharField(
        max_length=20,
        choices=[
            ('immediate', 'Comptant'),
            ('15_days', '15 jours'),
            ('30_days', '30 jours'),
            ('60_days', '60 jours'),
        ],
        default='30_days',
        verbose_name="Conditions de paiement"
    )
    
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    class Meta:
        verbose_name = "Facture"
        verbose_name_plural = "Factures"
        ordering = ['-invoice_date']
    
    def __str__(self):
        return f"{self.invoice_number} - {self.customer.get_display_name()}"
    
    @property
    def balance_due(self):
        """Calculate remaining balance."""
        return self.total_amount - self.paid_amount
    
    @property
    def is_fully_paid(self):
        """Check if invoice is fully paid."""
        return self.paid_amount >= self.total_amount
    
    @property
    def is_overdue(self):
        """Check if invoice is overdue."""
        from django.utils import timezone
        return (
            self.status not in ['paid', 'cancelled'] and
            self.due_date < timezone.now().date()
        )
    
    def send_by_email(self):
        """Send invoice by email to customer."""
        # TODO: Implement email sending
        pass
    
    def generate_pdf(self):
        """Generate PDF version of invoice."""
        from core.utils.pdf_templates import InvoicePDFGenerator
        import io
        
        buffer = io.BytesIO()
        generator = InvoicePDFGenerator(self)
        generator.generate(buffer)
        return buffer


class InvoiceLine(TimeStampedModel):
    """Invoice line items."""
    
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='lines',
        verbose_name="Facture"
    )
    description = models.CharField(max_length=200, verbose_name="Description")
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
        verbose_name = "Ligne de facture"
        verbose_name_plural = "Lignes de facture"
    
    def __str__(self):
        return f"{self.description} - {self.quantity}"
    
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


class InvoicePayment(AuditModel):
    """Invoice payment tracking."""
    
    payment_number = models.CharField(max_length=50, unique=True, verbose_name="Numéro de paiement")
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.PROTECT,
        related_name='payments',
        verbose_name="Facture"
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
        ('card', 'Carte bancaire'),
        ('mobile_money', 'Mobile Money'),
        ('check', 'Chèque'),
        ('bank_transfer', 'Virement'),
    ]
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        verbose_name="Mode de paiement"
    )
    
    reference = models.CharField(max_length=100, blank=True, verbose_name="Référence")
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    class Meta:
        verbose_name = "Paiement de facture"
        verbose_name_plural = "Paiements de factures"
        ordering = ['-payment_date']
    
    def __str__(self):
        return f"{self.payment_number} - {self.invoice.invoice_number} ({self.amount})"

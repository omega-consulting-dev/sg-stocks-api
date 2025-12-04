"""
Customer management models.
"""

from django.db import models
from django.conf import settings
from core.models import TimeStampedModel, ActiveModel, AuditModel


class Customer(ActiveModel, AuditModel):
    """
    Customer model (unified for both individual and business customers).
    """
    # Link to auth user (optional)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='customer',
        verbose_name="Utilisateur lié"
    )
    
    # Basic information
    name = models.CharField(max_length=200, verbose_name="Nom/Raison sociale")
    customer_code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Code client"
    )
    
    # Contact information
    email = models.EmailField(blank=True, verbose_name="Email")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Téléphone")
    mobile = models.CharField(max_length=20, blank=True, verbose_name="Mobile")
    
    # Address
    address = models.TextField(blank=True, verbose_name="Adresse")
    city = models.CharField(max_length=100, blank=True, verbose_name="Ville")
    postal_code = models.CharField(max_length=20, blank=True, verbose_name="Code postal")
    country = models.CharField(max_length=100, default='Cameroun', verbose_name="Pays")
    
    # Billing information
    billing_address = models.TextField(blank=True, verbose_name="Adresse de facturation")
    tax_id = models.CharField(max_length=50, blank=True, verbose_name="Numéro fiscal")
    
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
        default='immediate',
        verbose_name="Conditions de paiement"
    )
    credit_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Limite de crédit"
    )
    
    # Notes
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    class Meta:
        verbose_name = "Client"
        verbose_name_plural = "Clients"
        ordering = ['name']
    
    def __str__(self):
        return f"{self.customer_code} - {self.name}"
    
    def get_balance(self):
        """Calculate customer account balance."""
        from apps.invoicing.models import Invoice
        from django.db.models import Sum, Q
        
        invoices = Invoice.objects.filter(customer=self)
        total_invoiced = invoices.aggregate(
            total=Sum('total_amount')
        )['total'] or 0
        
        total_paid = invoices.aggregate(
            total=Sum('paid_amount')
        )['total'] or 0
        
        return total_invoiced - total_paid
    
    def has_credit_available(self, amount):
        """Check if customer has enough credit available."""
        if self.credit_limit == 0:
            return True
        current_balance = self.get_balance()
        return (current_balance + amount) <= self.credit_limit


class CustomerContact(TimeStampedModel, ActiveModel):
    """
    Additional contacts for a customer.
    """
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='contacts',
        verbose_name="Client"
    )
    name = models.CharField(max_length=200, verbose_name="Nom")
    position = models.CharField(max_length=100, blank=True, verbose_name="Fonction")
    email = models.EmailField(blank=True, verbose_name="Email")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Téléphone")
    mobile = models.CharField(max_length=20, blank=True, verbose_name="Mobile")
    is_primary = models.BooleanField(default=False, verbose_name="Contact principal")
    
    class Meta:
        verbose_name = "Contact client"
        verbose_name_plural = "Contacts clients"
    
    def __str__(self):
        return f"{self.name} ({self.customer.name})"
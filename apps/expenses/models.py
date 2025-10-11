"""
Expense management models.
"""

from django.db import models
from django.core.validators import MinValueValidator
from core.models import AuditModel


class ExpenseCategory(AuditModel):
    """
    Expense category model.
    """
    name = models.CharField(max_length=100, verbose_name="Nom")
    code = models.CharField(max_length=20, unique=True, verbose_name="Code")
    description = models.TextField(blank=True, verbose_name="Description")
    is_active = models.BooleanField(default=True, verbose_name="Active")
    
    class Meta:
        verbose_name = "Catégorie de dépense"
        verbose_name_plural = "Catégories de dépenses"
        ordering = ['name']
    
    def __str__(self):
        return f"{self.code} - {self.name}"


class Expense(AuditModel):
    """
    Expense model for tracking company expenses.
    """
    STATUS_CHOICES = [
        ('draft', 'Brouillon'),
        ('pending', 'En attente'),
        ('approved', 'Approuvé'),
        ('paid', 'Payé'),
        ('rejected', 'Rejeté'),
    ]
    
    expense_number = models.CharField(max_length=50, unique=True, verbose_name="Numéro de dépense")
    category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.PROTECT,
        related_name='expenses',
        verbose_name="Catégorie"
    )
    store = models.ForeignKey(
        'inventory.Store',
        on_delete=models.PROTECT,
        related_name='expenses',
        null=True,
        blank=True,
        verbose_name="Point de vente"
    )
    
    # Expense details
    expense_date = models.DateField(verbose_name="Date de dépense")
    description = models.TextField(verbose_name="Description")
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Montant"
    )
    
    # Beneficiary
    beneficiary = models.CharField(max_length=200, verbose_name="Bénéficiaire")
    
    # Payment
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Espèces'),
        ('bank_transfer', 'Virement bancaire'),
        ('check', 'Chèque'),
        ('mobile_money', 'Mobile Money'),
        ('card', 'Carte bancaire'),
    ]
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        null=True,
        blank=True,
        verbose_name="Mode de paiement"
    )
    payment_reference = models.CharField(max_length=100, blank=True, verbose_name="Référence de paiement")
    payment_date = models.DateField(null=True, blank=True, verbose_name="Date de paiement")
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name="Statut"
    )
    
    # Approval
    approved_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_expenses',
        verbose_name="Approuvé par"
    )
    approval_date = models.DateTimeField(null=True, blank=True, verbose_name="Date d'approbation")
    
    # Attachments
    receipt = models.FileField(
        upload_to='expenses/receipts/%Y/%m/',
        null=True,
        blank=True,
        verbose_name="Reçu/Facture"
    )
    
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    class Meta:
        verbose_name = "Dépense"
        verbose_name_plural = "Dépenses"
        ordering = ['-expense_date', '-created_at']
    
    def __str__(self):
        return f"{self.expense_number} - {self.description[:50]}"
    
    @property
    def is_paid(self):
        """Check if expense is paid."""
        return self.status == 'paid'
    
    @property
    def is_approved(self):
        """Check if expense is approved."""
        return self.status in ['approved', 'paid']
"""
Loan management models for tracking borrowings and repayments.
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from core.models import TimeStampedModel, AuditModel
from decimal import Decimal


class Loan(AuditModel):
    """
    Loan model for tracking borrowed money.
    """
    STATUS_CHOICES = [
        ('active', 'Actif'),
        ('paid', 'Remboursé'),
        ('defaulted', 'En défaut'),
        ('cancelled', 'Annulé'),
    ]
    
    LOAN_TYPE_CHOICES = [
        ('bank', 'Prêt bancaire'),
        ('supplier', 'Crédit fournisseur'),
        ('personal', 'Prêt personnel'),
        ('other', 'Autre'),
    ]
    
    loan_number = models.CharField(max_length=50, unique=True, verbose_name="Numéro de prêt")
    loan_type = models.CharField(
        max_length=20,
        choices=LOAN_TYPE_CHOICES,
        verbose_name="Type de prêt"
    )
    
    # Lender information
    lender_name = models.CharField(max_length=200, verbose_name="Nom du prêteur")
    lender_contact = models.CharField(max_length=200, blank=True, verbose_name="Contact prêteur")
    
    # Store (point of sale)
    store = models.ForeignKey(
        'inventory.Store',
        on_delete=models.PROTECT,
        related_name='loans',
        null=True,
        blank=True,
        verbose_name="Point de vente"
    )
    
    # Loan details
    principal_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Montant emprunté"
    )
    interest_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="Taux d'intérêt (%)"
    )
    duration_months = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name="Durée (mois)"
    )
    
    # Dates
    start_date = models.DateField(verbose_name="Date de début")
    end_date = models.DateField(verbose_name="Date de fin")
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name="Statut"
    )
    
    # Amounts
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Montant total (capital + intérêts)"
    )
    paid_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Montant payé"
    )
    
    # Notes
    purpose = models.TextField(blank=True, verbose_name="Objet du prêt")
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    class Meta:
        verbose_name = "Emprunt"
        verbose_name_plural = "Emprunts"
        ordering = ['-start_date']
    
    def __str__(self):
        return f"{self.loan_number} - {self.lender_name}"
    
    @property
    def balance_due(self):
        """Calculate remaining balance."""
        return self.total_amount - self.paid_amount
    
    @property
    def is_fully_paid(self):
        """Check if loan is fully repaid."""
        return self.paid_amount >= self.total_amount
    
    def calculate_total_amount(self):
        """Calculate total amount including interest."""
        if self.loan_type == 'bank':
            # Prêt bancaire: taux annuel proratisé sur la durée
            interest_amount = (self.principal_amount * self.interest_rate * self.duration_months) / (100 * 12)
        else:
            # Prêt personnel, fournisseur, autre: taux simple sur le montant total
            interest_amount = (self.principal_amount * self.interest_rate) / 100
        
        self.total_amount = self.principal_amount + interest_amount
        return self.total_amount
    
    def calculate_monthly_payment(self):
        """Calculate monthly payment amount."""
        if self.duration_months > 0:
            return self.total_amount / self.duration_months
        return 0


class LoanPayment(AuditModel):
    """
    Loan payment/repayment model.
    """
    payment_number = models.CharField(max_length=50, unique=True, verbose_name="Numéro de paiement")
    loan = models.ForeignKey(
        Loan,
        on_delete=models.PROTECT,
        related_name='payments',
        verbose_name="Emprunt"
    )
    
    # Payment details
    payment_date = models.DateField(verbose_name="Date de paiement")
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Montant"
    )
    principal_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Montant capital"
    )
    interest_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Montant intérêts"
    )
    
    # Payment method
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Espèces'),
        ('bank_transfer', 'Virement bancaire'),
        ('mobile_money', 'Mobile Money (MTN/Orange)'),
        ('check', 'Chèque'),
    ]
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        verbose_name="Mode de paiement"
    )
    
    reference = models.CharField(max_length=100, blank=True, verbose_name="Référence")
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    class Meta:
        verbose_name = "Paiement d'emprunt"
        verbose_name_plural = "Paiements d'emprunts"
        ordering = ['-payment_date']
    
    def __str__(self):
        return f"{self.payment_number} - {self.loan.loan_number} ({self.amount})"


class LoanSchedule(TimeStampedModel):
    """
    Loan repayment schedule model.
    """
    STATUS_CHOICES = [
        ('pending', 'À payer'),
        ('paid', 'Payé'),
        ('overdue', 'En retard'),
        ('partial', 'Partiellement payé'),
    ]
    
    loan = models.ForeignKey(
        Loan,
        on_delete=models.CASCADE,
        related_name='schedule',
        verbose_name="Emprunt"
    )
    
    # Schedule details
    installment_number = models.IntegerField(verbose_name="Numéro d'échéance")
    due_date = models.DateField(verbose_name="Date d'échéance")
    
    # Amounts
    principal_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Montant capital"
    )
    interest_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Montant intérêts"
    )
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Montant total"
    )
    paid_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Montant payé"
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Statut"
    )
    payment_date = models.DateField(null=True, blank=True, verbose_name="Date de paiement")
    
    class Meta:
        verbose_name = "Échéancier d'emprunt"
        verbose_name_plural = "Échéanciers d'emprunts"
        ordering = ['loan', 'installment_number']
        unique_together = [['loan', 'installment_number']]
    
    def __str__(self):
        return f"{self.loan.loan_number} - Échéance #{self.installment_number}"
    
    @property
    def balance_due(self):
        """Calculate remaining balance for this installment."""
        return self.total_amount - self.paid_amount
    
    @property
    def is_overdue(self):
        """Check if installment is overdue."""
        from django.utils import timezone
        return self.due_date < timezone.now().date() and self.status != 'paid'
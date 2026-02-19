"""
Cashbox management models for tracking cash movements.
"""

from django.db import models
from django.core.validators import MinValueValidator
from core.models import TimeStampedModel, AuditModel


class Cashbox(AuditModel):
    """
    Cashbox model representing a physical cash register.
    """
    name = models.CharField(max_length=100, verbose_name="Nom")
    code = models.CharField(max_length=20, verbose_name="Code")
    store = models.ForeignKey(
        'inventory.Store',
        on_delete=models.PROTECT,
        related_name='cashboxes',
        verbose_name="Point de vente"
    )
    
    # Current balance
    current_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Solde actuel"
    )
    
    # Status
    is_active = models.BooleanField(default=True, verbose_name="Active")
    
    class Meta:
        verbose_name = "Caisse"
        verbose_name_plural = "Caisses"
        ordering = ['store', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['code'],
                condition=models.Q(is_active=True),
                name='unique_active_cashbox_code'
            )
        ]
    
    def __str__(self):
        return f"{self.code} - {self.name}"


class CashboxSession(AuditModel):
    """
    Cashbox session for tracking opening and closing of cash register.
    """
    STATUS_CHOICES = [
        ('open', 'Ouverte'),
        ('closed', 'Fermée'),
    ]
    
    cashbox = models.ForeignKey(
        Cashbox,
        on_delete=models.PROTECT,
        related_name='sessions',
        verbose_name="Caisse"
    )
    cashier = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='cashbox_sessions',
        verbose_name="Caissier"
    )
    
    # Session details
    opening_date = models.DateTimeField(verbose_name="Date d'ouverture")
    closing_date = models.DateTimeField(null=True, blank=True, verbose_name="Date de fermeture")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='open',
        verbose_name="Statut"
    )
    
    # Opening balance
    opening_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Solde d'ouverture"
    )
    
    # Closing balance
    expected_closing_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Solde de fermeture attendu"
    )
    actual_closing_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Solde de fermeture réel"
    )
    
    # Notes
    opening_notes = models.TextField(blank=True, verbose_name="Notes d'ouverture")
    closing_notes = models.TextField(blank=True, verbose_name="Notes de fermeture")
    
    class Meta:
        verbose_name = "Session de caisse"
        verbose_name_plural = "Sessions de caisse"
        ordering = ['-opening_date']
    
    def __str__(self):
        return f"{self.cashbox.name} - {self.opening_date.date()}"
    
    @property
    def difference(self):
        """Calculate difference between expected and actual closing balance."""
        return self.actual_closing_balance - self.expected_closing_balance


class CashMovement(AuditModel):
    """
    Cash movement model for tracking all cash in/out transactions.
    """
    MOVEMENT_TYPE_CHOICES = [
        ('in', 'Encaissement'),
        ('out', 'Décaissement'),
    ]
    
    CATEGORY_CHOICES = [
        ('sale', 'Vente'),
        ('customer_payment', 'Règlement client'),
        ('supplier_payment', 'Paiement fournisseur'),
        ('loan_repayment', 'Remboursement emprunt'),
        ('loan_disbursement', 'Décaissement emprunt'),
        ('expense', 'Dépense'),
        ('bank_deposit', 'Dépôt en banque'),
        ('bank_withdrawal', 'Retrait banque'),
        ('adjustment', 'Ajustement'),
        ('other', 'Autre'),
    ]
    
    movement_number = models.CharField(max_length=50, unique=True, verbose_name="Numéro de mouvement")
    cashbox_session = models.ForeignKey(
        CashboxSession,
        on_delete=models.PROTECT,
        related_name='movements',
        verbose_name="Session de caisse",
        null=True,
        blank=True
    )
    
    # Movement details
    movement_type = models.CharField(
        max_length=10,
        choices=MOVEMENT_TYPE_CHOICES,
        verbose_name="Type de mouvement"
    )
    category = models.CharField(
        max_length=30,
        choices=CATEGORY_CHOICES,
        verbose_name="Catégorie"
    )
    
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Montant"
    )
    
    # Payment method
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Espèces'),
        ('card', 'Carte bancaire'),
        ('bank_transfer', 'Virement'),
        ('mobile_money', 'Mobile Money (MTN/Orange)'),
        ('check', 'Chèque'),
    ]
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='cash',
        verbose_name="Mode de paiement"
    )
    
    # References
    reference = models.CharField(max_length=100, blank=True, verbose_name="Référence")
    sale = models.ForeignKey(
        'sales.Sale',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cash_movements',
        verbose_name="Vente"
    )
    
    # Description
    description = models.TextField(blank=True, verbose_name="Description")
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    class Meta:
        verbose_name = "Mouvement de caisse"
        verbose_name_plural = "Mouvements de caisse"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.movement_number} - {self.get_movement_type_display()} ({self.amount})"


class CashCount(TimeStampedModel):
    """
    Cash count model for detailed denomination counting.
    """
    cashbox_session = models.ForeignKey(
        CashboxSession,
        on_delete=models.CASCADE,
        related_name='cash_counts',
        verbose_name="Session de caisse"
    )
    
    COUNT_TYPE_CHOICES = [
        ('opening', 'Ouverture'),
        ('closing', 'Fermeture'),
        ('interim', 'Intermédiaire'),
    ]
    count_type = models.CharField(
        max_length=20,
        choices=COUNT_TYPE_CHOICES,
        verbose_name="Type de comptage"
    )
    
    # Denominations
    coins_10000 = models.IntegerField(default=0, verbose_name="Pièces 10000 XAF")
    coins_5000 = models.IntegerField(default=0, verbose_name="Pièces 5000 XAF")
    coins_2000 = models.IntegerField(default=0, verbose_name="Pièces 2000 XAF")
    coins_1000 = models.IntegerField(default=0, verbose_name="Pièces 1000 XAF")
    coins_500 = models.IntegerField(default=0, verbose_name="Pièces 500 XAF")
    coins_250 = models.IntegerField(default=0, verbose_name="Pièces 250 XAF")
    coins_200 = models.IntegerField(default=0, verbose_name="Pièces 200 XAF")
    coins_100 = models.IntegerField(default=0, verbose_name="Pièces 100 XAF")
    coins_50 = models.IntegerField(default=0, verbose_name="Pièces 50 XAF")
    coins_25 = models.IntegerField(default=0, verbose_name="Pièces 25 XAF")
    
    notes_10000 = models.IntegerField(default=0, verbose_name="Billets 10000 XAF")
    notes_5000 = models.IntegerField(default=0, verbose_name="Billets 5000 XAF")
    notes_2000 = models.IntegerField(default=0, verbose_name="Billets 2000 XAF")
    notes_1000 = models.IntegerField(default=0, verbose_name="Billets 1000 XAF")
    notes_500 = models.IntegerField(default=0, verbose_name="Billets 500 XAF")
    
    class Meta:
        verbose_name = "Comptage de caisse"
        verbose_name_plural = "Comptages de caisse"
    
    def __str__(self):
        return f"Comptage {self.get_count_type_display()} - {self.cashbox_session}"
    
    @property
    def total_amount(self):
        """Calculate total amount from denominations."""
        total = 0
        total += self.coins_10000 * 10000
        total += self.coins_5000 * 5000
        total += self.coins_2000 * 2000
        total += self.coins_1000 * 1000
        total += self.coins_500 * 500
        total += self.coins_250 * 250
        total += self.coins_200 * 200
        total += self.coins_100 * 100
        total += self.coins_50 * 50
        total += self.coins_25 * 25
        total += self.notes_10000 * 10000
        total += self.notes_5000 * 5000
        total += self.notes_2000 * 2000
        total += self.notes_1000 * 1000
        total += self.notes_500 * 500
        return total
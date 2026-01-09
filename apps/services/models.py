"""
Service models for service management.
"""

from django.db import models
from django.core.validators import MinValueValidator
from core.models import TimeStampedModel, ActiveModel, AuditModel


class ServiceCategory(ActiveModel, AuditModel):
    """
    Service category model.
    """
    name = models.CharField(max_length=100, unique=True, verbose_name="Désignation")
    description = models.TextField(blank=True, verbose_name="Description")
    
    class Meta:
        verbose_name = "Catégorie de service"
        verbose_name_plural = "Catégories de services"
        ordering = ['name']
        indexes = [
            models.Index(fields=['is_active', 'name']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return self.name


class Service(ActiveModel, AuditModel):
    """
    Service model representing services offered.
    """
    # Basic information
    name = models.CharField(max_length=200, verbose_name="Nom")
    description = models.TextField(blank=True, verbose_name="Description détaillée")
    reference = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Référence"
    )
    
    # Category
    category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.PROTECT,
        related_name='services',
        verbose_name="Catégorie"
    )
    
    # Pricing
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Prix unitaire"
    )
    
    # Tax
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=19.25,
        validators=[MinValueValidator(0)],
        verbose_name="Taux de TVA (%)"
    )
    
    # Duration
    estimated_duration = models.IntegerField(
        null=True,
        blank=True,
        help_text="Durée estimée en minutes",
        verbose_name="Durée estimée (min)"
    )
    
    # Assigned staff
    assigned_staff = models.ManyToManyField(
        'accounts.User',
        blank=True,
        related_name='assigned_services',
        verbose_name="Personnel assigné"
    )
    
    class Meta:
        verbose_name = "Service"
        verbose_name_plural = "Services"
        ordering = ['name']
    
    def __str__(self):
        return f"{self.reference} - {self.name}"
    
    @property
    def unit_price_with_tax(self):
        """Calculate unit price including tax."""
        return self.unit_price * (1 + self.tax_rate / 100)


class ServiceIntervention(AuditModel):
    """
    Service intervention/appointment model.
    """
    STATUS_CHOICES = [
        ('scheduled', 'Planifié'),
        ('in_progress', 'En cours'),
        ('completed', 'Terminé'),
        ('cancelled', 'Annulé'),
    ]
    
    service = models.ForeignKey(
        Service,
        on_delete=models.PROTECT,
        related_name='interventions',
        verbose_name="Service"
    )
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.PROTECT,
        related_name='service_interventions',
        verbose_name="Client"
    )
    assigned_to = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='interventions',
        null=True,
        blank=True,
        verbose_name="Assigné à"
    )
    
    # Scheduling
    scheduled_date = models.DateField(verbose_name="Date planifiée")
    scheduled_time = models.TimeField(null=True, blank=True, verbose_name="Heure planifiée")
    actual_start = models.DateTimeField(null=True, blank=True, verbose_name="Début réel")
    actual_end = models.DateTimeField(null=True, blank=True, verbose_name="Fin réelle")
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='scheduled',
        verbose_name="Statut"
    )
    
    # Pricing
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=1,
        validators=[MinValueValidator(0)],
        verbose_name="Quantité"
    )
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Prix unitaire"
    )
    
    # Notes
    notes = models.TextField(blank=True, verbose_name="Notes")
    internal_notes = models.TextField(blank=True, verbose_name="Notes internes")
    
    # Quality assessment
    quality_rating = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
        help_text="Note de 1 à 5",
        verbose_name="Évaluation qualité"
    )
    quality_comments = models.TextField(blank=True, verbose_name="Commentaires qualité")
    
    class Meta:
        verbose_name = "Intervention"
        verbose_name_plural = "Interventions"
        ordering = ['-scheduled_date', '-scheduled_time']
    
    def __str__(self):
        return f"{self.service.name} - {self.customer} ({self.scheduled_date})"
    
    @property
    def total_price(self):
        """Calculate total price."""
        return self.unit_price * self.quantity
    
    @property
    def total_price_with_tax(self):
        """Calculate total price including tax."""
        return self.total_price * (1 + self.service.tax_rate / 100)
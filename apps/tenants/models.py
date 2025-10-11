"""
Tenant models for multi-tenancy support.
"""

from django.db import models
from django_tenants.models import TenantMixin, DomainMixin


class Company(TenantMixin):
    """
    Company/Tenant model representing each client company.
    Each company has its own schema in PostgreSQL.
    """
    name = models.CharField(max_length=100, verbose_name="Nom de l'entreprise")
    created_on = models.DateField(auto_now_add=True, verbose_name="Date de création")
    
    # Contact information
    email = models.EmailField(verbose_name="Email principal")
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Téléphone")
    address = models.TextField(blank=True, null=True, verbose_name="Adresse")
    
    # Subscription information
    PLAN_CHOICES = [
        ('starter', 'Starter'),
        ('business', 'Business'),
        ('enterprise', 'Enterprise'),
        ('custom', 'Custom'),
    ]
    plan = models.CharField(
        max_length=20,
        choices=PLAN_CHOICES,
        default='starter',
        verbose_name="Plan d'abonnement"
    )
    
    # Limits based on plan
    max_users = models.IntegerField(default=3, verbose_name="Nombre max d'utilisateurs")
    max_stores = models.IntegerField(default=1, verbose_name="Nombre max de points de vente")
    max_products = models.IntegerField(default=1000, verbose_name="Nombre max de produits")
    max_storage_mb = models.IntegerField(default=1000, verbose_name="Stockage max (MB)")
    
    # Feature flags
    feature_services = models.BooleanField(default=False, verbose_name="Module Services")
    feature_multi_store = models.BooleanField(default=False, verbose_name="Multi points de vente")
    feature_loans = models.BooleanField(default=False, verbose_name="Gestion des emprunts")
    feature_advanced_analytics = models.BooleanField(default=False, verbose_name="Analytics avancés")
    feature_api_access = models.BooleanField(default=False, verbose_name="Accès API")
    
    # Status
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    trial_end_date = models.DateField(null=True, blank=True, verbose_name="Fin de période d'essai")
    
    # Settings
    currency = models.CharField(max_length=3, default='XAF', verbose_name="Devise")
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=19.25,
        verbose_name="Taux de TVA (%)"
    )
    
    # Automatically create schema
    auto_create_schema = True
    auto_drop_schema = False
    
    class Meta:
        verbose_name = "Société (Tenant)"
        verbose_name_plural = "Sociétés (Tenants)"
    
    def __str__(self):
        return self.name
    
    def can_add_user(self):
        """Check if tenant can add more users."""
        from apps.accounts.models import User
        current_users = User.objects.filter(tenant=self).count()
        return current_users < self.max_users
    
    def can_add_store(self):
        """Check if tenant can add more stores."""
        from apps.inventory.models import Store
        current_stores = Store.objects.count()
        return current_stores < self.max_stores
    
    def has_feature(self, feature_name):
        """Check if tenant has access to a specific feature."""
        return getattr(self, f'feature_{feature_name}', False)


class Domain(DomainMixin):
    """
    Domain model for tenant routing.
    Each tenant can have multiple domains.
    """
    
    class Meta:
        verbose_name = "Domaine"
        verbose_name_plural = "Domaines"
    
    def __str__(self):
        return self.domain
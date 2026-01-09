"""
Tenant models for multi-tenancy support.
"""

from django.db import models
from django.contrib.auth.models import User as DjangoUser
from django.utils import timezone
from django.core.validators import MaxValueValidator, MinValueValidator
from django_tenants.models import TenantMixin, DomainMixin
from decimal import Decimal


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
    is_suspended = models.BooleanField(default=False, verbose_name="Suspendu")
    suspension_reason = models.TextField(blank=True, null=True, verbose_name="Raison suspension")
    
    # Provisioning status
    PROVISIONING_CHOICES = [
        ('pending', 'En attente'),
        ('in_progress', 'En cours'),
        ('completed', 'Terminé'),
        ('failed', 'Échoué'),
    ]
    provisioning_status = models.CharField(
        max_length=20,
        choices=PROVISIONING_CHOICES,
        default='pending',
        verbose_name="Statut du provisioning"
    )
    trial_end_date = models.DateField(null=True, blank=True, verbose_name="Fin de période d'essai")
    subscription_end_date = models.DateField(null=True, blank=True, verbose_name="Fin d'abonnement")
    
    # Billing
    billing_email = models.EmailField(blank=True, null=True, verbose_name="Email facturation")
    monthly_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Prix mensuel"
    )
    last_payment_date = models.DateField(null=True, blank=True, verbose_name="Dernière facture")
    next_billing_date = models.DateField(null=True, blank=True, verbose_name="Prochaine facturation")
    
    # Metrics and monitoring
    storage_used_mb = models.IntegerField(default=0, verbose_name="Stockage utilisé (MB)")
    last_activity_date = models.DateTimeField(null=True, blank=True, verbose_name="Dernière activité")
    total_users_count = models.IntegerField(default=0, verbose_name="Nombre d'utilisateurs")
    total_products_count = models.IntegerField(default=0, verbose_name="Nombre de produits")
    
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
        # Note: Import local pour éviter les conflits de modèles
        try:
            from apps.accounts.models import User
            current_users = User.objects.count()  # Dans le schéma du tenant
        except:
            current_users = self.total_users_count or 0
        return current_users < self.max_users
    
    def can_add_store(self):
        """Check if tenant can add more stores."""
        from apps.inventory.models import Store
        current_stores = Store.objects.count()
        return current_stores < self.max_stores
    
    def has_feature(self, feature_name):
        """Check if tenant has access to a specific feature."""
        return getattr(self, f'feature_{feature_name}', False)
    
    def is_trial_expired(self):
        """Check if trial period has expired."""
        if not self.trial_end_date:
            return False
        return timezone.now().date() > self.trial_end_date
    
    def is_subscription_expired(self):
        """Check if subscription has expired."""
        if not self.subscription_end_date:
            return False
        return timezone.now().date() > self.subscription_end_date
    
    def days_until_expiration(self):
        """Get days until subscription expires."""
        if not self.subscription_end_date:
            return None
        diff = self.subscription_end_date - timezone.now().date()
        return diff.days if diff.days >= 0 else 0
    
    def get_usage_percentage(self, resource_type):
        """Get usage percentage for a resource type."""
        if resource_type == 'users':
            return (self.total_users_count / self.max_users) * 100 if self.max_users > 0 else 0
        elif resource_type == 'storage':
            return (self.storage_used_mb / self.max_storage_mb) * 100 if self.max_storage_mb > 0 else 0
        elif resource_type == 'products':
            return (self.total_products_count / self.max_products) * 100 if self.max_products > 0 else 0
        return 0
    
    def get_plan_price(self):
        """Retourne le prix mensuel selon le plan."""
        prices = {
            'starter': Decimal('15000.00'),
            'business': Decimal('40000.00'),
            'enterprise': Decimal('60000.00'),
        }
        return prices.get(self.plan, Decimal('15000.00'))
    
    def save(self, *args, **kwargs):
        """Override save pour mettre à jour le prix automatiquement."""
        # Pour les plans prédéfinis, toujours recalculer le prix
        if self.plan in ['starter', 'business', 'enterprise']:
            self.monthly_price = self.get_plan_price()
        # Pour le plan 'custom', conserver le prix manuel (sauf s'il est à 0)
        elif self.plan == 'custom':
            if self.monthly_price == Decimal('0.00'):
                self.monthly_price = Decimal('15000.00')
        
        super().save(*args, **kwargs)


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


class CompanyBilling(models.Model):
    """
    Billing information and invoice tracking for each tenant.
    """
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='billings')
    
    # Invoice details
    invoice_number = models.CharField(max_length=50, unique=True, verbose_name="Numéro facture")
    invoice_date = models.DateField(verbose_name="Date facture")
    due_date = models.DateField(verbose_name="Date d'échéance")
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Montant")
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Montant TVA")
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Total TTC")
    
    # Status
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('paid', 'Payé'),
        ('overdue', 'En retard'),
        ('cancelled', 'Annulé'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_date = models.DateField(null=True, blank=True, verbose_name="Date paiement")
    payment_method = models.CharField(max_length=50, blank=True, verbose_name="Méthode paiement")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    class Meta:
        verbose_name = "Facturation"
        verbose_name_plural = "Facturations"
        ordering = ['-invoice_date']
    
    def __str__(self):
        return f"Facture {self.invoice_number} - {self.company.name}"
    
    def is_overdue(self):
        """Check if invoice is overdue."""
        return self.status == 'pending' and timezone.now().date() > self.due_date


class AuditLog(models.Model):
    """
    Audit log for tracking admin actions and system events.
    """
    # Target
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True, related_name='audit_logs')
    admin_user = models.CharField(max_length=150, verbose_name="Utilisateur admin")
    
    # Action details
    action_type = models.CharField(max_length=50, verbose_name="Type d'action")
    action_description = models.TextField(verbose_name="Description")
    resource_type = models.CharField(max_length=50, blank=True, verbose_name="Type de ressource")
    resource_id = models.CharField(max_length=100, blank=True, verbose_name="ID ressource")
    
    # Metadata
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Changes tracking
    old_values = models.JSONField(null=True, blank=True, verbose_name="Anciennes valeurs")
    new_values = models.JSONField(null=True, blank=True, verbose_name="Nouvelles valeurs")
    
    class Meta:
        verbose_name = "Log d'audit"
        verbose_name_plural = "Logs d'audit"
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.admin_user} - {self.action_type} - {self.timestamp}"


class SupportTicket(models.Model):
    """
    Support ticket system for customer support.
    """
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='support_tickets')
    
    # Ticket details
    ticket_number = models.CharField(max_length=20, unique=True, verbose_name="Numéro ticket")
    title = models.CharField(max_length=200, verbose_name="Titre")
    description = models.TextField(verbose_name="Description")
    
    # Priority and status
    PRIORITY_CHOICES = [
        ('low', 'Faible'),
        ('normal', 'Normale'),
        ('high', 'Élevée'),
        ('urgent', 'Urgente'),
    ]
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal')
    
    STATUS_CHOICES = [
        ('open', 'Ouvert'),
        ('in_progress', 'En cours'),
        ('waiting_customer', 'En attente client'),
        ('resolved', 'Résolu'),
        ('closed', 'Fermé'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    
    # Assignation
    assigned_to = models.CharField(max_length=150, blank=True, verbose_name="Assigné à")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    # Customer info
    customer_name = models.CharField(max_length=150, verbose_name="Nom client")
    customer_email = models.EmailField(verbose_name="Email client")
    
    class Meta:
        verbose_name = "Ticket support"
        verbose_name_plural = "Tickets support"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Ticket #{self.ticket_number} - {self.title}"
    
    def save(self, *args, **kwargs):
        if not self.ticket_number:
            # Générer un numéro de ticket unique
            import random, string
            self.ticket_number = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        super().save(*args, **kwargs)


class SystemMetrics(models.Model):
    """
    System-wide metrics and monitoring data.
    """
    # Timestamp
    recorded_at = models.DateTimeField(auto_now_add=True)
    
    # Global metrics
    total_tenants = models.IntegerField(default=0)
    active_tenants = models.IntegerField(default=0)
    total_users = models.IntegerField(default=0)
    total_revenue_monthly = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Performance metrics
    avg_response_time_ms = models.IntegerField(default=0, verbose_name="Temps de réponse moyen (ms)")
    error_rate_percent = models.FloatField(default=0, verbose_name="Taux d'erreur (%)")
    
    # Resource usage
    total_storage_used_gb = models.FloatField(default=0, verbose_name="Stockage total utilisé (GB)")
    peak_concurrent_users = models.IntegerField(default=0, verbose_name="Pic utilisateurs simultanés")
    
    class Meta:
        verbose_name = "Métriques système"
        verbose_name_plural = "Métriques système"
        ordering = ['-recorded_at']
    
    def __str__(self):
        return f"Métriques {self.recorded_at}"
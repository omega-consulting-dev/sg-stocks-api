"""
Complete User and Role models for authentication and authorization.
Gestion de tous les utilisateurs d'un tenant (clients, collaborateurs, fournisseurs)
"""

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
from django_tenants.utils import tenant_context
from core.models import TimeStampedModel


class UserManager(BaseUserManager):
    """Custom user manager."""
    
    def create_user(self, username, email=None, password=None, **extra_fields):
        """Create and return a regular user."""
        if not username:
            raise ValueError("Le nom d'utilisateur est obligatoire")
        
        email = self.normalize_email(email) if email else None
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        """Create and return a superuser."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_collaborator', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(username, email, password, **extra_fields)


class Role(TimeStampedModel):
    """
    Role model for defining user permissions.
    """
    ROLE_CHOICES = [
        ('super_admin', 'Super Administrateur'),
        ('manager', 'Gérant/Directeur'),
        ('store_manager', 'Responsable Point de Vente'),
        ('warehouse_keeper', 'Magasinier'),
        ('cashier', 'Caissier'),
        ('salesperson', 'Vendeur'),
        ('accountant', 'Comptable'),
        ('commercial', 'Commercial'),
    ]
    
    name = models.CharField(max_length=50, choices=ROLE_CHOICES, unique=True, verbose_name="Nom du rôle")
    display_name = models.CharField(max_length=100, verbose_name="Nom d'affichage")
    description = models.TextField(blank=True, verbose_name="Description")
    
    # Permissions flags
    can_manage_users = models.BooleanField(default=False, verbose_name="Gérer les utilisateurs")
    can_manage_products = models.BooleanField(default=False, verbose_name="Gérer les produits")
    can_manage_services = models.BooleanField(default=False, verbose_name="Gérer les services")
    can_manage_inventory = models.BooleanField(default=False, verbose_name="Gérer le stock")
    can_manage_sales = models.BooleanField(default=False, verbose_name="Gérer les ventes")
    can_manage_customers = models.BooleanField(default=False, verbose_name="Gérer les clients")
    can_manage_suppliers = models.BooleanField(default=False, verbose_name="Gérer les fournisseurs")
    can_manage_cashbox = models.BooleanField(default=False, verbose_name="Gérer la caisse")
    can_manage_loans = models.BooleanField(default=False, verbose_name="Gérer les emprunts")
    can_manage_expenses = models.BooleanField(default=False, verbose_name="Gérer les dépenses")
    can_view_analytics = models.BooleanField(default=False, verbose_name="Voir les analytics")
    can_export_data = models.BooleanField(default=False, verbose_name="Exporter les données")
    
    # Access scope
    ACCESS_SCOPE_CHOICES = [
        ('all', 'Tous les points de vente'),
        ('assigned', 'Points de vente assignés uniquement'),
        ('own', 'Propres données uniquement'),
    ]
    access_scope = models.CharField(
        max_length=20,
        choices=ACCESS_SCOPE_CHOICES,
        default='assigned',
        verbose_name="Périmètre d'accès"
    )
    
    class Meta:
        verbose_name = "Rôle"
        verbose_name_plural = "Rôles"
    
    def __str__(self):
        return self.display_name


class User(AbstractUser, TimeStampedModel):
    """
    Custom User model - Représente TOUS les utilisateurs du système.
    Peut être : collaborateur, client, fournisseur, ou une combinaison.
    """
    
    objects = UserManager()
    
    # Type d'utilisateur
    USER_TYPE_CHOICES = [
        ('collaborator', 'Collaborateur'),
        ('customer', 'Client'),
        ('supplier', 'Fournisseur'),
        ('customer_supplier', 'Client et Fournisseur'),
    ]
    user_type = models.CharField(
        max_length=20,
        choices=USER_TYPE_CHOICES,
        default='collaborator',
        verbose_name="Type d'utilisateur"
    )
    
    # Basic information
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Format: '+237612345678'. 9 à 15 chiffres."
    )
    phone = models.CharField(
        validators=[phone_regex],
        max_length=17,
        blank=True,
        verbose_name="Téléphone"
    )
    avatar = models.ImageField(
        upload_to='avatars/%Y/%m/',
        null=True,
        blank=True,
        verbose_name="Photo de profil"
    )
    
    # Address information
    address = models.TextField(blank=True, verbose_name="Adresse")
    city = models.CharField(max_length=100, blank=True, verbose_name="Ville")
    postal_code = models.CharField(max_length=20, blank=True, verbose_name="Code postal")
    country = models.CharField(max_length=100, default='Cameroun', verbose_name="Pays")
    
    # Employee information (pour collaborateurs)
    is_collaborator = models.BooleanField(default=True, verbose_name="Est un collaborateur")
    employee_id = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        verbose_name="Matricule employé"
    )
    
    # Role and permissions (pour collaborateurs)
    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        related_name='users',
        null=True,
        blank=True,
        verbose_name="Rôle principal"
    )
    secondary_roles = models.ManyToManyField(
        Role,
        related_name='secondary_users',
        blank=True,
        verbose_name="Rôles secondaires"
    )
    
    # Store assignments (pour collaborateurs)
    assigned_stores = models.ManyToManyField(
        'inventory.Store',
        blank=True,
        related_name='assigned_users',
        verbose_name="Points de vente assignés"
    )
    
    # Customer information (pour clients)
    is_customer = models.BooleanField(default=False, verbose_name="Est un client")
    customer_code = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        verbose_name="Code client"
    )
    customer_company_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Raison sociale (client)"
    )
    customer_tax_id = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Numéro fiscal (client)"
    )
    customer_credit_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Limite de crédit"
    )
    customer_payment_term = models.CharField(
        max_length=20,
        choices=[
            ('immediate', 'Comptant'),
            ('15_days', '15 jours'),
            ('30_days', '30 jours'),
            ('60_days', '60 jours'),
            ('90_days', '90 jours'),
        ],
        default='immediate',
        blank=True,
        verbose_name="Conditions de paiement"
    )
    
    # Supplier information (pour fournisseurs)
    is_supplier = models.BooleanField(default=False, verbose_name="Est un fournisseur")
    supplier_code = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        verbose_name="Code fournisseur"
    )
    supplier_company_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Raison sociale (fournisseur)"
    )
    supplier_tax_id = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Numéro fiscal (fournisseur)"
    )
    supplier_bank_account = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Compte bancaire (fournisseur)"
    )
    supplier_rating = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Évaluation fournisseur"
    )
    
    # Employment status (pour collaborateurs)
    is_active_employee = models.BooleanField(default=True, verbose_name="Employé actif")
    hire_date = models.DateField(null=True, blank=True, verbose_name="Date d'embauche")
    termination_date = models.DateField(null=True, blank=True, verbose_name="Date de départ")
    
    # Additional contact
    alternative_phone = models.CharField(
        validators=[phone_regex],
        max_length=17,
        blank=True,
        verbose_name="Téléphone alternatif"
    )
    emergency_contact_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Contact d'urgence"
    )
    emergency_contact_phone = models.CharField(
        validators=[phone_regex],
        max_length=17,
        blank=True,
        verbose_name="Téléphone du contact d'urgence"
    )
    
    # Notes
    notes = models.TextField(blank=True, verbose_name="Notes")

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"
        ordering = ['-date_joined']
        indexes = [
            models.Index(fields=['user_type']),
            models.Index(fields=['customer_code']),
            models.Index(fields=['supplier_code']),
            models.Index(fields=['employee_id']),
        ]
    
    def __str__(self):
        if self.is_collaborator:
            return f"{self.get_full_name()} ({self.username})"
        elif self.is_customer:
            return f"{self.customer_company_name or self.get_full_name()} - Client"
        elif self.is_supplier:
            return f"{self.supplier_company_name or self.get_full_name()} - Fournisseur"
        return self.username
    
    
    def get_all_roles(self):
        """Get all roles (primary + secondary)."""
        roles = list(self.secondary_roles.all())
        if self.role:
            roles.insert(0, self.role)
        return roles
    
    def has_permission(self, permission_name):
        """Check if user has a specific permission."""
        if self.is_superuser:
            return True
        
        for role in self.get_all_roles():
            if getattr(role, permission_name, False):
                return True
        return False
    
    def get_accessible_stores(self):
        """Get stores accessible to this user based on role."""
        if self.is_superuser or (self.role and self.role.access_scope == 'all'):
            from apps.inventory.models import Store
            return Store.objects.all()
        
        return self.assigned_stores.all()
    
    def get_display_name(self):
        """Get the best display name for this user."""
        if self.is_customer and self.customer_company_name:
            return self.customer_company_name
        elif self.is_supplier and self.supplier_company_name:
            return self.supplier_company_name
        elif self.get_full_name():
            return self.get_full_name()
        return self.username
    
    def get_customer_balance(self):
        """Calculate customer account balance."""
        if not self.is_customer:
            return 0
        
        from apps.invoicing.models import Invoice
        from django.db.models import Sum
        
        invoices = Invoice.objects.filter(customer__user=self)
        total_invoiced = invoices.aggregate(
            total=Sum('total_amount')
        )['total'] or 0
        
        total_paid = invoices.aggregate(
            total=Sum('paid_amount')
        )['total'] or 0
        
        return total_invoiced - total_paid
    
    def get_supplier_balance(self):
        """Calculate supplier account balance (what we owe)."""
        if not self.is_supplier:
            return 0
        
        from apps.suppliers.models import PurchaseOrder
        from django.db.models import Sum
        
        orders = PurchaseOrder.objects.filter(
            supplier__user=self,
            status='confirmed'
        )
        
        total_ordered = orders.aggregate(
            total=Sum('total_amount')
        )['total'] or 0
        
        total_paid = orders.aggregate(
            total=Sum('paid_amount')
        )['total'] or 0
        
        return total_ordered - total_paid
    
    def can_access_store(self, store):
        """Check if user has access to a specific store."""
        if self.is_superuser:
            return True
        
        if self.role and self.role.access_scope == 'all':
            return True
        
        return self.assigned_stores.filter(id=store.id).exists()


class Permission(TimeStampedModel):
    """
    Custom permission model for granular access control.
    """
    name = models.CharField(max_length=100, unique=True, verbose_name="Nom")
    codename = models.CharField(max_length=100, unique=True, verbose_name="Code")
    description = models.TextField(blank=True, verbose_name="Description")
    
    # Module
    MODULE_CHOICES = [
        ('products', 'Produits'),
        ('services', 'Services'),
        ('inventory', 'Stock'),
        ('sales', 'Ventes'),
        ('customers', 'Clients'),
        ('suppliers', 'Fournisseurs'),
        ('cashbox', 'Caisse'),
        ('loans', 'Emprunts'),
        ('expenses', 'Dépenses'),
        ('analytics', 'Analytics'),
        ('settings', 'Paramètres'),
        ('users', 'Utilisateurs'),
    ]
    module = models.CharField(max_length=50, choices=MODULE_CHOICES, verbose_name="Module")
    
    # Action
    ACTION_CHOICES = [
        ('view', 'Voir'),
        ('add', 'Ajouter'),
        ('change', 'Modifier'),
        ('delete', 'Supprimer'),
        ('export', 'Exporter'),
        ('approve', 'Approuver'),
    ]
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name="Action")
    
    roles = models.ManyToManyField(Role, related_name='permissions', blank=True)
    
    class Meta:
        verbose_name = "Permission"
        verbose_name_plural = "Permissions"
        unique_together = [['module', 'action']]
    
    def __str__(self):
        return f"{self.get_action_display()} - {self.get_module_display()}"


class UserSession(TimeStampedModel):
    """
    Track user sessions for security and audit.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sessions',
        verbose_name="Utilisateur"
    )
    session_key = models.CharField(max_length=40, unique=True, verbose_name="Clé de session")
    ip_address = models.GenericIPAddressField(verbose_name="Adresse IP")
    user_agent = models.TextField(verbose_name="User Agent")
    login_time = models.DateTimeField(auto_now_add=True, verbose_name="Heure de connexion")
    logout_time = models.DateTimeField(null=True, blank=True, verbose_name="Heure de déconnexion")
    is_active = models.BooleanField(default=True, verbose_name="Session active")
    
    class Meta:
        verbose_name = "Session utilisateur"
        verbose_name_plural = "Sessions utilisateurs"
        ordering = ['-login_time']
    
    def __str__(self):
        return f"{self.user.username} - {self.login_time}"


class UserActivity(TimeStampedModel):
    """
    Log user activities for audit trail.
    """
    ACTION_CHOICES = [
        ('login', 'Connexion'),
        ('logout', 'Déconnexion'),
        ('create', 'Création'),
        ('update', 'Modification'),
        ('delete', 'Suppression'),
        ('view', 'Consultation'),
        ('export', 'Export'),
        ('print', 'Impression'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='activities',
        verbose_name="Utilisateur"
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name="Action")
    module = models.CharField(max_length=50, verbose_name="Module")
    object_type = models.CharField(max_length=100, blank=True, verbose_name="Type d'objet")
    object_id = models.PositiveIntegerField(null=True, blank=True, verbose_name="ID objet")
    description = models.TextField(verbose_name="Description")
    ip_address = models.GenericIPAddressField(verbose_name="Adresse IP")
    
    class Meta:
        verbose_name = "Activité utilisateur"
        verbose_name_plural = "Activités utilisateurs"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['action', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.get_action_display()} - {self.module}"
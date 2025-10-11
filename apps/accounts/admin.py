"""
Accounts admin configuration.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from apps.accounts.models import User, Role, Permission, UserSession, UserActivity


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    """Admin for Role model."""
    
    list_display = ['display_name', 'name', 'access_scope', 'users_count', 'created_at']
    list_filter = ['access_scope', 'created_at']
    search_fields = ['name', 'display_name', 'description']
    # filter_horizontal = ['permissions']
    
    fieldsets = (
        ('Informations de base', {
            'fields': ('name', 'display_name', 'description', 'access_scope')
        }),
        ('Permissions - Gestion', {
            'fields': (
                'can_manage_users',
                'can_manage_products',
                'can_manage_services',
                'can_manage_inventory',
                'can_manage_sales',
            )
        }),
        ('Permissions - Partenaires', {
            'fields': (
                'can_manage_customers',
                'can_manage_suppliers',
            )
        }),
        ('Permissions - Finance', {
            'fields': (
                'can_manage_cashbox',
                'can_manage_loans',
                'can_manage_expenses',
            )
        }),
        ('Permissions - Autres', {
            'fields': (
                'can_view_analytics',
                'can_export_data',
            )
        }),
        ('Permissions granulaires', {
            'fields': ('permissions',),
            'classes': ('collapse',)
        }),
        ('Audit', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def users_count(self, obj):
        """Count users with this role."""
        return obj.users.count()
    users_count.short_description = "Nombre d'utilisateurs"


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin for User model."""
    
    list_display = [
        'username', 'email', 'display_name_colored', 'user_type_badge',
        'role', 'is_active', 'is_active_employee', 'date_joined'
    ]
    list_filter = [
        'user_type', 'is_active', 'is_active_employee', 'is_staff',
        'is_collaborator', 'is_customer', 'is_supplier',
        'role', 'date_joined'
    ]
    search_fields = [
        'username', 'email', 'first_name', 'last_name',
        'customer_code', 'customer_company_name',
        'supplier_code', 'supplier_company_name',
        'employee_id', 'phone'
    ]
    ordering = ['-date_joined']
    filter_horizontal = ['secondary_roles', 'assigned_stores', 'groups', 'user_permissions']
    
    fieldsets = (
        ('Authentification', {
            'fields': ('username', 'password', 'email')
        }),
        ('Informations personnelles', {
            'fields': (
                'first_name', 'last_name', 'phone', 'alternative_phone',
                'avatar', 'address', 'city', 'postal_code', 'country'
            )
        }),
        ('Type d\'utilisateur', {
            'fields': (
                'user_type', 'is_collaborator', 'is_customer', 'is_supplier'
            )
        }),
        ('Collaborateur', {
            'fields': (
                'employee_id', 'role', 'secondary_roles', 'assigned_stores',
                'hire_date', 'termination_date', 'is_active_employee'
            ),
            'classes': ('collapse',)
        }),
        ('Client', {
            'fields': (
                'customer_code', 'customer_company_name', 'customer_tax_id',
                'customer_credit_limit', 'customer_payment_term'
            ),
            'classes': ('collapse',)
        }),
        ('Fournisseur', {
            'fields': (
                'supplier_code', 'supplier_company_name', 'supplier_tax_id',
                'supplier_bank_account', 'supplier_rating'
            ),
            'classes': ('collapse',)
        }),
        ('Contact d\'urgence', {
            'fields': ('emergency_contact_name', 'emergency_contact_phone'),
            'classes': ('collapse',)
        }),
        ('Permissions Django', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('Dates importantes', {
            'fields': ('date_joined', 'last_login', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = (
        ('Authentification', {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2'),
        }),
        ('Type d\'utilisateur', {
            'fields': (
                'user_type', 'is_collaborator', 'is_customer', 'is_supplier'
            )
        }),
        ('Informations de base', {
            'fields': ('first_name', 'last_name', 'phone')
        }),
    )
    
    readonly_fields = ['date_joined', 'last_login', 'created_at', 'updated_at']
    
    def display_name_colored(self, obj):
        """Display name with color based on status."""
        color = 'green' if obj.is_active else 'red'
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            obj.get_display_name()
        )
    display_name_colored.short_description = "Nom d'affichage"
    
    def user_type_badge(self, obj):
        """Display user type as badge."""
        colors = {
            'collaborator': '#17a2b8',
            'customer': '#28a745',
            'supplier': '#ffc107',
            'customer_supplier': '#6c757d',
        }
        color = colors.get(obj.user_type, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color,
            obj.get_user_type_display()
        )
    user_type_badge.short_description = "Type"
    
    def get_queryset(self, request):
        """Optimize queryset."""
        qs = super().get_queryset(request)
        return qs.select_related('role').prefetch_related('secondary_roles', 'assigned_stores')


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    """Admin for Permission model."""
    
    list_display = ['name', 'codename', 'module', 'action', 'roles_count', 'created_at']
    list_filter = ['module', 'action', 'created_at']
    search_fields = ['name', 'codename', 'description']
    filter_horizontal = ['roles']
    ordering = ['module', 'action']
    
    fieldsets = (
        ('Informations de base', {
            'fields': ('name', 'codename', 'description')
        }),
        ('Classification', {
            'fields': ('module', 'action')
        }),
        ('Rôles', {
            'fields': ('roles',)
        }),
        ('Audit', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def roles_count(self, obj):
        """Count roles with this permission."""
        return obj.roles.count()
    roles_count.short_description = "Nombre de rôles"


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    """Admin for UserSession model."""
    
    list_display = [
        'user', 'ip_address', 'login_time', 'logout_time',
        'is_active', 'duration_display'
    ]
    list_filter = ['is_active', 'login_time']
    search_fields = ['user__username', 'user__email', 'ip_address']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-login_time']
    
    fieldsets = (
        ('Utilisateur', {
            'fields': ('user',)
        }),
        ('Session', {
            'fields': ('session_key', 'is_active')
        }),
        ('Connexion', {
            'fields': ('ip_address', 'user_agent', 'login_time', 'logout_time')
        }),
        ('Audit', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def duration_display(self, obj):
        """Display session duration."""
        if obj.logout_time:
            delta = obj.logout_time - obj.login_time
            hours = int(delta.total_seconds() // 3600)
            minutes = int((delta.total_seconds() % 3600) // 60)
            return f"{hours}h {minutes}min"
        return "En cours"
    duration_display.short_description = "Durée"
    
    def has_add_permission(self, request):
        """Disable manual session creation."""
        return False


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    """Admin for UserActivity model."""
    
    list_display = [
        'user', 'action_display_colored', 'module', 'object_type',
        'ip_address', 'created_at'
    ]
    list_filter = ['action', 'module', 'created_at']
    search_fields = [
        'user__username', 'user__email', 'description',
        'module', 'object_type', 'ip_address'
    ]
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Utilisateur', {
            'fields': ('user', 'ip_address')
        }),
        ('Action', {
            'fields': ('action', 'module', 'object_type', 'object_id', 'description')
        }),
        ('Audit', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def action_display_colored(self, obj):
        """Display action with color."""
        colors = {
            'login': '#17a2b8',
            'logout': '#6c757d',
            'create': '#28a745',
            'update': '#ffc107',
            'delete': '#dc3545',
            'view': '#007bff',
            'export': '#6f42c1',
            'print': '#fd7e14',
        }
        color = colors.get(obj.action, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_action_display()
        )
    action_display_colored.short_description = "Action"
    
    def has_add_permission(self, request):
        """Disable manual activity creation."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Disable activity modification."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Only superusers can delete activities."""
        return request.user.is_superuser
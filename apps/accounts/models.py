from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.utils.translation import gettext_lazy as _

# from guardian.mixins import GuardianUserMixin
# from apps.tenants.models import Company

class User(AbstractUser):
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, validators=[UnicodeUsernameValidator()],)

    groups = models.ManyToManyField(
        Group,
        verbose_name=_("groups"),
        blank=True,
        help_text=_(
            "The groups this user belongs to. A user will get all permissions "
            "granted to each of their groups."
        ),
        related_name="tenant_user_set",
        related_query_name="user",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name=_("user permissions"),
        blank=True,
        help_text=_("Specific permissions for this user."),
        related_name="tenant_user_set",
        related_query_name="user",
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

# class Role(models.Model):
#     name = models.CharField(max_length=50, unique=True)  # e.g., 'gérant', 'caissier'
#     permissions = models.ManyToManyField('auth.Permission')

# class User(GuardianUserMixin, AbstractUser):
#     tenant = models.ForeignKey(Company, on_delete=models.CASCADE)
#     phone = models.CharField(max_length=20, blank=True)
#     avatar = models.ImageField(upload_to='avatars/', blank=True)
#     is_collaborator = models.BooleanField(default=True)
#     employee_id = models.CharField(max_length=50, unique=True, blank=True)
#     roles = models.ManyToManyField(Role, blank=True)
#     assigned_stores = models.ManyToManyField('inventory.Store', blank=True)
#     assigned_warehouses = models.ManyToManyField('inventory.Warehouse', blank=True)
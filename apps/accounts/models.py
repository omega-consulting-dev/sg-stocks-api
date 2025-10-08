from django.contrib.auth.models import AbstractUser
from django.db import models
from guardian.mixins import GuardianUserMixin
from apps.tenants.models import Company

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
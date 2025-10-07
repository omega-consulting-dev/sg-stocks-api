from django.db import models
from django_tenants.models import TenantMixin, DomainMixin
from django.core.validators import MinValueValidator

class Company(TenantMixin):
    name = models.CharField(max_length=100)
    created_on = models.DateField(auto_now_add=True)
    plan = models.CharField(max_length=50, default='starter')
    max_users = models.IntegerField(default=3, validators=[MinValueValidator(1)])
    max_stores = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    is_active = models.BooleanField(default=True)
    trial_end_date = models.DateField(null=True, blank=True)
    
    # Features toggling
    feature_services = models.BooleanField(default=False)
    feature_multi_store = models.BooleanField(default=False)
    feature_loans = models.BooleanField(default=False)
    
    auto_create_schema = True

class Domain(DomainMixin):
    pass
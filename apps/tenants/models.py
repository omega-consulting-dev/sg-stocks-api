# tenants/models.py
from django.db import models
from django_tenants.models import TenantMixin, DomainMixin
from django.utils.translation import gettext_lazy as _

class Company(TenantMixin):
    """
    Représente un Tenant (une entreprise qui utilise la solution).
    Chaque instance crée son propre schéma PostgreSQL.
    """
    name = models.CharField(_("Nom de l'entreprise"), max_length=100)
    created_on = models.DateField(auto_now_add=True)
    
    # Informations de facturation/Plan
    plan = models.CharField(_("Plan tarifaire"), max_length=50, default='Starter')
    max_users = models.IntegerField(_("Max. utilisateurs"), default=3)
    max_stores = models.IntegerField(_("Max. points de vente"), default=1)
    
    # Statut
    is_active = models.BooleanField(_("Actif"), default=True)
    trial_end_date = models.DateField(_("Fin de période d'essai"), null=True, blank=True)
    
    # Features activées (pour Feature Toggling)
    feature_services = models.BooleanField(_("Gestion des services"), default=False)
    feature_multi_store = models.BooleanField(_("Multi-points de vente"), default=False)
    feature_loans = models.BooleanField(_("Gestion des emprunts"), default=False)
    feature_advanced_analytics = models.BooleanField(_("Analytics avancées"), default=False)
    feature_api_access = models.BooleanField(_("Accès API"), default=False)

    # Configuration de django-tenants
    auto_create_schema = True
    auto_drop_schema = True

    class Meta:
        verbose_name = _("Société (Tenant)")
        verbose_name_plural = _("Sociétés (Tenants)")

    def __str__(self):
        return self.name

class Domain(DomainMixin):
    """
    Associe un nom de domaine ou sous-domaine à un Company (Tenant).
    Exemple: maboutique.mon-erp.com
    """
    
    class Meta:
        verbose_name = _("Domaine/Sous-domaine")
        verbose_name_plural = _("Domaines/Sous-domaines")

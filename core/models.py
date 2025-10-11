"""
Core models and mixins used across the application.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class TimeStampedModel(models.Model):
    """
    An abstract base class model that provides self-updating
    'created_at' and 'updated_at' fields.
    """
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Créé le"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Modifié le"))
    
    class Meta:
        abstract = True


class ActiveModel(models.Model):
    """
    An abstract base class model that provides 'is_active' field.
    """
    is_active = models.BooleanField(default=True, verbose_name=_("Actif"))
    
    class Meta:
        abstract = True


class AuditModel(TimeStampedModel):
    """
    An abstract base class model that provides audit fields.
    """
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_created',
        verbose_name=_("Créé par")
    )
    updated_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_updated',
        verbose_name=_("Modifié par")
    )
    
    class Meta:
        abstract = True
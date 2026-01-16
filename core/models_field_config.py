"""
Field configuration models for form customization.
"""

from django.db import models
from core.models import TimeStampedModel


class FieldConfiguration(TimeStampedModel):
    """Configuration for form fields visibility and requirements."""
    
    FORM_CHOICES = [
        ('product', 'Produit'),
        ('product_table', 'Tableau Produit'),
        ('service', 'Service'),
        ('service_table', 'Tableau Service'),
        ('purchase', 'Achat (Entrée Stock)'),
        ('purchase_table', 'Tableau Achat'),
        ('customer', 'Client'),
        ('supplier', 'Fournisseur'),
        ('sale', 'Vente'),
        ('invoice', 'Facture'),
        ('expense', 'Dépense'),
    ]
    
    form_name = models.CharField(
        max_length=50,
        choices=FORM_CHOICES,
        verbose_name="Formulaire"
    )
    field_name = models.CharField(
        max_length=100,
        verbose_name="Nom du champ"
    )
    field_label = models.CharField(
        max_length=200,
        verbose_name="Libellé du champ"
    )
    is_visible = models.BooleanField(
        default=True,
        verbose_name="Visible"
    )
    is_required = models.BooleanField(
        default=False,
        verbose_name="Obligatoire"
    )
    display_order = models.IntegerField(
        default=0,
        verbose_name="Ordre d'affichage"
    )
    
    class Meta:
        unique_together = ('form_name', 'field_name')
        ordering = ['form_name', 'display_order', 'field_name']
        verbose_name = "Configuration de champ"
        verbose_name_plural = "Configurations de champs"
    
    def __str__(self):
        return f"{self.get_form_name_display()} - {self.field_label}"

"""
Company settings models for invoice customization.
"""

from django.db import models
from core.models import TimeStampedModel


class CompanySettings(TimeStampedModel):
    """
    Model to store company information and invoice customization settings.
    Only one instance should exist per company/tenant.
    """
    
    # Company Information
    company_name = models.CharField(
        max_length=200,
        default="SG-STOCK",
        verbose_name="Nom de l'entreprise"
    )
    company_slogan = models.CharField(
        max_length=200,
        default="Solution de Gestion Commerciale",
        blank=True,
        verbose_name="Slogan"
    )
    company_email = models.EmailField(
        default="contact@sgstock.cm",
        verbose_name="Email"
    )
    company_phone = models.CharField(
        max_length=50,
        default="+237 XXX XXX XXX",
        verbose_name="Téléphone"
    )
    company_address = models.TextField(
        blank=True,
        verbose_name="Adresse complète"
    )
    company_website = models.URLField(
        blank=True,
        verbose_name="Site web"
    )
    tax_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Numéro fiscal / RC"
    )
    
    # Logo
    logo = models.ImageField(
        upload_to='company/logos/',
        null=True,
        blank=True,
        verbose_name="Logo de l'entreprise"
    )
    
    # Invoice Customization - Colors
    primary_color = models.CharField(
        max_length=7,
        default="#0769CF",
        help_text="Couleur principale (format: #RRGGBB)",
        verbose_name="Couleur principale"
    )
    secondary_color = models.CharField(
        max_length=7,
        default="#003FD8",
        help_text="Couleur secondaire (format: #RRGGBB)",
        verbose_name="Couleur secondaire"
    )
    text_color = models.CharField(
        max_length=7,
        default="#292D32",
        help_text="Couleur du texte (format: #RRGGBB)",
        verbose_name="Couleur du texte"
    )
    
    # Invoice Header Customization
    invoice_header_text = models.TextField(
        blank=True,
        help_text="Texte personnalisé pour l'en-tête de facture",
        verbose_name="Texte d'en-tête"
    )
    show_logo_on_invoice = models.BooleanField(
        default=True,
        verbose_name="Afficher le logo sur la facture"
    )
    
    # Invoice Footer Customization
    invoice_footer_text = models.TextField(
        default="Merci pour votre confiance !",
        verbose_name="Message de pied de page"
    )
    invoice_footer_note = models.TextField(
        blank=True,
        help_text="Note additionnelle en bas de facture",
        verbose_name="Note additionnelle"
    )
    
    # Payment Information
    bank_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Nom de la banque"
    )
    bank_account = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Numéro de compte bancaire"
    )
    mobile_money_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Numéro Mobile Money"
    )
    
    # Invoice Settings
    invoice_prefix = models.CharField(
        max_length=10,
        default="FAC",
        verbose_name="Préfixe de facture"
    )
    show_tax_breakdown = models.BooleanField(
        default=True,
        verbose_name="Afficher le détail de la TVA"
    )
    default_payment_terms = models.TextField(
        default="Règlement à réception de facture",
        verbose_name="Conditions de paiement par défaut"
    )
    
    class Meta:
        verbose_name = "Configuration d'entreprise"
        verbose_name_plural = "Configurations d'entreprise"
    
    def __str__(self):
        return f"Configuration - {self.company_name}"
    
    @classmethod
    def get_settings(cls):
        """Get or create company settings singleton."""
        settings, created = cls.objects.get_or_create(id=1)
        return settings

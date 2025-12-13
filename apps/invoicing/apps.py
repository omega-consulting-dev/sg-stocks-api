from django.apps import AppConfig


class InvoicingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.invoicing'
    verbose_name = 'Facturation'
    
    def ready(self):
        """Import signals when app is ready."""
        # Import signals to register them
        import apps.invoicing.signals  # noqa

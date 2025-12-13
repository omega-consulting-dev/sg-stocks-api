from django.apps import AppConfig


class SuppliersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.suppliers'
    verbose_name = 'Gestion des Fournisseurs'
    
    def ready(self):
        """Import signals when app is ready."""
        import apps.suppliers.signals  # noqa

from django.apps import AppConfig


class InventoryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.inventory'
    verbose_name = 'Gestion des Stocks'
    
    def ready(self):
        """Import signals when app is ready."""
        import apps.inventory.signals  # noqa

from django.apps import AppConfig


class CashboxConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.cashbox'
    verbose_name = 'Gestion de Caisse'
    
    def ready(self):
        """Importer les signals quand l'app est prête."""
        import apps.cashbox.signals

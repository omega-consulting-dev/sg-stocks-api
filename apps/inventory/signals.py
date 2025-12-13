"""
Signals pour la gestion automatique des stocks lors des mouvements.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from apps.inventory.models import StockMovement, Stock


@receiver(post_save, sender=StockMovement)
def update_stock_on_movement(sender, instance, created, **kwargs):
    """
    Met à jour automatiquement les quantités de stock lors de la création d'un mouvement.
    """
    if not created or not instance.is_active:
        return
    
    with transaction.atomic():
        # Récupérer ou créer le stock pour ce produit/magasin
        stock, _ = Stock.objects.select_for_update().get_or_create(
            product=instance.product,
            store=instance.store,
            defaults={'quantity': 0, 'reserved_quantity': 0}
        )
        
        # Mettre à jour selon le type de mouvement
        if instance.movement_type == 'in':
            # Entrée: augmenter le stock
            stock.quantity += instance.quantity
        elif instance.movement_type == 'out':
            # Sortie: diminuer le stock
            stock.quantity -= instance.quantity
            # S'assurer que le stock ne devient pas négatif
            if stock.quantity < 0:
                stock.quantity = 0
        elif instance.movement_type == 'adjustment':
            # Ajustement: remplacer la quantité
            stock.quantity = instance.quantity
        
        stock.save()

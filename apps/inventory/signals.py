"""
Signals pour la gestion automatique des stocks lors des mouvements.
"""
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.db import transaction
from apps.inventory.models import StockMovement, Stock
from apps.accounts.models import User


# DÉSACTIVÉ: Ce signal causait un doublement des stocks car _update_stock() 
# est déjà appelé manuellement dans perform_create() de la vue.
# La gestion manuelle avec transactions atomiques est plus robuste.
#
# @receiver(post_save, sender=StockMovement)
# def update_stock_on_movement(sender, instance, created, **kwargs):
#     """
#     Met à jour automatiquement les quantités de stock lors de la création d'un mouvement.
#     """
#     if not created or not instance.is_active:
#         return
#     
#     with transaction.atomic():
#         # Récupérer ou créer le stock pour ce produit/magasin
#         stock, _ = Stock.objects.select_for_update().get_or_create(
#             product=instance.product,
#             store=instance.store,
#             defaults={'quantity': 0, 'reserved_quantity': 0}
#         )
#         
#         # Mettre à jour selon le type de mouvement
#         if instance.movement_type == 'in':
#             # Entrée: augmenter le stock
#             stock.quantity += instance.quantity
#         elif instance.movement_type == 'out':
#             # Sortie: diminuer le stock
#             stock.quantity -= instance.quantity
#             # S'assurer que le stock ne devient pas négatif
#             if stock.quantity < 0:
#                 stock.quantity = 0
#         elif instance.movement_type == 'adjustment':
#             # Ajustement: remplacer la quantité
#             stock.quantity = instance.quantity
#         
#         stock.save()


@receiver(post_delete, sender=StockMovement)
def reverse_stock_on_movement_delete(sender, instance, **kwargs):
    """
    Annule l'impact sur le stock lors de la suppression d'un mouvement.
    """
    if not instance.is_active:
        return
    
    with transaction.atomic():
        # Récupérer le stock pour ce produit/magasin
        try:
            stock = Stock.objects.select_for_update().get(
                product=instance.product,
                store=instance.store
            )
            
            # Annuler le mouvement selon le type
            if instance.movement_type == 'in':
                # Annuler une entrée: diminuer le stock
                stock.quantity -= instance.quantity
                # S'assurer que le stock ne devient pas négatif
                if stock.quantity < 0:
                    stock.quantity = 0
            elif instance.movement_type == 'out':
                # Annuler une sortie: augmenter le stock
                stock.quantity += instance.quantity
            
            stock.save()
        except Stock.DoesNotExist:
            # Si le stock n'existe pas, rien à faire
            pass


@receiver(post_save, sender=Stock)
def notify_stock_issues(sender, instance, created, update_fields, **kwargs):
    """
    Notifier les utilisateurs lors de problèmes de stock dans un magasin.
    Ne notifie QUE si le stock diminue et atteint un seuil critique.
    """
    import logging
    from core.notifications import notify_stock_rupture, notify_stock_low
    
    logger = logging.getLogger(__name__)
    
    # Ne pas notifier lors de la création d'un nouveau stock
    if created:
        logger.info(f"[STOCK] Nouveau stock créé, pas de notification")
        return
    
    # Récupérer le produit et le magasin
    product = instance.product
    store = instance.store
    stock_quantity = instance.quantity
    
    # Log pour debug
    logger.info(f"[STOCK] Signal déclenché pour {product.name} dans {store.name} (Stock: {stock_quantity}, Minimum: {product.minimum_stock})")
    
    # Vérifier si le produit a un seuil minimum défini
    if product.minimum_stock <= 0:
        logger.warning(f"[STOCK] Pas de notification pour {product.name} - minimum_stock = {product.minimum_stock}")
        return
    
    # Vérifier si c'est une mise à jour de la quantité
    # Si update_fields est fourni et ne contient pas 'quantity', on skip
    if update_fields is not None and 'quantity' not in update_fields:
        logger.info(f"[STOCK] Mise à jour sans changement de quantité, pas de notification")
        return
    
    # Récupérer l'ancienne valeur depuis la base de données AVANT la sauvegarde
    # Utiliser les données trackées si disponibles
    old_quantity = None
    if hasattr(instance, '_stock_old_quantity'):
        old_quantity = instance._stock_old_quantity
    
    # Ne notifier QUE si le stock a diminué ou reste critique
    # Ne PAS notifier si le stock augmente (entrée de stock)
    if old_quantity is not None and stock_quantity > old_quantity:
        logger.info(f"[STOCK] ✅ Stock en augmentation pour {product.name} ({old_quantity} → {stock_quantity}), pas de notification")
        return
    
    # Si on ne peut pas déterminer le sens du changement, on vérifie seulement si stock critique
    # mais on évite de notifier si le stock est positif (probablement une entrée)
    if old_quantity is None and stock_quantity > product.minimum_stock:
        logger.info(f"[STOCK] Stock au-dessus du minimum, pas de notification")
        return
    
    # Obtenir les utilisateurs à notifier pour ce magasin
    # 1. Utilisateurs assignés à ce magasin spécifique
    # 2. Utilisateurs sans magasin assigné (admins globaux)
    users_assigned_to_store = User.objects.filter(
        is_active=True,
        role__isnull=False,
        assigned_stores=store
    )
    
    users_global = User.objects.filter(
        is_active=True,
        role__isnull=False,
        assigned_stores__isnull=True
    )
    
    # Combiner les deux ensembles
    users_to_notify = (users_assigned_to_store | users_global).distinct()
    
    if not users_to_notify.exists():
        logger.warning(f"[STOCK] Aucun utilisateur à notifier pour {store.name}")
        return
    
    logger.info(f"[STOCK] {users_to_notify.count()} utilisateur(s) à notifier pour {store.name}: {[u.username for u in users_to_notify]}")
    
    # Vérifier si en rupture de stock dans ce magasin (stock = 0)
    if stock_quantity <= 0:
        logger.error(f"[STOCK] 🔴 RUPTURE DE STOCK: {product.name} dans {store.name}")
        for user in users_to_notify:
            notify_stock_rupture(
                user=user,
                product_name=f"{product.name} ({store.name})",
                product_id=product.id
            )
            logger.info(f"[STOCK] Notification rupture envoyée à {user.username}")
    # Vérifier si stock faible dans ce magasin (stock <= minimum)
    elif stock_quantity <= product.minimum_stock:
        logger.warning(f"[STOCK] 🟠 STOCK FAIBLE: {product.name} dans {store.name} ({stock_quantity} <= {product.minimum_stock})")
        for user in users_to_notify:
            notify_stock_low(
                user=user,
                product_name=f"{product.name} ({store.name})",
                product_id=product.id,
                current_quantity=stock_quantity,
                reorder_level=product.minimum_stock
            )
            logger.info(f"[STOCK] Notification stock faible envoyée à {user.username}")
    else:
        logger.info(f"[STOCK] ✅ Stock OK pour {product.name} dans {store.name} ({stock_quantity} > {product.minimum_stock})")


@receiver(pre_save, sender=Stock)
def track_stock_changes(sender, instance, **kwargs):
    """
    Tracker l'ancienne valeur du stock avant modification pour savoir si le stock augmente ou diminue.
    """
    if instance.pk:
        try:
            old_instance = Stock.objects.get(pk=instance.pk)
            instance._stock_old_quantity = old_instance.quantity
        except Stock.DoesNotExist:
            instance._stock_old_quantity = None

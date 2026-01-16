# Logique de Modification d'un Transfert de Stock

## 🎯 Objectif
Permettre de modifier un transfert de stock existant avec gestion correcte des stocks (annuler l'ancien et appliquer le nouveau).

## 📊 Analyse des Approches Possibles

### ❌ Approche 1 : Modification Directe avec Delta (DÉCONSEILLÉE)
**Comment ça marche :**
- Calculer la différence entre l'ancienne et la nouvelle quantité
- Ajuster uniquement le delta

**Problèmes :**
- ❌ Très complexe à gérer avec plusieurs produits
- ❌ Risque d'erreurs de calcul
- ❌ Difficile à tracer dans l'historique
- ❌ Que faire si un produit est supprimé ? Ajouté ?

### ✅ Approche 2 : Annuler et Recréer (RECOMMANDÉE)
**Comment ça marche :**
1. Lors du chargement en mode édition :
   - Charger le transfert avec toutes ses lignes dans le panier
   - L'utilisateur peut modifier, ajouter, supprimer des produits

2. Lors de la sauvegarde :
   - **Annuler complètement l'ancien transfert** (inverser tous les mouvements de stock)
   - **Créer un nouveau transfert** avec les nouvelles données
   - Garder une référence dans l'historique

**Avantages :**
- ✅ Simple à comprendre et à implémenter
- ✅ Traçabilité complète (audit trail)
- ✅ Pas de calcul de delta complexe
- ✅ Fonctionne pour tous les cas (ajout, suppression, modification)

**Inconvénients :**
- ⚠️ Crée 2 entrées dans l'historique (ancien annulé + nouveau)
- ✅ MAIS c'est une bonne chose pour l'audit !

### 🔒 Approche 3 : Verrouillage Strict (PRODUCTION)
**Comment ça marche :**
- Autoriser la modification SEULEMENT pour les transferts en **statut "draft"** (brouillon)
- Une fois **validé** (statut "in_transit" ou "received") → **IMPOSSIBLE À MODIFIER**
- Pour "modifier" un transfert validé → il faut l'annuler et en créer un nouveau

**Avantages :**
- ✅ Aucun risque d'incohérence de stock
- ✅ Audit trail parfait
- ✅ Conforme aux bonnes pratiques comptables

**États d'un transfert :**
```
draft        → Brouillon (MODIFIABLE)
in_transit   → En transit (VERROUILLÉ, peut être annulé)
received     → Reçu (VERROUILLÉ, peut être annulé avec conditions)
cancelled    → Annulé (VERROUILLÉ)
```

## 🎨 Solution Recommandée : Hybride (Approche 2 + 3)

### Phase 1 : Modification des Brouillons (IMMÉDIAT)
```
SI transfert.status == "draft":
    ✅ Permettre modification libre (l'API actuelle le fait déjà)
    ✅ Aucun mouvement de stock n'est encore créé
    ✅ Modification simple des lignes
```

### Phase 2 : Annulation des Transferts Validés
```
SI transfert.status == "in_transit":
    ❌ Interdire la modification directe
    ✅ Permettre l'annulation (avec remise en stock)
    ✅ Créer un nouveau transfert si besoin
```

### Phase 3 : Cas Complexe - Transferts Reçus
```
SI transfert.status == "received":
    ❌ Interdire modification ET annulation standard
    ✅ Créer un "transfert de correction" dans le sens inverse
    📋 Nécessite une justification/note obligatoire
```

## 💻 Implémentation Frontend

### 1. Charger le Transfert en Mode Édition
```typescript
// Lors du clic sur "Modifier"
const editTransfer = async (transfer: StockTransfer) => {
  // Charger les détails complets avec les lignes
  const fullTransfer = await transfersStore.fetchTransfer(transfer.id)
  
  // Pré-remplir le formulaire avec les données existantes
  formData.value = {
    source_store: fullTransfer.source_store.id,
    destination_store: fullTransfer.destination_store.id,
    transfer_date: fullTransfer.transfer_date,
    notes: fullTransfer.notes
  }
  
  // Charger les produits dans le panier
  transferLines.value = fullTransfer.lines.map(line => ({
    id: crypto.randomUUID(), // ID local pour le formulaire
    product: line.product.id,
    productName: line.product.name,
    quantity: line.quantity_requested,
    lineId: line.id // ID de la ligne originale
  }))
  
  editingTransferId.value = transfer.id
  showEditDialog.value = true
}
```

### 2. Sauvegarder les Modifications
```typescript
const saveTransferEdits = async () => {
  if (transferStatus === 'draft') {
    // Modification directe simple (l'API le gère déjà)
    await transfersApi.updateTransfer(editingTransferId, {
      source_store: formData.source_store,
      destination_store: formData.destination_store,
      lines: transferLines.map(line => ({
        product: line.product,
        quantity_requested: line.quantity
      }))
    })
  } else {
    // Transfert déjà validé → Afficher un message
    showError("Ce transfert ne peut plus être modifié. Annulez-le et créez-en un nouveau.")
  }
}
```

### 3. Annuler un Transfert Validé
```typescript
const cancelAndRecreate = async (transfer: StockTransfer) => {
  // 1. Annuler l'ancien transfert
  await transfersStore.cancelTransfer(transfer.id)
  
  // 2. Pré-remplir un nouveau formulaire avec les données
  openCreateDialogWithData(transfer)
}
```

## 🔧 Implémentation Backend (Django)

### Modification du ViewSet
```python
def update(self, request, *args, **kwargs):
    """Update transfer - only allowed for draft status."""
    transfer = self.get_object()
    
    # Vérifier le statut
    if transfer.status != 'draft':
        return Response(
            {
                'error': 'Seuls les transferts en brouillon peuvent être modifiés.',
                'detail': 'Pour modifier ce transfert, annulez-le d\'abord puis créez-en un nouveau.'
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Continuer avec la mise à jour normale
    return super().update(request, *args, **kwargs)
```

### Action d'Annulation
```python
@action(detail=True, methods=['post'])
def cancel(self, request, pk=None):
    """Cancel a transfer and restore stock."""
    transfer = self.get_object()
    
    if transfer.status == 'cancelled':
        return Response(
            {'error': 'Ce transfert est déjà annulé'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    with transaction.atomic():
        # Annuler les mouvements de stock selon le statut
        if transfer.status == 'in_transit':
            # Remettre le stock au magasin source
            for line in transfer.lines.all():
                stock = Stock.objects.get(
                    product=line.product,
                    store=transfer.source_store
                )
                stock.quantity += line.quantity_sent
                stock.save()
                
                # Supprimer le mouvement de sortie
                StockMovement.objects.filter(
                    reference=transfer.transfer_number,
                    product=line.product,
                    store=transfer.source_store
                ).delete()
        
        elif transfer.status == 'received':
            # Cas complexe : retirer du stock destination ET remettre au source
            for line in transfer.lines.all():
                # Retirer du stock destination
                dest_stock = Stock.objects.get(
                    product=line.product,
                    store=transfer.destination_store
                )
                dest_stock.quantity -= line.quantity_received
                dest_stock.save()
                
                # Remettre au stock source
                source_stock = Stock.objects.get(
                    product=line.product,
                    store=transfer.source_store
                )
                source_stock.quantity += line.quantity_sent
                source_stock.save()
                
                # Supprimer les mouvements
                StockMovement.objects.filter(
                    reference=transfer.transfer_number,
                    product=line.product
                ).delete()
        
        # Marquer le transfert comme annulé
        transfer.status = 'cancelled'
        transfer.cancelled_by = request.user
        transfer.cancelled_at = timezone.now()
        transfer.save()
    
    return Response({'message': 'Transfert annulé avec succès'})
```

## 📝 Règles de Gestion

### ✅ Autorisé
- Modifier un transfert en **statut "draft"** (brouillon)
- Annuler un transfert en **statut "in_transit"** ou **"received"**
- Supprimer un transfert en **statut "draft"**

### ❌ Interdit
- Modifier un transfert déjà **validé**, **en transit** ou **reçu**
- Supprimer un transfert qui a des mouvements de stock
- Annuler un transfert déjà **annulé**

### 🔄 Actions Alternatives
- Pour "modifier" un transfert validé → **Annuler + Créer nouveau**
- Pour corriger une erreur après réception → **Transfert de correction inverse**

## 🎯 Résumé de la Meilleure Logique

1. **Brouillon (draft)** :
   - ✅ Modification directe autorisée
   - ✅ Aucun impact sur le stock (pas encore de mouvements)

2. **En Transit (in_transit)** :
   - ❌ Modification interdite
   - ✅ Annulation possible (inverse le mouvement de sortie)
   - ✅ Possibilité de créer un nouveau transfert après annulation

3. **Reçu (received)** :
   - ❌ Modification interdite
   - ⚠️ Annulation possible mais avec attention (inverse entrée ET sortie)
   - ✅ Alternative : Transfert de correction

4. **Annulé (cancelled)** :
   - ❌ Aucune action possible
   - 📋 Consultation uniquement pour l'historique

Cette approche garantit :
- 🔒 **Intégrité des stocks** : Aucune incohérence possible
- 📋 **Traçabilité** : Historique complet de toutes les actions
- 👥 **Sécurité** : Permissions vérifiées à chaque étape
- 🎯 **Simplicité** : Facile à comprendre pour les utilisateurs

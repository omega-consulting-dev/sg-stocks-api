# 🎯 Solution Implémentée : Modification des Transferts de Stock

## ✅ Ce Qui A Été Fait

### 1. Backend (Django) - COMPLÉTÉ ✅

#### Sécurisation de la Modification
```python
def update(self, request, *args, **kwargs):
    """Seuls les transferts en statut 'draft' peuvent être modifiés"""
    ✅ Vérifie que le transfert est en brouillon
    ❌ Bloque la modification si le statut est: in_transit, received, cancelled
    📋 Retourne un message clair avec le statut actuel
```

#### Amélioration de l'Annulation
```python
def cancel(self, request, pk=None):
    """Annule un transfert et restaure les stocks correctement"""
    
    ✅ Gère TOUS les statuts:
    
    1. DRAFT (Brouillon):
       - Simple annulation
       - Aucun mouvement de stock à inverser
    
    2. IN_TRANSIT (En Transit):
       - Remet le stock au magasin SOURCE
       - Supprime les mouvements de sortie
    
    3. RECEIVED (Reçu):
       - Retire du stock DESTINATION
       - Remet au stock SOURCE
       - Vérifie que le stock destination est suffisant
       - Supprime TOUS les mouvements liés
    
    ✅ Utilise des transactions atomiques (tout ou rien)
    ✅ Utilise select_for_update() pour éviter les conflits
```

### 2. Règles de Gestion Implémentées

| Statut Transfer | Peut Modifier ? | Peut Annuler ? | Action sur Stock |
|----------------|-----------------|----------------|------------------|
| **draft** | ✅ OUI | ✅ OUI | Aucun (pas encore de mouvements) |
| **in_transit** | ❌ NON | ✅ OUI | Remet au stock source |
| **received** | ❌ NON | ⚠️ OUI* | Retire de destination + remet à source |
| **cancelled** | ❌ NON | ❌ NON | N/A |

> \* Pour **received**, annulation possible SEULEMENT si le stock destination est suffisant

### 3. Messages d'Erreur Clairs

```json
// Tentative de modification d'un transfert validé
{
  "error": "Seuls les transferts en brouillon peuvent être modifiés.",
  "detail": "Pour modifier ce transfert, annulez-le d'abord puis créez-en un nouveau.",
  "current_status": "in_transit"
}

// Stock insuffisant pour annuler un transfert reçu
{
  "error": "Stock insuffisant pour annuler le transfert.",
  "detail": "Le produit \"Agri bio fongicide 1L\" a un stock de 10 dans \"PV Douala\" mais 50 sont nécessaires pour annuler le transfert."
}
```

## 📋 Ce Qu'Il Reste à Faire (Frontend)

### 1. Page de Liste des Transferts

#### A. Afficher le Bouton "Modifier" Conditionnellement
```vue
<template>
  <div v-for="transfer in transfers" :key="transfer.id">
    <!-- Bouton Modifier (seulement pour draft) -->
    <Button 
      v-if="transfer.status === 'draft'"
      @click="editTransfer(transfer)"
      variant="outline"
      size="sm"
    >
      <PencilIcon class="h-4 w-4" />
      Modifier
    </Button>
    
    <!-- Bouton Annuler (pour tous sauf cancelled) -->
    <Button 
      v-if="transfer.status !== 'cancelled'"
      @click="cancelTransfer(transfer)"
      variant="destructive"
      size="sm"
    >
      <XIcon class="h-4 w-4" />
      Annuler
    </Button>
  </div>
</template>
```

#### B. Charger les Données pour la Modification
```typescript
const editTransfer = async (transfer: StockTransfer) => {
  // 1. Vérifier le statut
  if (transfer.status !== 'draft') {
    alert('Ce transfert ne peut plus être modifié. Statut: ' + transfer.status)
    return
  }
  
  // 2. Charger les détails complets
  const fullTransfer = await transfersStore.fetchTransfer(transfer.id)
  
  // 3. Pré-remplir le formulaire
  formData.value = {
    source_store: fullTransfer.source_store.id,
    destination_store: fullTransfer.destination_store.id,
    transfer_date: fullTransfer.transfer_date,
    notes: fullTransfer.notes || ''
  }
  
  // 4. Charger les produits dans le panier
  produitsTransferts.value = fullTransfer.lines.map(line => ({
    product_id: line.product.id,
    product_name: line.product.name,
    product_reference: line.product.reference,
    quantiteTransfert: line.quantity_requested,
    prix_achat: line.product.purchase_price || 0,
    total: (line.product.purchase_price || 0) * line.quantity_requested,
    notes: line.notes || '',
    lineId: line.id  // Garder l'ID de la ligne originale
  }))
  
  // 5. Marquer qu'on est en mode édition
  editingTransferId.value = transfer.id
  editMode.value = true
  
  // 6. Ouvrir le formulaire
  showTransferForm.value = true
}
```

#### C. Sauvegarder les Modifications
```typescript
const saveTransferEdits = async () => {
  try {
    const updateData = {
      source_store: parseInt(formData.value.source_store),
      destination_store: parseInt(formData.value.destination_store),
      transfer_date: formData.value.transfer_date,
      notes: formData.value.notes,
      lines: produitsTransferts.value.map(p => ({
        product: p.product_id,
        quantity_requested: p.quantiteTransfert,
        notes: p.notes
      }))
    }
    
    // Appeler l'API de mise à jour
    await transfersStore.updateTransfer(editingTransferId.value, updateData)
    
    // Fermer le formulaire et rafraîchir
    closeTransferForm()
    await transfersStore.fetchTransfers()
    
    showSuccess('Transfert modifié avec succès !')
  } catch (error: any) {
    // Gérer l'erreur (ex: tentative de modification d'un transfert validé)
    if (error.response?.data?.error) {
      showError(error.response.data.error)
    } else {
      showError('Erreur lors de la modification du transfert')
    }
  }
}
```

#### D. Annuler un Transfert
```typescript
const cancelTransfer = async (transfer: StockTransfer) => {
  // Message de confirmation différent selon le statut
  let confirmMessage = ''
  
  if (transfer.status === 'draft') {
    confirmMessage = 'Voulez-vous annuler ce transfert en brouillon ?'
  } else if (transfer.status === 'in_transit') {
    confirmMessage = 'Ce transfert est en transit. L\'annuler remettra les produits au stock source. Continuer ?'
  } else if (transfer.status === 'received') {
    confirmMessage = 'ATTENTION : Ce transfert a déjà été reçu. L\'annuler va retirer les produits du stock destination ET les remettre au stock source. Êtes-vous sûr ?'
  }
  
  if (!confirm(confirmMessage)) return
  
  try {
    await transfersStore.cancelTransfer(transfer.id)
    await transfersStore.fetchTransfers()
    await transfersStore.fetchStats()
    
    showSuccess('Transfert annulé avec succès. Les stocks ont été restaurés.')
  } catch (error: any) {
    if (error.response?.data?.error) {
      showError(error.response.data.error)
      if (error.response.data.detail) {
        showError(error.response.data.detail)
      }
    } else {
      showError('Erreur lors de l\'annulation du transfert')
    }
  }
}
```

### 2. Composant TransferFormDialog.vue

```vue
<script setup lang="ts">
// Props
const props = defineProps<{
  open: boolean
  editData?: StockTransferDetail | null  // Pour le mode édition
}>()

// État local
const editMode = computed(() => !!props.editData)
const transferId = computed(() => props.editData?.id)

// Watcher pour pré-remplir le formulaire en mode édition
watch(() => props.editData, (data) => {
  if (data) {
    // Pré-remplir le formulaire
    formData.value = {
      source_store: data.source_store.id,
      destination_store: data.destination_store.id,
      transfer_date: data.transfer_date,
      notes: data.notes || ''
    }
    
    // Charger les produits
    transferLines.value = data.lines.map(line => ({
      id: crypto.randomUUID(),
      product: line.product.id,
      productName: line.product.name,
      quantity: line.quantity_requested
    }))
  }
}, { immediate: true })

// Soumission
const handleSubmit = async () => {
  if (editMode.value && transferId.value) {
    // Mode édition
    await transfersStore.updateTransfer(transferId.value, prepareData())
  } else {
    // Mode création
    await transfersStore.createTransfer(prepareData())
  }
}
</script>

<template>
  <Dialog :open="open" @update:open="$emit('update:open', $event)">
    <DialogContent>
      <DialogHeader>
        <DialogTitle>
          {{ editMode ? 'Modifier le transfert' : 'Nouveau transfert' }}
        </DialogTitle>
      </DialogHeader>
      
      <!-- Alerte si transfert non-draft -->
      <Alert v-if="editData && editData.status !== 'draft'" variant="destructive">
        <AlertCircle class="h-4 w-4" />
        <AlertTitle>Modification impossible</AlertTitle>
        <AlertDescription>
          Ce transfert ne peut plus être modifié (statut: {{ editData.status_display }}).
          Pour le modifier, annulez-le d'abord puis créez-en un nouveau.
        </AlertDescription>
      </Alert>
      
      <!-- Formulaire (désactivé si non-draft) -->
      <form 
        @submit.prevent="handleSubmit"
        :class="{ 'opacity-50 pointer-events-none': editData?.status !== 'draft' }"
      >
        <!-- Champs du formulaire... -->
      </form>
    </DialogContent>
  </Dialog>
</template>
```

## 🎯 Workflow Utilisateur Final

### Scénario 1 : Modifier un Transfert en Brouillon
1. ✅ Cliquer sur "Modifier" → Le formulaire se charge avec les produits
2. ✅ Modifier les quantités, ajouter/supprimer des produits
3. ✅ Sauvegarder → Le transfert est mis à jour
4. ✅ Aucun impact sur le stock (car toujours en brouillon)

### Scénario 2 : Modifier un Transfert Validé
1. ❌ Bouton "Modifier" désactivé ou absent
2. ✅ Affichage d'un message : "Ce transfert ne peut plus être modifié"
3. ✅ Options disponibles :
   - Annuler le transfert (restaure les stocks)
   - Créer un nouveau transfert corrigé

### Scénario 3 : Annuler un Transfert en Transit
1. ✅ Cliquer sur "Annuler"
2. ⚠️ Message de confirmation : "Cela va remettre les produits au stock source"
3. ✅ Confirmer → Le stock source est restauré
4. ✅ Les mouvements de sortie sont supprimés
5. ✅ Le transfert passe en statut "cancelled"

### Scénario 4 : Annuler un Transfert Reçu
1. ✅ Cliquer sur "Annuler"
2. ⚠️⚠️ Message d'alerte : "ATTENTION : Cela va retirer les produits de la destination"
3. ✅ Confirmer → Vérifie que le stock destination est suffisant
4. ✅ Si OK : Retire de la destination ET remet à la source
5. ❌ Si KO : Message d'erreur avec détails du stock manquant

## 📱 Interface Utilisateur Recommandée

```
┌──────────────────────────────────────────────────────────┐
│ TRANSFERT #TR2026001                                      │
│                                                           │
│ Statut: [En Transit] 🚚                                   │
│ Source: PV Douala → Destination: PV Yaoundé              │
│ Date: 16/01/2026                                         │
│                                                           │
│ Produits:                                                 │
│ • Agri bio fongicide 1L : 50 unités                      │
│ • Engrais NPK 25kg : 100 unités                          │
│                                                           │
│ ┌─────────────┐  ┌──────────────┐  ┌──────────────┐     │
│ │  👁 Voir    │  │  ❌ Annuler  │  │  📄 Imprimer │     │
│ └─────────────┘  └──────────────┘  └──────────────┘     │
│                                                           │
│ ⚠️ Ce transfert ne peut plus être modifié                │
│    Pour le modifier, annulez-le et créez-en un nouveau   │
└──────────────────────────────────────────────────────────┘
```

```
┌──────────────────────────────────────────────────────────┐
│ TRANSFERT #TR2026002                                      │
│                                                           │
│ Statut: [Brouillon] 📝                                    │
│ Source: PV Douala → Destination: PV Yaoundé              │
│ Date: 16/01/2026                                         │
│                                                           │
│ Produits:                                                 │
│ • Agri bio fongicide 1L : 30 unités                      │
│                                                           │
│ ┌─────────────┐  ┌──────────────┐  ┌──────────────┐     │
│ │  ✏️ Modifier │  │  ❌ Supprimer│  │  ✅ Valider  │     │
│ └─────────────┘  └──────────────┘  └──────────────┘     │
│                                                           │
│ ✅ Ce transfert peut être modifié librement               │
└──────────────────────────────────────────────────────────┘
```

## 🎓 Résumé de la Meilleure Logique

**Ma recommandation : APPROCHE HYBRIDE (Implémentée)**

✅ **Pour les BROUILLONS (draft)** :
- Modification LIBRE et DIRECTE
- Aucun mouvement de stock encore créé
- Simple mise à jour des lignes

✅ **Pour les VALIDÉS/REÇUS** :
- Modification INTERDITE
- Annulation POSSIBLE avec restauration automatique des stocks
- Traçabilité complète dans l'historique

**Avantages** :
- 🔒 Sécurisé : Aucun risque d'incohérence de stock
- 📋 Traçable : Audit trail complet
- 👥 Simple : Facile à comprendre pour les utilisateurs
- ⚡ Flexible : Permet les corrections via annulation + recréation

**Cette approche est conforme aux bonnes pratiques comptables et de gestion de stock !**

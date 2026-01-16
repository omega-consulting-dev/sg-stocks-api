# 🐛 BUG : Annulation de Transfert - Stock Incorrect

## 📋 Description du Problème

### Symptômes
Lorsqu'un transfert avec statut "Reçu" est annulé, le stock n'est pas correctement restauré au magasin source.

### Exemple concret
1. **Premier transfert** : 250 unités de Magasin Central → PV Douala (statut: Reçu)
   - Central: -250
   - Douala: +250

2. **Vente** : 1 produit vendu depuis PV Douala
   - Douala: 249

3. **Deuxième transfert** : 50 unités de Central → Douala (statut: Reçu)
   - Central: -50
   - Douala: +50 = 299

4. **Annulation du 2ème transfert**
   - ❌ **BUG** : Le stock retourne à 198 au lieu de 249
   - Perte de 51 unités !

## 🔍 Cause du Bug

### Localisation
Fichier : `apps/inventory/views.py`
Fonction : `StockTransferViewSet.cancel()`
Ligne : ~1520

### Code incorrect
```python
# Cas 2: Transfert reçu
elif transfer.status == 'received':
    for line in transfer.lines.all():
        # Retirer du stock destination
        dest_stock.quantity -= line.quantity_received  # ✅ OK
        dest_stock.save()
        
        # Remettre au stock source
        source_stock.quantity += line.quantity_sent  # ❌ ERREUR ICI !
        source_stock.save()
```

### Explication
- **Problème** : On utilise `quantity_sent` au lieu de `quantity_received`
- **Pourquoi c'est un bug** : `quantity_sent` peut être différent de `quantity_received`
  - Exemple : Envoyé 50, reçu 48 (2 cassés en route)
  - À l'annulation : on retire 48 de destination mais on remet 50 à la source ❌
  - Résultat : +2 unités créées de nulle part !

### Impact
- **Stock incohérent** entre magasins
- **Perte ou gain fictif** de produits
- **Inventaire faussé**

## ✅ Solution Appliquée

### Code corrigé
```python
# Cas 2: Transfert reçu
elif transfer.status == 'received':
    for line in transfer.lines.all():
        # Retirer du stock destination
        dest_stock.quantity -= line.quantity_received
        dest_stock.save()
        
        # Remettre au stock source (la quantité reçue, pas la quantité envoyée)
        source_stock.quantity += line.quantity_received  # ✅ CORRIGÉ
        source_stock.save()
```

### Principe
Pour annuler un transfert reçu, il faut :
1. Retirer **quantity_received** de la destination
2. Remettre **quantity_received** à la source (pas quantity_sent !)
3. Supprimer tous les mouvements de stock

## 🔧 Correction du Stock Existant

### Méthode 1 : Via Shell Django

```bash
# 1. Ouvrir le shell du tenant
python manage.py tenant_command shell --schema=agribio

# 2. Exécuter les commandes
from apps.inventory.models import Stock, Store
from apps.products.models import Product
from django.db import transaction

# Trouver le produit et le magasin
product = Product.objects.filter(reference='PROD001').first()
store = Store.objects.filter(name__icontains='Douala').first()
stock = Stock.objects.filter(product=product, store=store).first()

# Afficher l'état actuel
print(f"Stock actuel: {stock.quantity}")  # Devrait afficher 198

# Corriger (ajouter 51 unités pour revenir à 249)
with transaction.atomic():
    stock.quantity = 249  # ou stock.quantity += 51
    stock.save()
    print(f"Stock corrigé: {stock.quantity}")
```

### Méthode 2 : Via Admin/Interface

1. Aller dans la gestion des stocks
2. Chercher le produit "Agri bio fongicide 1L" dans "PV Douala"
3. Modifier manuellement le stock de 198 → 249

## 📊 Calcul de la Correction

```
Stock attendu après les opérations :
- Départ : 0
- Premier transfert reçu : +250
- Vente : -1
- Deuxième transfert reçu : +50
- Annulation du 2ème : -50
= 249 unités attendues

Stock réel après le bug : 198

Différence à corriger : 249 - 198 = 51 unités
```

## 🛡️ Tests à Effectuer

Après correction du code, tester :

1. **Transfert draft annulé**
   - Créer transfert (draft)
   - Annuler
   - ✅ Vérifier : aucun impact sur stock

2. **Transfert in_transit annulé**
   - Créer transfert
   - Valider (in_transit)
   - Annuler
   - ✅ Vérifier : stock source restauré

3. **Transfert received annulé**
   - Créer transfert
   - Valider (in_transit)
   - Recevoir (received)
   - Annuler
   - ✅ Vérifier : 
     - Stock destination réduit de quantity_received
     - Stock source augmenté de quantity_received
     - Stocks cohérents

4. **Transfert avec quantités différentes**
   - Envoyé : 100
   - Reçu : 98
   - Annuler
   - ✅ Vérifier : stock source augmenté de 98 (pas 100)

## 📝 Changelog

### 16/01/2026
- ✅ Bug identifié et corrigé
- ✅ Documentation créée
- ⏳ Stock à corriger manuellement pour les transferts déjà annulés

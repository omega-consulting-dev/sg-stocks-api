# 🔐 Guide d'Implémentation du Contrôle d'Accès

## Architecture : Backend (API) + Frontend (UI)

Le contrôle d'accès est **partagé** entre Backend et Frontend :
- **Backend** : Filtre les données et bloque les actions non autorisées ✅ **SÉCURITÉ**
- **Frontend** : Masque les boutons et menus selon les permissions ✅ **UX**

---

## 1️⃣ BACKEND - Filtrage Automatique (Déjà implémenté)

### Configuration dans chaque ViewSet

```python
# apps/inventory/views.py
from core.mixins import StoreAccessMixin, UserStoreValidationMixin

class StockMovementViewSet(StoreAccessMixin, UserStoreValidationMixin, viewsets.ModelViewSet):
    """Les mixins filtrent automatiquement selon les stores assignés."""
    pass
```

### Fonctionnement automatique :

#### Utilisateur avec `access_scope = 'assigned'` :
```python
# L'utilisateur ne voit QUE les données de ses stores
GET /api/v1/inventory/stock-movements/
# Retourne uniquement les mouvements des stores 1 et 2 (ses stores assignés)
```

#### Utilisateur avec `access_scope = 'all'` (Admin) :
```python
# L'utilisateur voit TOUTES les données
GET /api/v1/inventory/stock-movements/
# Retourne les mouvements de TOUS les stores
```

---

## 2️⃣ FRONTEND - Récupération des Permissions

### Endpoint `/me` - Récupérer les infos utilisateur

```javascript
// authService.js
export const getCurrentUser = async () => {
  const response = await api.get('/api/v1/auth/me/');
  return response.data;
};
```

### Réponse du Backend :

```json
{
  "id": 5,
  "username": "pierre_magasinier",
  "email": "pierre@store.cm",
  "first_name": "Pierre",
  "last_name": "Mbida",
  "full_name": "Pierre Mbida",
  "phone": "+237670123456",
  "employee_id": "EMP001",
  "role": 3,
  "role_details": {
    "name": "warehouse_keeper",
    "display_name": "Magasinier",
    "access_scope": "assigned",
    "can_manage_users": false,
    "can_manage_products": true,
    "can_view_products": true,
    "can_manage_categories": true,
    "can_manage_inventory": true,
    "can_view_inventory": true,
    "can_manage_sales": false,
    "can_manage_customers": false,
    "can_manage_suppliers": false,
    "can_manage_cashbox": false,
    "can_view_analytics": false,
    "can_export_data": true
  },
  "assigned_stores": [1, 2],
  "assigned_stores_details": [
    {
      "id": 1,
      "name": "Store Douala",
      "code": "DLA",
      "city": "Douala"
    },
    {
      "id": 2,
      "name": "Store Yaoundé",
      "code": "YDE",
      "city": "Yaoundé"
    }
  ],
  "is_superuser": false,
  "is_staff": false,
  "last_login": "2025-12-09T10:30:00Z",
  "date_joined": "2025-01-15T08:00:00Z"
}
```

---

## 3️⃣ FRONTEND - Stockage et Utilisation

### Context React (Recommandé)

```javascript
// contexts/AuthContext.jsx
import React, { createContext, useContext, useState, useEffect } from 'react';
import { getCurrentUser } from '../services/authService';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    loadUser();
  }, []);
  
  const loadUser = async () => {
    try {
      const userData = await getCurrentUser();
      setUser(userData);
    } catch (error) {
      console.error('Failed to load user', error);
    } finally {
      setLoading(false);
    }
  };
  
  // Helper functions pour vérifier les permissions
  const hasPermission = (permission) => {
    if (!user || !user.role_details) return false;
    if (user.is_superuser) return true;
    return user.role_details[permission] === true;
  };
  
  const canAccessStore = (storeId) => {
    if (!user) return false;
    if (user.is_superuser) return true;
    if (user.role_details.access_scope === 'all') return true;
    return user.assigned_stores.includes(storeId);
  };
  
  const value = {
    user,
    loading,
    hasPermission,
    canAccessStore,
    reload: loadUser
  };
  
  return (
    <AuthContext.Provider value={value}>
      {!loading && children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
```

---

## 4️⃣ FRONTEND - Utilisation dans les Composants

### Exemple 1 : Affichage conditionnel de menus

```jsx
// components/Sidebar.jsx
import { useAuth } from '../contexts/AuthContext';

const Sidebar = () => {
  const { user, hasPermission } = useAuth();
  
  return (
    <nav>
      <h2>Menu</h2>
      <ul>
        {/* Tous peuvent voir le dashboard */}
        <li><Link to="/dashboard">📊 Dashboard</Link></li>
        
        {/* Seulement si peut voir les produits */}
        {hasPermission('can_view_products') && (
          <li><Link to="/products">📦 Produits</Link></li>
        )}
        
        {/* Seulement si peut gérer l'inventaire */}
        {hasPermission('can_manage_inventory') && (
          <li><Link to="/inventory">📋 Inventaire</Link></li>
        )}
        
        {/* Seulement si peut gérer les ventes */}
        {hasPermission('can_manage_sales') && (
          <li><Link to="/sales">💰 Ventes</Link></li>
        )}
        
        {/* Seulement si peut voir les analytics */}
        {hasPermission('can_view_analytics') && (
          <li><Link to="/analytics">📈 Analytics</Link></li>
        )}
        
        {/* Seulement pour les admins */}
        {user.is_superuser && (
          <li><Link to="/admin">⚙️ Administration</Link></li>
        )}
      </ul>
    </nav>
  );
};
```

### Exemple 2 : Boutons conditionnels

```jsx
// pages/ProductList.jsx
import { useAuth } from '../contexts/AuthContext';

const ProductList = () => {
  const { hasPermission } = useAuth();
  const [products, setProducts] = useState([]);
  
  return (
    <div>
      <h1>📦 Liste des Produits</h1>
      
      {/* Bouton "Créer" visible uniquement si permission */}
      {hasPermission('can_manage_products') && (
        <Button onClick={handleCreate}>
          + Créer un produit
        </Button>
      )}
      
      <Table>
        {products.map(product => (
          <tr key={product.id}>
            <td>{product.name}</td>
            <td>{product.reference}</td>
            <td>
              {/* Boutons d'action selon permissions */}
              {hasPermission('can_manage_products') && (
                <>
                  <Button onClick={() => handleEdit(product)}>✏️ Modifier</Button>
                  <Button onClick={() => handleDelete(product)}>🗑️ Supprimer</Button>
                </>
              )}
            </td>
          </tr>
        ))}
      </Table>
    </div>
  );
};
```

### Exemple 3 : Filtre par Store

```jsx
// pages/StockMovements.jsx
import { useAuth } from '../contexts/AuthContext';

const StockMovements = () => {
  const { user } = useAuth();
  const [movements, setMovements] = useState([]);
  const [selectedStore, setSelectedStore] = useState(null);
  
  return (
    <div>
      <h1>📦 Mouvements de Stock</h1>
      
      {/* Sélecteur de store (uniquement les stores assignés) */}
      <Select 
        value={selectedStore}
        onChange={setSelectedStore}
        options={user.assigned_stores_details}
      />
      
      {/* Les données sont déjà filtrées par le backend */}
      <MovementsTable movements={movements} />
    </div>
  );
};
```

### Exemple 4 : Protection de routes

```jsx
// App.jsx ou routes.jsx
import { useAuth } from '../contexts/AuthContext';
import { Navigate } from 'react-router-dom';

const ProtectedRoute = ({ children, permission }) => {
  const { user, hasPermission } = useAuth();
  
  if (!user) {
    return <Navigate to="/login" />;
  }
  
  if (permission && !hasPermission(permission)) {
    return <Navigate to="/unauthorized" />;
  }
  
  return children;
};

// Utilisation
<Routes>
  <Route path="/products" element={
    <ProtectedRoute permission="can_view_products">
      <ProductList />
    </ProtectedRoute>
  } />
  
  <Route path="/inventory" element={
    <ProtectedRoute permission="can_manage_inventory">
      <InventoryPage />
    </ProtectedRoute>
  } />
  
  <Route path="/admin" element={
    <ProtectedRoute permission="can_manage_users">
      <AdminPanel />
    </ProtectedRoute>
  } />
</Routes>
```

---

## 5️⃣ FLUX COMPLET

### Création d'un utilisateur par l'Admin

```
1. Admin crée l'utilisateur
   POST /api/v1/auth/users/
   {
     "username": "pierre",
     "password": "***",
     "role": 3,  // Magasinier
     "assigned_stores": [1, 2]  // Douala et Yaoundé
   }

2. L'utilisateur se connecte
   POST /api/v1/auth/login/
   {
     "username": "pierre",
     "password": "***"
   }
   → Reçoit un token JWT

3. Frontend appelle /me pour récupérer les permissions
   GET /api/v1/auth/me/
   → Stocke les infos dans le Context

4. L'interface s'adapte automatiquement :
   ✅ Menu : Affiche uniquement Produits, Inventaire
   ❌ Menu : Cache Ventes, Analytics, Admin
   ✅ Store Selector : Affiche uniquement Douala et Yaoundé

5. L'utilisateur essaie d'accéder aux données
   GET /api/v1/inventory/stock-movements/
   → Backend filtre automatiquement : uniquement Store 1 et 2
   
6. L'utilisateur essaie de créer un mouvement pour Store 3
   POST /api/v1/inventory/stock-movements/
   { "store": 3, ... }
   → Backend rejette : 403 Forbidden
```

---

## ✅ Résumé

| Responsabilité | Backend | Frontend |
|---------------|---------|----------|
| **Filtrer les données** | ✅ Automatique via mixins | ❌ |
| **Bloquer les actions** | ✅ Vérifications dans perform_create/update | ❌ |
| **Masquer les menus** | ❌ | ✅ Selon hasPermission() |
| **Masquer les boutons** | ❌ | ✅ Selon hasPermission() |
| **Protéger les routes** | ❌ | ✅ ProtectedRoute component |
| **Sécurité** | ✅ **CRITIQUE** | ✅ UX seulement |

**🔐 Règle d'or** : Le Backend est **la source de vérité**. Le Frontend ne fait que l'UX.

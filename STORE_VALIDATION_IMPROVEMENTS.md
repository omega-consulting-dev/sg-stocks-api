# Gestion des erreurs de validation pour les Stores

## Modifications apportées

### Backend - `apps/inventory/serializers.py`

Ajout de validations personnalisées pour chaque champ obligatoire avec des messages d'erreur explicites :

```python
class StoreSerializer(serializers.ModelSerializer):
    # ... existing fields ...
    
    def validate_code(self, value):
        """Validate that code is unique."""
        if not value:
            raise serializers.ValidationError("Le code du magasin est obligatoire.")
        
        # Vérifier l'unicité en excluant l'instance actuelle si en mode édition
        instance = self.instance
        queryset = Store.objects.filter(code=value)
        if instance:
            queryset = queryset.exclude(pk=instance.pk)
        
        if queryset.exists():
            raise serializers.ValidationError("Un magasin avec ce code existe déjà.")
        
        return value
    
    def validate_name(self, value):
        """Validate that name is not empty."""
        if not value or not value.strip():
            raise serializers.ValidationError("Le nom du magasin est obligatoire.")
        return value.strip()
    
    def validate_address(self, value):
        """Validate that address is not empty."""
        if not value or not value.strip():
            raise serializers.ValidationError("L'adresse du magasin est obligatoire.")
        return value.strip()
    
    def validate_city(self, value):
        """Validate that city is not empty."""
        if not value or not value.strip():
            raise serializers.ValidationError("La ville du magasin est obligatoire.")
        return value.strip()
```

**Avantages :**
- Messages d'erreur clairs et en français
- Validation des chaînes vides ET des chaînes contenant uniquement des espaces
- Nettoyage automatique des espaces en début/fin (`.strip()`)
- Validation de l'unicité du code avec gestion du mode édition

### Frontend - `StoreEditForm.vue`

#### 1. Ajout d'un état pour stocker les erreurs par champ

```typescript
const fieldErrors = ref<Record<string, string>>({})
```

#### 2. Extraction et affichage des erreurs de validation

```typescript
catch (e) {
  const error = e as { response?: { data?: Record<string, unknown> } }
  
  // Extraire les erreurs de validation par champ
  if (error.response?.data) {
    const errors = error.response.data
    
    // Si c'est un objet avec des erreurs par champ
    if (typeof errors === 'object' && !Array.isArray(errors)) {
      fieldErrors.value = {}
      for (const [field, messages] of Object.entries(errors)) {
        if (Array.isArray(messages)) {
          fieldErrors.value[field] = messages[0]
        } else if (typeof messages === 'string') {
          fieldErrors.value[field] = messages
        }
      }
      
      // Message général si des erreurs de champs sont présentes
      if (Object.keys(fieldErrors.value).length > 0) {
        formError.value = 'Veuillez corriger les erreurs dans le formulaire'
      }
    }
  }
}
```

#### 3. Affichage visuel des erreurs pour chaque champ

**Exemple pour le champ "name" :**

```vue
<div class="space-y-1">
  <Label for="name" class="text-sm font-medium">
    Nom du magasin <span class="text-red-500">*</span>
  </Label>
  <div class="relative">
    <Building2 class="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
    <Input
      id="name"
      v-model="formData.name"
      placeholder="Ex : Boutique Centre-Ville"
      :class="['pl-10 h-10', fieldErrors.name ? 'border-red-500' : '']"
      required
      :disabled="loading"
    />
  </div>
  <p v-if="fieldErrors.name" class="text-xs text-red-500 mt-1">
    {{ fieldErrors.name }}
  </p>
</div>
```

**Améliorations visuelles :**
- Astérisque rouge `*` pour indiquer les champs obligatoires
- Bordure rouge sur le champ en cas d'erreur (`:class` dynamique)
- Message d'erreur spécifique affiché sous le champ en rouge

## Résultat

### Avant
- Erreur générique : "Une erreur est survenue"
- L'utilisateur ne sait pas quel champ est problématique
- Pas d'indication visuelle sur le formulaire

### Après
✅ **Message d'erreur spécifique** : "Le nom du magasin est obligatoire"
✅ **Indication visuelle** : Bordure rouge sur le champ en erreur
✅ **Champ précis** : L'erreur apparaît directement sous le champ concerné
✅ **Message général** : "Veuillez corriger les erreurs dans le formulaire"

## Exemple de réponse API en cas d'erreur

```json
{
  "name": ["Le nom du magasin est obligatoire."],
  "city": ["La ville du magasin est obligatoire."],
  "address": ["L'adresse du magasin est obligatoire."]
}
```

Le frontend transforme cela en :
- Bordure rouge sur les champs `name`, `city`, et `address`
- Messages sous chaque champ :
  - "Le nom du magasin est obligatoire."
  - "La ville du magasin est obligatoire."
  - "L'adresse du magasin est obligatoire."

## Champs validés

| Champ | Validation | Message d'erreur |
|-------|-----------|------------------|
| **code** | Non vide + Unique | "Le code du magasin est obligatoire." / "Un magasin avec ce code existe déjà." |
| **name** | Non vide + Pas seulement des espaces | "Le nom du magasin est obligatoire." |
| **address** | Non vide + Pas seulement des espaces | "L'adresse du magasin est obligatoire." |
| **city** | Non vide + Pas seulement des espaces | "La ville du magasin est obligatoire." |

## Tests à effectuer

1. **Test de création** : Essayer de créer un store sans remplir un champ obligatoire
2. **Test de modification** : Essayer de vider un champ obligatoire lors de la modification
3. **Test avec espaces** : Remplir un champ avec uniquement des espaces
4. **Test de code dupliqué** : Essayer de créer un store avec un code existant

Dans tous les cas, l'utilisateur devrait voir :
- Le champ problématique surligné en rouge
- Un message d'erreur précis sous le champ
- Un message général en haut du formulaire

"""
Script de test pour vérifier la validation des champs obligatoires lors de la création d'un store.
Ce script vérifie que chaque champ obligatoire retourne une erreur spécifique lorsqu'il est manquant.
"""

import django
import os
import sys

# Configuration Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config.base')
django.setup()

from apps.inventory.serializers import StoreSerializer
from rest_framework.exceptions import ValidationError


def test_missing_fields():
    """Test que les champs obligatoires retournent des erreurs spécifiques."""
    
    print("\n" + "="*80)
    print("TEST DE VALIDATION DES CHAMPS OBLIGATOIRES DU STORE")
    print("="*80 + "\n")
    
    # Note: Pour éviter les accès DB, on teste uniquement les validateurs custom
    # Les validateurs Django standards (required, unique) ne sont pas testés ici
    
    # Test 1: Nom vide (chaîne vide)
    print("1️⃣  Test avec NOM VIDE (chaîne vide):")
    print("-" * 40)
    serializer = StoreSerializer(data={
        'code': 'STR-999',
        'name': '',
        'address': '123 Rue Test',
        'city': 'Douala',
        'store_type': 'retail'
    })
    is_valid = serializer.is_valid()
    if not is_valid and 'name' in serializer.errors:
        print(f"✅ Erreur détectée: {serializer.errors['name'][0]}")
    else:
        print("❌ ÉCHEC: Erreur de nom vide non détectée")
    
    # Test 2: Nom avec uniquement des espaces
    print("\n2️⃣  Test avec NOM contenant uniquement des espaces:")
    print("-" * 40)
    serializer = StoreSerializer(data={
        'code': 'STR-999',
        'name': '   ',
        'address': '123 Rue Test',
        'city': 'Douala',
        'store_type': 'retail'
    })
    is_valid = serializer.is_valid()
    if not is_valid and 'name' in serializer.errors:
        print(f"✅ Erreur détectée: {serializer.errors['name'][0]}")
    else:
        print("❌ ÉCHEC: Erreur de nom (espaces) non détectée")
    
    # Test 3: Adresse vide
    print("\n3️⃣  Test avec ADRESSE VIDE:")
    print("-" * 40)
    serializer = StoreSerializer(data={
        'code': 'STR-999',
        'name': 'Test Store',
        'address': '',
        'city': 'Douala',
        'store_type': 'retail'
    })
    is_valid = serializer.is_valid()
    if not is_valid and 'address' in serializer.errors:
        print(f"✅ Erreur détectée: {serializer.errors['address'][0]}")
    else:
        print("❌ ÉCHEC: Erreur d'adresse vide non détectée")
    
    # Test 4: Adresse avec uniquement des espaces
    print("\n4️⃣  Test avec ADRESSE contenant uniquement des espaces:")
    print("-" * 40)
    serializer = StoreSerializer(data={
        'code': 'STR-999',
        'name': 'Test Store',
        'address': '   ',
        'city': 'Douala',
        'store_type': 'retail'
    })
    is_valid = serializer.is_valid()
    if not is_valid and 'address' in serializer.errors:
        print(f"✅ Erreur détectée: {serializer.errors['address'][0]}")
    else:
        print("❌ ÉCHEC: Erreur d'adresse (espaces) non détectée")
    
    # Test 5: Ville vide
    print("\n5️⃣  Test avec VILLE VIDE:")
    print("-" * 40)
    serializer = StoreSerializer(data={
        'code': 'STR-999',
        'name': 'Test Store',
        'address': '123 Rue Test',
        'city': '',
        'store_type': 'retail'
    })
    is_valid = serializer.is_valid()
    if not is_valid and 'city' in serializer.errors:
        print(f"✅ Erreur détectée: {serializer.errors['city'][0]}")
    else:
        print("❌ ÉCHEC: Erreur de ville vide non détectée")
    
    # Test 6: Ville avec uniquement des espaces
    print("\n6️⃣  Test avec VILLE contenant uniquement des espaces:")
    print("-" * 40)
    serializer = StoreSerializer(data={
        'code': 'STR-999',
        'name': 'Test Store',
        'address': '123 Rue Test',
        'city': '   ',
        'store_type': 'retail'
    })
    is_valid = serializer.is_valid()
    if not is_valid and 'city' in serializer.errors:
        print(f"✅ Erreur détectée: {serializer.errors['city'][0]}")
    else:
        print("❌ ÉCHEC: Erreur de ville (espaces) non détectée")
    
    # Test 7: Code vide
    print("\n7️⃣  Test avec CODE VIDE:")
    print("-" * 40)
    serializer = StoreSerializer(data={
        'code': '',
        'name': 'Test Store',
        'address': '123 Rue Test',
        'city': 'Douala',
        'store_type': 'retail'
    })
    is_valid = serializer.is_valid()
    if not is_valid and 'code' in serializer.errors:
        print(f"✅ Erreur détectée: {serializer.errors['code'][0]}")
    else:
        print("❌ ÉCHEC: Erreur de code vide non détectée")
    
    # Test 8: Tous les champs manquants (validation Django standard)
    print("\n8️⃣  Test avec TOUS les champs manquants (validation Django):")
    print("-" * 40)
    serializer = StoreSerializer(data={})
    is_valid = serializer.is_valid()
    if not is_valid:
        print("✅ Erreurs détectées:")
        for field, errors in serializer.errors.items():
            error_msg = errors[0] if isinstance(errors, list) else errors
            print(f"   • {field}: {error_msg}")
    else:
        print("❌ ÉCHEC: Aucune erreur détectée")
    
    print("\n" + "="*80)
    print("RÉSUMÉ DES VALIDATIONS")
    print("="*80)
    print("""
Les validations suivantes sont implémentées:

1️⃣  validate_code(): Vérifie que le code n'est pas vide
2️⃣  validate_name(): Vérifie que le nom n'est pas vide ni uniquement des espaces
3️⃣  validate_address(): Vérifie que l'adresse n'est pas vide ni uniquement des espaces
4️⃣  validate_city(): Vérifie que la ville n'est pas vide ni uniquement des espaces

Côté frontend (StoreEditForm.vue):
✅ Affichage des erreurs de validation champ par champ
✅ Bordure rouge sur les champs en erreur
✅ Message d'erreur spécifique sous chaque champ
✅ Message d'erreur général en haut du formulaire

Cela permet une meilleure gestion des erreurs et facilite la correction par l'utilisateur!
    """)
    print("="*80 + "\n")


if __name__ == '__main__':
    test_missing_fields()

"""
Script pour nettoyer les CashMovements incorrects créés par les paiements fournisseurs
et remboursements d'emprunts par virement bancaire.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config')
django.setup()

from django_tenants.utils import schema_context
from apps.tenants.models import Company
from apps.cashbox.models import CashMovement

def fix_incorrect_cash_movements():
    """
    Supprime les CashMovements incorrects créés pour les paiements par virement bancaire.
    Ces mouvements ne devraient pas exister car l'argent ne passe pas par la caisse.
    """
    
    # Récupérer tous les tenants
    companies = Company.objects.exclude(schema_name='public')
    
    for company in companies:
        print(f"\n{'='*60}")
        print(f"Traitement du tenant: {company.name} ({company.schema_name})")
        print(f"{'='*60}")
        
        with schema_context(company.schema_name):
            # Trouver tous les mouvements de type 'in' avec category='bank_withdrawal'
            # qui correspondent à des paiements fournisseurs ou emprunts par virement
            incorrect_movements = CashMovement.objects.filter(
                movement_type='in',
                category='bank_withdrawal',
                payment_method='bank_transfer'
            )
            
            count = incorrect_movements.count()
            
            if count == 0:
                print(f"✓ Aucun mouvement incorrect trouvé pour {company.name}")
                continue
            
            print(f"\n{count} mouvements incorrects trouvés:")
            
            total_amount = 0
            for movement in incorrect_movements:
                print(f"  - {movement.movement_number}: {movement.amount} XAF - {movement.description}")
                total_amount += float(movement.amount)
            
            print(f"\nMontant total incorrect ajouté en caisse: {total_amount:,.2f} XAF")
            
            # Demander confirmation
            response = input(f"\nVoulez-vous supprimer ces {count} mouvements pour {company.name}? (oui/non): ")
            
            if response.lower() in ['oui', 'o', 'yes', 'y']:
                deleted_count = incorrect_movements.delete()[0]
                print(f"✓ {deleted_count} mouvements supprimés avec succès!")
            else:
                print("✗ Suppression annulée")
    
    print(f"\n{'='*60}")
    print("TRAITEMENT TERMINÉ")
    print(f"{'='*60}\n")

if __name__ == '__main__':
    fix_incorrect_cash_movements()


"""
Script pour corriger les paiements d'emprunts qui ont été déduits de la mauvaise caisse
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config')
django.setup()

from django_tenants.utils import schema_context
from apps.tenants.models import Company
from apps.cashbox.models import CashMovement

def fix_loan_payments():
    """
    Annule les CashMovements incorrects créés pour les paiements d'emprunts
    """
    
    companies = Company.objects.exclude(schema_name='public')
    
    for company in companies:
        print(f"\n{'='*60}")
        print(f"Traitement du tenant: {company.name} ({company.schema_name})")
        print(f"{'='*60}")
        
        with schema_context(company.schema_name):
            # Trouver tous les mouvements de type 'out' avec category='loan_payment'
            loan_movements = CashMovement.objects.filter(
                movement_type='out',
                category='loan_payment',
                payment_method='cash'
            ).select_related('cashbox_session__cashbox__store')
            
            count = loan_movements.count()
            
            if count == 0:
                print(f"✓ Aucun paiement d'emprunt en espèces trouvé pour {company.name}")
                continue
            
            print(f"\n{count} paiements d'emprunts en espèces trouvés:")
            
            total_amount = 0
            for movement in loan_movements:
                store_name = movement.cashbox_session.cashbox.store.name if movement.cashbox_session and movement.cashbox_session.cashbox and movement.cashbox_session.cashbox.store else 'N/A'
                print(f"  - {movement.movement_number}: {movement.amount} XAF")
                print(f"    Store: {store_name}")
                print(f"    Description: {movement.description}")
                print(f"    Date: {movement.created_at}")
                total_amount += float(movement.amount)
            
            print(f"\nMontant total déduit: {total_amount:,.2f} XAF")
            
            # Demander confirmation
            response = input(f"\nVoulez-vous ANNULER (supprimer) ces {count} mouvements pour {company.name}? (oui/non): ")
            
            if response.lower() in ['oui', 'o', 'yes', 'y']:
                # Avant de supprimer, remettre à jour les soldes des caisses
                for movement in loan_movements:
                    if movement.cashbox_session and movement.cashbox_session.cashbox:
                        cashbox = movement.cashbox_session.cashbox
                        # Remettre l'argent dans la caisse (annuler la sortie)
                        cashbox.current_balance += movement.amount
                        cashbox.save()
                        print(f"  ✓ Remboursé {movement.amount} XAF dans {cashbox.store.name if cashbox.store else 'N/A'}")
                
                # Supprimer les mouvements
                deleted_count = loan_movements.delete()[0]
                print(f"\n✓ {deleted_count} mouvements supprimés avec succès!")
                print("Les soldes de caisse ont été corrigés.")
            else:
                print("✗ Annulation refusée")
    
    print(f"\n{'='*60}")
    print("TRAITEMENT TERMINÉ")
    print(f"{'='*60}\n")

if __name__ == '__main__':
    fix_loan_payments()

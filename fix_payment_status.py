"""
Script pour corriger le statut des paiements
Usage: python fix_payment_status.py
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config')
django.setup()

from django.db import connection
from apps.invoicing.models import InvoicePayment

def fix_duplicate_payments():
    """Marquer les paiements en double comme échoués."""
    
    # Définir le schema
    schema_name = 'agribio'  # Changez selon votre tenant
    connection.set_schema(schema_name)
    
    print(f"\n🔧 Correction des paiements en double pour le schema: {schema_name}\n")
    
    # Trouver les paiements en double pour la même facture à la même date
    from django.db.models import Count
    from collections import defaultdict
    
    payments = InvoicePayment.objects.all().order_by('invoice', 'payment_date', 'created_at')
    
    # Grouper par facture et date
    grouped = defaultdict(list)
    for payment in payments:
        key = (payment.invoice_id, payment.payment_date)
        grouped[key].append(payment)
    
    # Trouver les doublons
    total_fixed = 0
    for key, payment_list in grouped.items():
        if len(payment_list) > 1:
            # Garder le dernier (le plus récent), marquer les autres comme échoués
            for payment in payment_list[:-1]:
                if payment.status != 'failed':
                    print(f"⚠️  Paiement en double trouvé:")
                    print(f"   N°: {payment.payment_number}")
                    print(f"   Facture: {payment.invoice.invoice_number}")
                    print(f"   Date: {payment.payment_date}")
                    print(f"   Montant: {payment.amount}")
                    print(f"   Statut actuel: {payment.status}")
                    
                    payment.status = 'failed'
                    payment.save()
                    
                    print(f"   ✅ Statut mis à jour: failed\n")
                    total_fixed += 1
    
    print(f"{'='*60}")
    print(f"✅ Terminé!")
    print(f"   Total de paiements corrigés: {total_fixed}")
    print(f"{'='*60}\n")

if __name__ == '__main__':
    fix_duplicate_payments()

"""
Script pour supprimer les 2 factures de test de 100 000 FCFA de Enzo (CLI00002)
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config.dev')
django.setup()

from django.db import connection
from apps.invoicing.models import Invoice

def delete_test_invoices():
    schema_name = 'agribio'
    connection.set_schema(schema_name)
    
    print(f"\n🗑️  Suppression des factures de test pour Enzo (CLI00002)")
    
    # Les 2 factures de test identifiées
    test_invoice_numbers = ['FAC2026000002', 'FAC2026000003']
    
    for invoice_number in test_invoice_numbers:
        try:
            invoice = Invoice.objects.get(invoice_number=invoice_number)
            print(f"\n📋 Facture trouvée: {invoice.invoice_number}")
            print(f"   Client: {invoice.customer.name}")
            print(f"   Montant: {invoice.total_amount} FCFA")
            print(f"   Montant payé: {invoice.paid_amount} FCFA")
            print(f"   Statut: {invoice.status}")
            
            # Supprimer d'abord tous les paiements
            payments = invoice.payments.all()
            if payments.exists():
                payment_count = payments.count()
                payments.delete()
                print(f"   🗑️  {payment_count} paiement(s) supprimé(s)")
            
            # Supprimer la facture
            invoice.delete()
            print(f"   ✅ Facture supprimée avec succès")
            
        except Invoice.DoesNotExist:
            print(f"\n❌ Facture {invoice_number} non trouvée")
    
    print(f"\n✅ Opération terminée !")

if __name__ == '__main__':
    delete_test_invoices()

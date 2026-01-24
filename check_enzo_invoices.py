"""
Script pour vérifier les factures du client Enzo
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config.dev')
django.setup()

from django.db import connection
from apps.customers.models import Customer
from apps.invoicing.models import Invoice

def check_enzo_invoices():
    schema_name = 'agribio'
    connection.set_schema(schema_name)
    
    print(f"\n🔍 Vérification des factures pour le client Enzo (CLI00002)")
    
    try:
        customer = Customer.objects.get(customer_code='CLI00002')
        print(f"\n✅ Client trouvé: {customer.name} ({customer.customer_code})")
        
        invoices = customer.invoices.all()
        print(f"\n📄 Nombre de factures: {invoices.count()}")
        
        total_invoiced = 0
        total_paid = 0
        
        for invoice in invoices:
            print(f"\n📋 Facture: {invoice.invoice_number}")
            print(f"   Date: {invoice.invoice_date}")
            print(f"   Montant total: {invoice.total_amount} FCFA")
            print(f"   Montant payé: {invoice.paid_amount} FCFA")
            print(f"   Solde dû: {invoice.total_amount - invoice.paid_amount} FCFA")
            print(f"   Statut: {invoice.status}")
            
            # Vérifier les paiements
            payments = invoice.payments.all()
            if payments.exists():
                print(f"   Paiements:")
                for payment in payments:
                    print(f"      - {payment.payment_number}: {payment.amount} FCFA (Statut: {payment.status})")
            
            total_invoiced += invoice.total_amount
            total_paid += invoice.paid_amount
        
        print(f"\n💰 TOTAUX:")
        print(f"   Total facturé: {total_invoiced} FCFA")
        print(f"   Total payé: {total_paid} FCFA")
        print(f"   Solde: {total_invoiced - total_paid} FCFA")
        
    except Customer.DoesNotExist:
        print("\n❌ Client Enzo (CLI00002) non trouvé")

if __name__ == '__main__':
    check_enzo_invoices()

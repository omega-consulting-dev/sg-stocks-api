"""
Script pour supprimer toutes les factures du client "Client No Name" (CLI00001)
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config.dev')
django.setup()

from django.db import connection
from apps.customers.models import Customer
from apps.invoicing.models import Invoice, InvoicePayment

def delete_noname_invoices():
    schema_name = 'agribio'
    connection.set_schema(schema_name)
    
    print(f"\n🗑️  Suppression des factures pour le client CLI00001 (No Name)")
    
    try:
        customer = Customer.objects.get(customer_code='CLI00001')
        print(f"\n✅ Client trouvé: {customer.name} ({customer.customer_code})")
        
        invoices = customer.invoices.all()
        invoice_count = invoices.count()
        
        if invoice_count == 0:
            print("\n✅ Aucune facture à supprimer")
            return
        
        print(f"\n📄 Nombre de factures à supprimer: {invoice_count}")
        
        # Lister les factures avant suppression
        for invoice in invoices:
            payments_count = invoice.payments.count()
            print(f"\n📋 Facture: {invoice.invoice_number}")
            print(f"   Montant: {invoice.total_amount} FCFA")
            print(f"   Paiements: {payments_count}")
        
        # Supprimer toutes les factures (les paiements seront supprimés en cascade)
        deleted_count, deleted_details = invoices.delete()
        
        print(f"\n✅ Suppression terminée !")
        print(f"   Factures supprimées: {deleted_details.get('invoicing.Invoice', 0)}")
        print(f"   Paiements supprimés: {deleted_details.get('invoicing.InvoicePayment', 0)}")
        print(f"   Total objets supprimés: {deleted_count}")
        
    except Customer.DoesNotExist:
        print("\n❌ Client CLI00001 non trouvé")

if __name__ == '__main__':
    delete_noname_invoices()

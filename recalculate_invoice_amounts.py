"""
Script pour recalculer les montants payés des factures en ne comptant que les paiements réussis
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config.dev')
django.setup()

from django.db import connection
from apps.invoicing.models import Invoice

def recalculate_invoice_amounts():
    # Schéma agribio
    schema_name = 'agribio'
    connection.set_schema(schema_name)
    
    print(f"\n🔄 Recalcul des montants payés pour le tenant: {schema_name}")
    
    invoices = Invoice.objects.all()
    updated_count = 0
    
    for invoice in invoices:
        # Calculer le total payé avec uniquement les paiements réussis
        total_paid = sum(
            payment.amount 
            for payment in invoice.payments.filter(status='success')
        )
        
        if invoice.paid_amount != total_paid:
            print(f"\n📄 Facture: {invoice.invoice_number}")
            print(f"   Ancien montant payé: {invoice.paid_amount}")
            print(f"   Nouveau montant payé: {total_paid}")
            
            invoice.paid_amount = total_paid
            
            # Mettre à jour le statut
            if invoice.paid_amount >= invoice.total_amount:
                invoice.status = 'paid'
            elif invoice.paid_amount > 0:
                invoice.status = 'partial'
            else:
                invoice.status = 'draft'
            
            invoice.save(update_fields=['paid_amount', 'status'])
            updated_count += 1
    
    print(f"\n✅ Terminé ! {updated_count} facture(s) mise(s) à jour")

if __name__ == '__main__':
    recalculate_invoice_amounts()

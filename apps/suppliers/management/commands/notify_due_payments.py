from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.suppliers.models import PurchaseOrder
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import F
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Notify about supplier payments due in 3 days and 1 day for the current tenant.'

    def handle(self, *args, **options):
        today = timezone.now().date()
        targets = [today + timedelta(days=3), today + timedelta(days=1)]

        for target in targets:
            orders = PurchaseOrder.objects.filter(due_date=target).exclude(total_amount__lte=F('paid_amount'))
            count = orders.count()
            if count == 0:
                self.stdout.write(f'No due payments for {target}')
                continue

            self.stdout.write(f'Found {count} purchase orders due on {target}')

            for po in orders:
                balance = po.total_amount - po.paid_amount
                subject = f"Paiement dû: PO {po.order_number} le {po.due_date}"
                message = (
                    f"La commande {po.order_number} pour le fournisseur {po.supplier.name} "
                    f"est due le {po.due_date}. Montant dû: {balance}.\n" 
                    f"Merci de procéder au règlement."
                )

                # Try sending to supplier email if available
                recipients = []
                if po.supplier.email:
                    recipients.append(po.supplier.email)

                # Also notify admins if configured
                admins = [a[1] for a in getattr(settings, 'ADMINS', [])]
                recipients += admins

                if recipients:
                    try:
                        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, recipients)
                        self.stdout.write(f'Sent notification for PO {po.order_number} to {recipients}')
                    except Exception as e:
                        logger.exception(f'Failed to send notification for PO {po.order_number}: {e}')
                else:
                    # Fallback to logging
                    logger.info(f'Notification (no recipients) PO {po.order_number}: {message}')

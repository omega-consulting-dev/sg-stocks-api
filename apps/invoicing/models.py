from django.db import models
from django.core.validators import MinValueValidator
from django.db.models.signals import post_save
from django.dispatch import receiver
from core.models import TimeStampedModel, AuditModel


class Invoice(AuditModel):
    """Invoice model for billing customers."""
    
    STATUS_CHOICES = [
        ('draft', 'Brouillon'),
        ('sent', 'Envoyée'),
        ('paid', 'Payée'),
        ('overdue', 'En retard'),
        ('cancelled', 'Annulée'),
    ]
    
    invoice_number = models.CharField(max_length=50, unique=True, verbose_name="Numéro de facture")
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.PROTECT,
        related_name='invoices',
        verbose_name="Client"
    )
    sale = models.OneToOneField(
        'sales.Sale',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invoice',
        verbose_name="Vente"
    )
    store = models.ForeignKey(
        'inventory.Store',
        on_delete=models.PROTECT,
        related_name='invoices',
        verbose_name="Point de vente"
    )
    
    # Dates
    invoice_date = models.DateField(verbose_name="Date de facture")
    due_date = models.DateField(verbose_name="Date d'échéance")
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name="Statut"
    )
    
    # Financial
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Sous-total"
    )
    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Montant remise"
    )
    tax_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Montant TVA"
    )
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Montant total"
    )
    paid_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Montant payé"
    )
    
    # Payment terms
    payment_term = models.CharField(
        max_length=20,
        choices=[
            ('immediate', 'Comptant'),
            ('15_days', '15 jours'),
            ('30_days', '30 jours'),
            ('60_days', '60 jours'),
        ],
        default='30_days',
        verbose_name="Conditions de paiement"
    )
    
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    class Meta:
        verbose_name = "Facture"
        verbose_name_plural = "Factures"
        ordering = ['-invoice_date']
    
    def __str__(self):
        return f"{self.invoice_number} - {self.customer.name}"
    
    def save(self, *args, **kwargs):
        """Generate invoice number if not provided."""
        if not self.invoice_number:
            from django.utils import timezone
            # Generate invoice number: FAC-YYYY-XXXXXX
            today = timezone.now().date()
            year = today.strftime('%Y')
            
            # Count invoices created this year
            year_invoices = Invoice.objects.filter(
                invoice_number__startswith=f'FAC{year}'
            ).count()
            
            self.invoice_number = f'FAC{year}{year_invoices + 1:06d}'
        
        super().save(*args, **kwargs)
    
    @property
    def balance_due(self):
        """Calculate remaining balance."""
        from decimal import Decimal, ROUND_HALF_UP
        balance = self.total_amount - self.paid_amount
        return balance.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @property
    def is_fully_paid(self):
        """Check if invoice is fully paid."""
        return self.paid_amount >= self.total_amount
    
    @property
    def is_overdue(self):
        """Check if invoice is overdue."""
        from django.utils import timezone
        return (
            self.status not in ['paid', 'cancelled'] and
            self.due_date < timezone.now().date()
        )
    
    @property
    def total_items(self):
        """Calculate total quantity of items."""
        return sum(line.quantity for line in self.lines.all())
    
    def send_by_email(self):
        """Send invoice by email to customer."""
        # TODO: Implement email sending
        pass
    
    def generate_pdf(self):
        """Generate PDF version of invoice."""
        from core.utils.pdf_templates import InvoicePDFGenerator
        import io
        
        buffer = io.BytesIO()
        generator = InvoicePDFGenerator(self)
        generator.generate(buffer)
        return buffer
    
    @classmethod
    def generate_from_sale(cls, sale):
        """Generate invoice from a confirmed sale."""
        from datetime import timedelta
        
        if sale.status not in ['confirmed', 'completed']:
            raise ValueError('Can only generate invoice from confirmed or completed sales')
        
        if hasattr(sale, 'invoice') and sale.invoice:
            raise ValueError('Invoice already exists for this sale')
        
        # Calculate due date based on payment term
        payment_term_days = {
            'immediate': 0,
            '15_days': 15,
            '30_days': 30,
            '60_days': 60
        }
        due_days = payment_term_days.get(sale.payment_term, 30) if hasattr(sale, 'payment_term') else 30
        due_date = sale.sale_date + timedelta(days=due_days)
        
        # Create invoice from sale
        invoice = cls.objects.create(
            customer=sale.customer,
            sale=sale,
            store=sale.store,
            created_by=sale.created_by,  # Copy creator from sale
            invoice_date=sale.sale_date,
            due_date=due_date,
            status='draft',
            subtotal=sale.subtotal,
            discount_amount=sale.discount_amount,
            tax_amount=sale.tax_amount,
            total_amount=sale.total_amount,
            paid_amount=sale.paid_amount,
            payment_term='immediate',
            notes=sale.notes
        )
        
        # Copy sale lines to invoice lines
        for sale_line in sale.lines.all():
            InvoiceLine.objects.create(
                invoice=invoice,
                product=sale_line.product,
                service=sale_line.service,
                description=sale_line.description or (
                    sale_line.product.name if sale_line.product else sale_line.service.name
                ),
                quantity=sale_line.quantity,
                unit_price=sale_line.unit_price,
                tax_rate=sale_line.tax_rate,
                discount_percentage=sale_line.discount_percentage
            )
        
        return invoice


class InvoiceLine(TimeStampedModel):
    """Invoice line items."""
    
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='lines',
        verbose_name="Facture"
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='invoice_lines',
        verbose_name="Produit"
    )
    service = models.ForeignKey(
        'services.Service',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='invoice_lines',
        verbose_name="Service"
    )
    description = models.CharField(max_length=200, verbose_name="Description")
    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Quantité"
    )
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Prix unitaire"
    )
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=19.25,
        verbose_name="Taux TVA (%)"
    )
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Remise (%)"
    )
    
    class Meta:
        verbose_name = "Ligne de facture"
        verbose_name_plural = "Lignes de facture"
    
    def __str__(self):
        return f"{self.description} - {self.quantity}"
    
    @property
    def subtotal(self):
        """Calculate line subtotal."""
        return self.quantity * self.unit_price
    
    @property
    def discount_amount(self):
        """Calculate discount amount."""
        return self.subtotal * (self.discount_percentage / 100)
    
    @property
    def subtotal_after_discount(self):
        """Calculate subtotal after discount."""
        return self.subtotal - self.discount_amount
    
    @property
    def tax_amount(self):
        """Calculate tax amount."""
        return self.subtotal_after_discount * (self.tax_rate / 100)
    
    @property
    def total(self):
        """Calculate line total."""
        return self.subtotal_after_discount + self.tax_amount


class InvoicePayment(AuditModel):
    """Invoice payment tracking."""
    
    payment_number = models.CharField(max_length=50, unique=True, verbose_name="Numéro de paiement")
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.PROTECT,
        related_name='payments',
        verbose_name="Facture"
    )
    
    # Payment details
    payment_date = models.DateField(verbose_name="Date de paiement")
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Montant"
    )
    
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Espèces'),
        ('card', 'Carte bancaire'),
        ('mobile_money', 'Mobile Money'),
        ('check', 'Chèque'),
        ('bank_transfer', 'Virement'),
    ]
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        verbose_name="Mode de paiement"
    )
    
    reference = models.CharField(max_length=100, blank=True, verbose_name="Référence")
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    class Meta:
        verbose_name = "Paiement de facture"
        verbose_name_plural = "Paiements de facture"
        ordering = ['-payment_date']
    
    def __str__(self):
        return f"{self.payment_number} - {self.amount}"
    
    def save(self, *args, **kwargs):
        """Generate payment number if not provided."""
        if not self.payment_number:
            from django.utils import timezone
            # Generate payment number: PAY-YYYYMMDD-XXXX
            today = timezone.now().date()
            date_str = today.strftime('%Y%m%d')
            
            # Count payments created today
            today_payments = InvoicePayment.objects.filter(
                payment_number__startswith=f'PAY-{date_str}'
            ).count()
            
            self.payment_number = f'PAY-{date_str}-{today_payments + 1:04d}'
        
        super().save(*args, **kwargs)


# Fonction pour créer automatiquement les mouvements de stock
# Appelée manuellement dans le serializer après la création des lignes
def create_stock_movements_from_invoice(sender, instance, created, **kwargs):
    """
    Créer automatiquement les mouvements de stock quand une facture est créée.
    - Caissier crée facture → mouvement de sortie automatique
    - Sécurise les données : vérifie stock disponible, enregistre traçabilité complète
    """
    # Éviter les boucles infinies et traiter uniquement les factures confirmées
    if kwargs.get('raw', False):
        return
    
    # Créer mouvements dès la création de la facture (pas uniquement quand envoyée/payée)
    # Car dans le workflow actuel, les factures sont créées directement comme des ventes
    if not created:
        return  # Uniquement à la création, pas aux mises à jour
    
    # Vérifier si on a déjà créé les mouvements pour cette facture
    from apps.inventory.models import StockMovement, Stock
    
    existing_movements = StockMovement.objects.filter(
        reference=f"FACT-{instance.invoice_number}"
    ).exists()
    
    if existing_movements:
        return  # Mouvements déjà créés
    
    # Créer un mouvement pour chaque ligne de facture qui a un produit
    for line in instance.lines.all():
        # Vérifier si la ligne a une référence à un produit
        # (les lignes peuvent être des produits ou des services)
        if hasattr(line, 'product') and line.product:
            # Vérifier le stock disponible AVANT de créer le mouvement
            stock = Stock.objects.filter(
                product=line.product,
                store=instance.store
            ).first()
            
            # Bloquer si stock insuffisant
            if not stock or stock.available_quantity < line.quantity:
                from rest_framework.exceptions import ValidationError
                available = stock.available_quantity if stock else 0
                raise ValidationError({
                    'detail': f"Stock insuffisant pour {line.product.name}. "
                              f"Disponible: {available}, Demandé: {line.quantity}"
                })
            
            try:
                # Créer mouvement de sortie - le signal update_stock_on_movement mettra à jour le stock
                StockMovement.objects.create(
                    product=line.product,
                    store=instance.store,
                    movement_type='out',
                    quantity=line.quantity,
                    total_value=line.total,  # Montant total de la ligne (avec taxes)
                    invoice=instance,  # Lien vers la facture
                    reference=f"FACT-{instance.invoice_number}",
                    notes=f"Sortie automatique - Facture {instance.invoice_number} - Client: {instance.customer.name}",
                    created_by=instance.created_by,
                    is_active=True
                )
                # Note: Le stock sera mis à jour automatiquement par le signal update_stock_on_movement
                
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(
                    f"Erreur création mouvement stock pour facture {instance.invoice_number}, "
                    f"produit {line.product.name}: {str(e)}"
                )

        verbose_name_plural = "Paiements de factures"
        ordering = ['-payment_date']
    
    def __str__(self):
        return f"{self.payment_number} - {self.invoice.invoice_number} ({self.amount})"

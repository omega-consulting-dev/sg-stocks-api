import pytest
from datetime import date, timedelta
from decimal import Decimal
from django.utils import timezone

from apps.invoicing.models import Invoice, InvoiceLine, InvoicePayment
from apps.accounts.models import User


@pytest.mark.django_db
class TestInvoiceModel:
    """Tests for Invoice model."""
    
    @pytest.fixture
    def customer(self):
        """Create a test customer."""
        return User.objects.create_user(
            username='customer1',
            email='customer@test.com',
            password='test123',
            is_customer=True,
            customer_code='CLI00001'
        )
    
    @pytest.fixture
    def invoice(self, customer):
        """Create a test invoice."""
        return Invoice.objects.create(
            invoice_number='FAC202500001',
            customer=customer,
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            subtotal=Decimal('100000'),
            tax_amount=Decimal('19250'),
            total_amount=Decimal('119250'),
            payment_term='30_days'
        )
    
    def test_create_invoice(self, invoice, customer):
        """Test invoice creation."""
        assert invoice.invoice_number == 'FAC202500001'
        assert invoice.customer == customer
        assert invoice.status == 'draft'
        assert invoice.balance_due == Decimal('119250')
    
    def test_invoice_balance_due(self, invoice):
        """Test balance due calculation."""
        assert invoice.balance_due == invoice.total_amount
        
        # Make a payment
        invoice.paid_amount = Decimal('50000')
        invoice.save()
        
        assert invoice.balance_due == Decimal('69250')
    
    def test_invoice_is_fully_paid(self, invoice):
        """Test is_fully_paid property."""
        assert not invoice.is_fully_paid
        
        invoice.paid_amount = invoice.total_amount
        invoice.save()
        
        assert invoice.is_fully_paid
    
    def test_invoice_is_overdue(self, invoice):
        """Test is_overdue property."""
        # Not overdue yet
        assert not invoice.is_overdue
        
        # Make it overdue
        invoice.due_date = date.today() - timedelta(days=1)
        invoice.save()
        
        assert invoice.is_overdue
        
        # Paid invoices are not overdue
        invoice.status = 'paid'
        invoice.save()
        
        assert not invoice.is_overdue


@pytest.mark.django_db
class TestInvoiceLine:
    """Tests for InvoiceLine model."""
    
    @pytest.fixture
    def invoice(self):
        """Create a test invoice."""
        customer = User.objects.create_user(
            username='customer1',
            email='customer@test.com',
            password='test123',
            is_customer=True
        )
        
        return Invoice.objects.create(
            invoice_number='FAC202500001',
            customer=customer,
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=30)
        )
    
    def test_create_invoice_line(self, invoice):
        """Test invoice line creation."""
        line = InvoiceLine.objects.create(
            invoice=invoice,
            description='Product Test',
            quantity=Decimal('2'),
            unit_price=Decimal('50000'),
            tax_rate=Decimal('19.25')
        )
        
        assert line.subtotal == Decimal('100000')
        assert line.tax_amount == Decimal('19250')
        assert line.total == Decimal('119250')
    
    def test_line_with_discount(self, invoice):
        """Test line with discount."""
        line = InvoiceLine.objects.create(
            invoice=invoice,
            description='Product Test',
            quantity=Decimal('1'),
            unit_price=Decimal('100000'),
            tax_rate=Decimal('19.25'),
            discount_percentage=Decimal('10')
        )
        
        assert line.discount_amount == Decimal('10000')
        assert line.subtotal_after_discount == Decimal('90000')
        assert line.tax_amount == Decimal('17325')
        assert line.total == Decimal('107325')


@pytest.mark.django_db
class TestInvoicePayment:
    """Tests for InvoicePayment model."""
    
    @pytest.fixture
    def invoice(self):
        """Create a test invoice."""
        customer = User.objects.create_user(
            username='customer1',
            email='customer@test.com',
            password='test123',
            is_customer=True
        )
        
        return Invoice.objects.create(
            invoice_number='FAC202500001',
            customer=customer,
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            total_amount=Decimal('100000')
        )
    
    def test_create_payment(self, invoice):
        """Test payment creation."""
        payment = InvoicePayment.objects.create(
            payment_number='FAC202500001-PAY001',
            invoice=invoice,
            payment_date=date.today(),
            amount=Decimal('50000'),
            payment_method='cash'
        )
        
        assert payment.invoice == invoice
        assert payment.amount == Decimal('50000')
        assert payment.payment_method == 'cash'
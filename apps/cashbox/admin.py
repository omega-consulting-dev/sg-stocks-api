from django.contrib import admin
from apps.cashbox.models import Cashbox, CashboxSession, CashMovement

@admin.register(Cashbox)
class CashboxAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'store', 'current_balance', 'is_active']
    list_filter = ['store', 'is_active']


@admin.register(CashboxSession)
class CashboxSessionAdmin(admin.ModelAdmin):
    list_display = ['cashbox', 'cashier', 'opening_date', 'closing_date', 'status']
    list_filter = ['status', 'opening_date']


@admin.register(CashMovement)
class CashMovementAdmin(admin.ModelAdmin):
    list_display = ['movement_number', 'cashbox_session', 'movement_type', 'category', 'amount', 'created_at']
    list_filter = ['movement_type', 'category', 'payment_method']

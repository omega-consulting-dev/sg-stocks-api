from django.contrib import admin
from apps.inventory.models import (
    Store, Stock, StockMovement, StockTransfer, 
    StockTransferLine, Inventory, InventoryLine
)

@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'store_type', 'city', 'manager', 'is_active']
    list_filter = ['store_type', 'is_active', 'city']
    search_fields = ['name', 'code']


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ['product', 'store', 'quantity', 'reserved_quantity', 'available_quantity']
    list_filter = ['store']
    search_fields = ['product__name', 'product__reference']


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ['product', 'store', 'movement_type', 'quantity', 'created_at']
    list_filter = ['movement_type', 'store', 'created_at']


class StockTransferLineInline(admin.TabularInline):
    model = StockTransferLine
    extra = 1


@admin.register(StockTransfer)
class StockTransferAdmin(admin.ModelAdmin):
    list_display = ['transfer_number', 'source_store', 'destination_store', 'status', 'transfer_date']
    list_filter = ['status', 'transfer_date']
    inlines = [StockTransferLineInline]


class InventoryLineInline(admin.TabularInline):
    model = InventoryLine
    extra = 1


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ['inventory_number', 'store', 'inventory_date', 'status']
    list_filter = ['status', 'inventory_date', 'store']
    inlines = [InventoryLineInline]

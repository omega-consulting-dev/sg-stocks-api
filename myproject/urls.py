from django.contrib import admin
from django.conf.urls.static import static
from django.urls import path, include
from myproject import config

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # API v1
    path('api/v1/auth/', include('apps.accounts.urls')),
    path('api/v1/tenants/', include('apps.tenants.urls')),
    path('api/v1/products/', include('apps.products.urls')),
    path('api/v1/services/', include('apps.services.urls')),
    path('api/v1/inventory/', include('apps.inventory.urls')),
    path('api/v1/sales/', include('apps.sales.urls')),
    path('api/v1/invoices/', include('apps.invoicing.urls')),
    path('api/v1/customers/', include('apps.customers.urls')),
    path('api/v1/suppliers/', include('apps.suppliers.urls')),
    path('api/v1/cashbox/', include('apps.cashbox.urls')),
    path('api/v1/loans/', include('apps.loans.urls')),
    path('api/v1/expenses/', include('apps.expenses.urls')),
    path('api/v1/analytics/', include('apps.analytics.urls')),
]

# Static and media files in development
if config.DEBUG:
    urlpatterns += static(config.MEDIA_URL, document_root=config.MEDIA_ROOT)
    urlpatterns += static(config.STATIC_URL, document_root=config.STATIC_ROOT)

    if 'debug_toolbar' in config.INSTALLED_APPS:
        import debug_toolbar
        urlpatterns += [path('__debug__/', include(debug_toolbar.urls))]

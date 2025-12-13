from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.expenses.views import ExpenseViewSet, ExpenseCategoryViewSet, ExpenseExportExcelView

router = DefaultRouter()
router.register(r'expenses', ExpenseViewSet, basename='expense')
router.register(r'categories', ExpenseCategoryViewSet, basename='category')

# Vue directe pour l'export Excel
urlpatterns = [
    path('expenses/export_excel/', ExpenseExportExcelView.as_view(), name='export-excel'),
    path('', include(router.urls)),
]
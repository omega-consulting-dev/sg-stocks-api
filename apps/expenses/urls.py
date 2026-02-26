from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.expenses.views import ExpenseViewSet, ExpenseCategoryViewSet

router = DefaultRouter()
router.register(r'', ExpenseViewSet, basename='expense')
router.register(r'categories', ExpenseCategoryViewSet, basename='category')

urlpatterns = [
    path('', include(router.urls)),
]
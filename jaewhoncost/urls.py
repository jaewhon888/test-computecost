from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    OwnerViewSet, BranchViewSet, IngredientViewSet,
    RecipeViewSet, RecipeItemViewSet, MenuViewSet,
    SaleViewSet, SettingViewSet,
    PriceHistoryViewSet, PurchaseViewSet, PurchaseItemViewSet,
    DashboardView, IngredientsView, RecipesView, MenusView,
    PurchasesView, PriceHistoryReportView, SalesView, BranchesView, OwnersView, SettingsView,
    CostCalculationView, CostCalculatorFormView
)

router = DefaultRouter()
router.register(r'owners', OwnerViewSet)
router.register(r'branches', BranchViewSet)
router.register(r'ingredients', IngredientViewSet)
router.register(r'recipes', RecipeViewSet)
router.register(r'recipe-items', RecipeItemViewSet)
router.register(r'menus', MenuViewSet)
router.register(r'sales', SaleViewSet)
router.register(r'settings', SettingViewSet)
router.register(r'price-history', PriceHistoryViewSet)
router.register(r'purchases', PurchaseViewSet)
router.register(r'purchase-items', PurchaseItemViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
    path('', DashboardView.as_view(), name='dashboard'),
    path('ingredients/', IngredientsView.as_view(), name='ingredients'),
    path('recipes/', RecipesView.as_view(), name='recipes'),
    path('menus/', MenusView.as_view(), name='menus'),
    path('purchases/', PurchasesView.as_view(), name='purchases'),
    path('price-history-report/', PriceHistoryReportView.as_view(), name='price_history_report'),
    path('sales/', SalesView.as_view(), name='sales'),
    path('branches/', BranchesView.as_view(), name='branches'),
    path('owners/', OwnersView.as_view(), name='owners'),
    path('settings/', SettingsView.as_view(), name='settings'),
    path('cost-calculation/', CostCalculationView.as_view(), name='cost_calculation'),
    path('cost-calculator/', CostCalculatorFormView.as_view(), name='cost_calculator'),
    path('profit-report/', SaleViewSet.as_view({'get': 'profit_report'}), name='profit_report'),
]


from django.shortcuts import render
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.template.loader import render_to_string

# Create your views here.
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Owner, Branch, Ingredient, Recipe, RecipeItem, Menu, Sale, Setting, PriceHistory, Purchase, PurchaseItem
from .serializers import (
    OwnerSerializer, BranchSerializer, IngredientSerializer,
    RecipeSerializer, RecipeItemSerializer, MenuSerializer,
    SaleSerializer, SettingSerializer,
    PriceHistorySerializer, PurchaseSerializer, PurchaseItemSerializer
)
from .forms import CostCalculationForm
import json

# ViewSets
class OwnerViewSet(viewsets.ModelViewSet):
    queryset = Owner.objects.all()
    serializer_class = OwnerSerializer


class BranchViewSet(viewsets.ModelViewSet):
    queryset = Branch.objects.all()
    serializer_class = BranchSerializer
    pagination_class = None
    
    @action(detail=True, methods=['get'])
    def ingredients(self, request, pk=None):
        branch = self.get_object()
        ingredients = branch.ingredients.all()
        serializer = IngredientSerializer(ingredients, many=True)
        return Response(serializer.data)


class IngredientViewSet(viewsets.ModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None
    
    def get_queryset(self):
        branch_id = self.request.query_params.get('branch_id')
        if branch_id:
            return Ingredient.objects.filter(branch_id=branch_id)
        return Ingredient.objects.all()


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    
    def get_queryset(self):
        branch_id = self.request.query_params.get('branch_id')
        if branch_id:
            return Recipe.objects.filter(branch_id=branch_id)
        return Recipe.objects.all()
    
    @action(detail=True, methods=['post'])
    def calculate_cost(self, request, pk=None):
        """API endpoint สำหรับคำนวณต้นทุนแบบ real-time (รองรับการคำนวณตามช่วงวันที่)"""
        recipe = self.get_object()
        data = request.data
        
        # รับพารามิเตอร์จาก request
        waste_percent = float(data.get('waste_percent', 5.0))
        target_food_cost_percent = float(data.get('target_food_cost_percent', 30.0))
        
        # รับพารามิเตอร์วันที่สำหรับการคำนวณย้อนหลัง
        calculation_date = data.get('calculation_date')
        use_historical_prices = data.get('use_historical_prices', False)
        
        # Overhead costs
        overhead_costs = {
            'utilities': float(data.get('overhead_utilities', 4.80)),
            'labor': float(data.get('overhead_labor', 16.20)),
            'rent': float(data.get('overhead_rent', 6.00)),
            'depreciation': float(data.get('overhead_depreciation', 1.80)),
            'marketing': float(data.get('overhead_marketing', 1.80)),
            'delivery': float(data.get('overhead_delivery', 17.01)),
        }
        total_overhead = sum(overhead_costs.values())
        
        # คำนวณต้นทุนวัตถุดิบ
        total_ingredient_cost = 0
        items_detail = []
        
        for item in recipe.items.all():
            quantity = float(item.quantity)
            
            # ถ้ามีการระบุวันที่และต้องการใชราคาย้อนหลัง
            if calculation_date and use_historical_prices:
                from django.utils import timezone
                from datetime import datetime
                calc_date = datetime.strptime(calculation_date, '%Y-%m-%d')
                
                # ค้นหาราคาวัตถุดิบที่มีผลบังคับใช้ก่อนหรือในวันที่ระบุ
                price_history = item.ingredient.price_history.filter(
                    effective_date__lte=calc_date
                ).order_by('-effective_date').first()
                
                if price_history:
                    price_per_unit = float(price_history.price)
                else:
                    # ถ้าไม่มีประวัติ ใชราคาปัจจุบัน
                    price_per_unit = float(item.ingredient.price)
            else:
                # ใชราคาปัจจุบัน
                price_per_unit = float(item.ingredient.price)
            
            item_cost = quantity * price_per_unit
            total_ingredient_cost += item_cost
            
            items_detail.append({
                'ingredient_name': item.ingredient.name,
                'quantity': float(item.quantity),
                'unit': item.ingredient.unit,
                'price_per_unit': price_per_unit,
                'cost': item_cost,
                'is_historical': calculation_date and use_historical_prices,
            })
        
        # คำนวณตามมาตรฐานสากล
        waste_factor = waste_percent / 100.0
        standard_food_cost = target_food_cost_percent / 100.0
        
        effective_cost = total_ingredient_cost / (1 - waste_factor) if waste_factor < 1 else total_ingredient_cost
        total_cost_with_overhead = effective_cost + total_overhead
        suggested_price = total_ingredient_cost / standard_food_cost if standard_food_cost > 0 else 0
        
        # หาราคาขายจริง
        menu = recipe.menu_set.first()
        actual_selling_price = float(menu.price) if menu else 0
        
        # คำนวณกำไรจริง
        if actual_selling_price > 0:
            actual_profit = actual_selling_price - total_cost_with_overhead
            actual_profit_percent = (actual_profit / actual_selling_price) * 100
            actual_food_cost_percent = (total_cost_with_overhead / actual_selling_price) * 100
        else:
            actual_profit = actual_profit_percent = actual_food_cost_percent = 0
        
        return Response({
            'recipe_name': recipe.name,
            'branch_name': recipe.branch.name,
            'calculation_date': calculation_date,
            'use_historical_prices': use_historical_prices,
            'total_ingredient_cost': total_ingredient_cost,
            'items': items_detail,
            'waste_percent': waste_percent,
            'effective_cost': effective_cost,
            'overhead_costs': overhead_costs,
            'total_overhead': total_overhead,
            'total_cost_with_overhead': total_cost_with_overhead,
            'actual_selling_price': actual_selling_price,
            'suggested_price': suggested_price,
            'actual_profit': actual_profit,
            'actual_profit_percent': actual_profit_percent,
            'actual_food_cost_percent': actual_food_cost_percent,
            'target_food_cost_percent': target_food_cost_percent,
            'calculation_steps': [
                f'1. รวมต้นทุนวัตถุดิบ: {total_ingredient_cost:.2f} บาท' + (' (ราคาย้อนหลัง)' if calculation_date else ''),
                f'2. Waste {waste_percent}%: {total_ingredient_cost:.2f} ÷ (1 - {waste_factor}) = {effective_cost:.2f} บาท',
                f'3. Overhead: {total_overhead:.2f} บาท',
                f'4. ต้นทุนรวม: {total_cost_with_overhead:.2f} บาท',
                f'5. ราคาขายแนะนำ (Food Cost {target_food_cost_percent}%): {suggested_price:.2f} บาท',
                f'6. กำไรจริง: {actual_profit:.2f} บาท ({actual_profit_percent:.1f}%)' if actual_selling_price > 0 else '6. ยังไม่มีราคาขายจริง'
            ]
        }
        )


class RecipeItemViewSet(viewsets.ModelViewSet):
    queryset = RecipeItem.objects.all()
    serializer_class = RecipeItemSerializer
    
    def get_queryset(self):
        recipe_id = self.request.query_params.get('recipe_id')
        if recipe_id:
            return RecipeItem.objects.filter(recipe_id=recipe_id)
        return RecipeItem.objects.all()


class MenuViewSet(viewsets.ModelViewSet):
    queryset = Menu.objects.all()
    serializer_class = MenuSerializer
    
    def get_queryset(self):
        branch_id = self.request.query_params.get('branch_id')
        if branch_id:
            return Menu.objects.filter(branch_id=branch_id)
        return Menu.objects.all()


class SaleViewSet(viewsets.ModelViewSet):
    queryset = Sale.objects.all()
    serializer_class = SaleSerializer
    
    def get_queryset(self):
        branch_id = self.request.query_params.get('branch_id')
        if branch_id:
            return Sale.objects.filter(branch_id=branch_id)
        return Sale.objects.all()
    
    @action(detail=False, methods=['get'])
    def daily_sales(self, request):
        from django.db.models import Sum
        from datetime import datetime, timedelta
        
        days = int(request.query_params.get('days', 30))
        start_date = datetime.now() - timedelta(days=days)
        
        sales = Sale.objects.filter(sale_date__gte=start_date).values('sale_date__date').annotate(total=Sum('total_price'))
        return Response(sales)


class SettingViewSet(viewsets.ModelViewSet):
    queryset = Setting.objects.all()
    serializer_class = SettingSerializer


# Template Views
class DashboardView(TemplateView):
    template_name = 'jaewhoncost/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from .models import Recipe, Menu, Ingredient, Purchase
        
        # ข้อมูลสำหรับ Dashboard
        recipes = Recipe.objects.all().prefetch_related('items__ingredient', 'menu_set')[:5]
        recent_sales = Sale.objects.all().select_related('menu')[:10]
        
        context['recent_recipes'] = recipes
        context['recent_sales'] = recent_sales
        context['total_recipes'] = Recipe.objects.count()
        context['total_menus'] = Menu.objects.count()
        context['total_ingredients'] = Ingredient.objects.count()
        context['total_sales'] = Sale.objects.count()
        context['total_purchases'] = Purchase.objects.count()
        
        return context


class IngredientsView(TemplateView):
    template_name = 'jaewhoncost/ingredients.html'


class RecipesView(TemplateView):
    template_name = 'jaewhoncost/recipes.html'


class MenusView(TemplateView):
    template_name = 'jaewhoncost/menus.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from .models import Menu
        # ดึง menus ทั้งหมดพร้อมข้อมูล branch และ recipe
        menus = Menu.objects.all().select_related('branch', 'recipe').order_by('id')
        context['menus'] = menus
        context['branches'] = Branch.objects.all()
        context['recipes'] = Recipe.objects.all().select_related('branch')
        return context


class PurchasesView(TemplateView):
    template_name = 'jaewhoncost/purchases.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['branches'] = Branch.objects.all()
        return context


class PriceHistoryReportView(TemplateView):
    template_name = 'jaewhoncost/price_history_report.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ingredients'] = Ingredient.objects.all().select_related('branch')
        return context


class SalesView(TemplateView):
    template_name = 'jaewhoncost/sales.html'


class BranchesView(TemplateView):
    template_name = 'jaewhoncost/branches.html'


class OwnersView(TemplateView):
    template_name = 'jaewhoncost/owners.html'


class SettingsView(TemplateView):
    template_name = 'jaewhoncost/settings.html'


class CostCalculationView(TemplateView):
    """หน้าคำนวณต้นทุนแบบเต็มรูปแบบพร้อมฟอร์ม"""
    template_name = 'jaewhoncost/cost_calculation.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = CostCalculationForm()
        return context


class CostCalculatorFormView(TemplateView):
    """หน้าฟอร์มหลักสำหรับคำนวณต้นทุนแบบ Real-time"""
    template_name = 'jaewhoncost/cost_calculator_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = CostCalculationForm()
        
        # ดึงข้อมูลสูตรทั้งหมดสำหรับแสดงในหน้า
        from .models import Recipe
        context['recipes'] = Recipe.objects.all().prefetch_related('items__ingredient', 'branch')
        
        return context


# ===== Purchase ViewSets =====
class PriceHistoryViewSet(viewsets.ModelViewSet):
    queryset = PriceHistory.objects.all().select_related('ingredient', 'purchase')
    serializer_class = PriceHistorySerializer
    
    def get_queryset(self):
        queryset = PriceHistory.objects.all().select_related('ingredient', 'purchase')
        ingredient_id = self.request.query_params.get('ingredient_id')
        if ingredient_id:
            queryset = queryset.filter(ingredient_id=ingredient_id)
        
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(effective_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(effective_date__lte=end_date)
        
        return queryset


class PurchaseViewSet(viewsets.ModelViewSet):
    queryset = Purchase.objects.all().prefetch_related('items__ingredient')
    serializer_class = PurchaseSerializer
    
    def get_queryset(self):
        queryset = Purchase.objects.all().prefetch_related('items__ingredient')
        branch_id = self.request.query_params.get('branch_id')
        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)
        return queryset
    
    @action(detail=False, methods=['get'])
    def report(self, request):
        """รายงานการจัดซื้อตามช่วงเวลา"""
        from django.db.models import Sum
        from datetime import datetime
        
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        queryset = self.get_queryset()
        if start_date:
            queryset = queryset.filter(purchase_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(purchase_date__lte=end_date)
        
        total_amount = queryset.aggregate(total=Sum('total_amount'))['total'] or 0
        
        return Response({
            'total_purchases': queryset.count(),
            'total_amount': total_amount,
            'purchases': PurchaseSerializer(queryset, many=True).data
        })


class PurchaseItemViewSet(viewsets.ModelViewSet):
    queryset = PurchaseItem.objects.all().select_related('purchase', 'ingredient')
    serializer_class = PurchaseItemSerializer
    
    def get_queryset(self):
        queryset = PurchaseItem.objects.all().select_related('purchase', 'ingredient')
        purchase_id = self.request.query_params.get('purchase_id')
        if purchase_id:
            queryset = queryset.filter(purchase_id=purchase_id)
        return queryset

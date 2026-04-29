from django.shortcuts import render
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.template.loader import render_to_string

# Create your views here.
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Owner, Branch, Ingredient, Recipe, RecipeItem, Menu, Sale, Setting
from .serializers import (
    OwnerSerializer, BranchSerializer, IngredientSerializer,
    RecipeSerializer, RecipeItemSerializer, MenuSerializer,
    SaleSerializer, SettingSerializer
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
    
    @action(detail=True, methods=['get'])
    def ingredients(self, request, pk=None):
        branch = self.get_object()
        ingredients = branch.ingredients.all()
        serializer = IngredientSerializer(ingredients, many=True)
        return Response(serializer.data)


class IngredientViewSet(viewsets.ModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    
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
        """API endpoint สำหรับคำนวณต้นทุนแบบ real-time"""
        recipe = self.get_object()
        data = request.data
        
        # รับพารามิเตอร์จาก request
        waste_percent = float(data.get('waste_percent', 5.0))
        target_food_cost_percent = float(data.get('target_food_cost_percent', 30.0))
        
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
            price_per_unit = float(item.ingredient.price)
            item_cost = quantity * price_per_unit
            total_ingredient_cost += item_cost
            
            items_detail.append({
                'ingredient_name': item.ingredient.name,
                'quantity': float(item.quantity),
                'unit': item.ingredient.unit,
                'price_per_unit': float(item.ingredient.price),
                'cost': item_cost,
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
            actual_profit = 0
            actual_profit_percent = 0
            actual_food_cost_percent = 0
        
        return Response({
            'recipe_name': recipe.name,
            'branch_name': recipe.branch.name,
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
                f'1. รวมต้นทุนวัตถุดิบ: {total_ingredient_cost:.2f} บาท',
                f'2. Waste {waste_percent}%: {total_ingredient_cost:.2f} ÷ (1 - {waste_factor}) = {effective_cost:.2f} บาท',
                f'3. Overhead: {total_overhead:.2f} บาท',
                f'4. ต้นทุนรวม: {total_cost_with_overhead:.2f} บาท',
                f'5. ราคาขายแนะนำ (Food Cost {target_food_cost_percent}%): {suggested_price:.2f} บาท',
                f'6. กำไรจริง: {actual_profit:.2f} บาท ({actual_profit_percent:.1f}%)' if actual_selling_price > 0 else '6. ยังไม่มีราคาขายจริง'
            ]
        })


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
        from .models import Recipe, Menu
        
        # ข้อมูลสำหรับ Dashboard
        recipes = Recipe.objects.all().prefetch_related('items__ingredient', 'menu_set')[:5]
        recent_sales = Sale.objects.all().select_related('menu')[:10]
        
        context['recent_recipes'] = recipes
        context['recent_sales'] = recent_sales
        context['total_recipes'] = Recipe.objects.count()
        context['total_sales'] = Sale.objects.count()
        
        return context


class IngredientsView(TemplateView):
    template_name = 'jaewhoncost/ingredients.html'


class RecipesView(TemplateView):
    template_name = 'jaewhoncost/recipes.html'


class MenusView(TemplateView):
    template_name = 'jaewhoncost/menus.html'


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

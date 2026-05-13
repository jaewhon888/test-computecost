from django.shortcuts import render
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.template.loader import render_to_string

# Create your views here.
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
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
    
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Return stats for a branch: recipes, menus, ingredients, sales, purchases"""
        from django.db.models import Count, Sum, Avg
        branch = self.get_object()
        
        total_ingredients = branch.ingredients.count()
        total_recipes = branch.recipes.count()
        total_menus = branch.menus.count()
        total_sales = branch.sales.count()
        total_purchases = branch.purchases.count()
        
        total_revenue = sum((s.total_price or 0) for s in branch.sales.all())
        total_cost = sum((p.total_amount or 0) for p in branch.purchases.all())
        profit = total_revenue - total_cost
        
        # Stock summary
        total_stock_value = sum(
            (i.price * i.stock) for i in branch.ingredients.all()
        )
        low_stock = branch.ingredients.filter(stock__lte=5, stock__gt=0).count()
        out_of_stock = branch.ingredients.filter(stock=0).count()
        
        # Top selling menu
        top_menu = branch.sales.values('menu__name').annotate(
            qty=Count('id'), revenue=Sum('total_price')
        ).order_by('-qty')[:1].first()
        
        return Response({
            'branch_name': branch.name,
            'owner_name': branch.owner.name,
            'total_ingredients': total_ingredients,
            'total_recipes': total_recipes,
            'total_menus': total_menus,
            'total_sales': total_sales,
            'total_purchases': total_purchases,
            'total_revenue': float(total_revenue),
            'total_cost': float(total_cost),
            'profit': float(profit),
            'total_stock_value': float(total_stock_value),
            'low_stock_count': low_stock,
            'out_of_stock_count': out_of_stock,
            'top_menu': top_menu['menu__name'] if top_menu else None,
            'top_menu_qty': top_menu['qty'] if top_menu else 0,
        })


class IngredientViewSet(viewsets.ModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None


class OwnerViewSet(viewsets.ModelViewSet):
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    queryset = Owner.objects.all()
    serializer_class = OwnerSerializer
    
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Return stats for an owner: branches, total sales, revenue, etc."""
        from django.db.models import Count, Sum
        owner = self.get_object()
        
        total_branches = owner.branches.count()
        
        total_ingredients = sum(b.ingredients.count() for b in owner.branches.all())
        total_recipes = sum(b.recipes.count() for b in owner.branches.all())
        total_menus = sum(b.menus.count() for b in owner.branches.all())
        
        total_sales = 0
        total_revenue = 0
        for b in owner.branches.all():
            total_sales += b.sales.count()
            total_revenue += sum((s.total_price or 0) for s in b.sales.all())
        
        total_cost = sum(
            (p.total_amount or 0) for b in owner.branches.all()
            for p in b.purchases.all()
        )
        profit = total_revenue - total_cost
        
        # Branch breakdown
        branches_summary = []
        for b in owner.branches.all():
            b_revenue = sum((s.total_price or 0) for s in b.sales.all())
            b_cost = sum((p.total_amount or 0) for p in b.purchases.all())
            branches_summary.append({
                'id': b.id,
                'name': b.name,
                'address': b.address,
                'phone': b.phone,
                'total_recipes': b.recipes.count(),
                'total_menus': b.menus.count(),
                'total_ingredients': b.ingredients.count(),
                'total_sales': b.sales.count(),
                'revenue': float(b_revenue),
                'cost': float(b_cost),
                'profit': float(b_revenue - b_cost),
            })
        
        return Response({
            'owner_name': owner.name,
            'email': owner.email,
            'phone': owner.phone,
            'total_branches': total_branches,
            'total_ingredients': total_ingredients,
            'total_recipes': total_recipes,
            'total_menus': total_menus,
            'total_sales': total_sales,
            'total_revenue': float(total_revenue),
            'total_cost': float(total_cost),
            'profit': float(profit),
            'branches': branches_summary,
        })
    
    def get_queryset(self):
        """Return Owner queryset, optionally filtered by branch_id"""
        return Owner.objects.all()


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    
    def get_queryset(self):
        branch_id = self.request.query_params.get('branch_id')
        if branch_id:
            return Recipe.objects.filter(branch_id=branch_id)
        return Recipe.objects.all()
    
    def perform_create(self, serializer):
        # ดึง items ออกจาก request data ก่อน serializer ตรวจสอบ
        items_data = self.request.data.pop('items', [])
        recipe = serializer.save()
        # สร้าง items ใหม่
        if items_data:
            for item_data in items_data:
                RecipeItem.objects.create(
                    recipe=recipe,
                    ingredient_id=item_data.get('ingredient'),
                    quantity=item_data.get('quantity', 0)
                )
    
    def perform_update(self, serializer):
        # ดึง items ออกจาก request data ก่อน serializer ตรวจสอบ
        items_data = self.request.data.pop('items', None)
        recipe = serializer.save()
        # อัปเดต items
        if items_data is not None:  # None หมายถึงไม่ไดส่ง items มา
            # ลบ items เก่า
            recipe.items.all().delete()
            # สร้าง items ใหม่
            for item_data in items_data:
                RecipeItem.objects.create(
                    recipe=recipe,
                    ingredient_id=item_data.get('ingredient'),
                    quantity=item_data.get('quantity', 0)
                )
    
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
        
        # ดึง overhead costs จาก Setting model (ตามสาขาของสูตร)
        try:
            branch_setting = Setting.objects.get(branch=recipe.branch)
            overhead_costs = {
                'utilities': float(data.get('overhead_utilities', branch_setting.overhead_utilities)),
                'labor': float(data.get('overhead_labor', branch_setting.overhead_labor)),
                'rent': float(data.get('overhead_rent', branch_setting.overhead_rent)),
                'depreciation': float(data.get('overhead_depreciation', branch_setting.overhead_depreciation)),
                'marketing': float(data.get('overhead_marketing', branch_setting.overhead_marketing)),
                'delivery': float(data.get('overhead_delivery', branch_setting.overhead_delivery)),
            }
        except Setting.DoesNotExist:
            # ถ้าไม่มี Setting ใชค่า default (กรณีสร้าง Setting ไม่สำเร็จ)
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
    
    @action(detail=True, methods=['post'])
    def calculate_cost(self, request, pk=None):
        """คำนวณต้นทุนของเมนู (ใช้ recipe ที่ผูกอยู่)"""
        menu = self.get_object()
        
        if not menu.recipe:
            return Response({'error': 'เมนูนี้ไม่ได้ผูกกับสูตรอาหาร'}, status=400)
        
        # เรียกใช้ calculate_cost ของ recipe viewset โดยตรง
        recipe_viewset = RecipeViewSet()
        recipe_viewset.request = request
        recipe_viewset.format_kwarg = None
        recipe_viewset.kwargs = {'pk': menu.recipe.id}
        
        # เพิ่ม actual_selling_price จากราคาเมนูใน request data
        request.data['actual_selling_price'] = float(menu.price)
        
        response = recipe_viewset.calculate_cost(request, pk=menu.recipe.id)
        
        # เพิ่มข้อมูลเมนูในผลลัพธ์
        if response.status_code == 200:
            result = response.data
            result['menu_name'] = menu.name
            result['menu_price'] = float(menu.price)
            result['menu_id'] = menu.id
            result['branch_name'] = menu.branch.name
            return Response(result)
        
        return response
    
    @action(detail=False, methods=['post'])
    def calculate_all(self, request):
        """คำนวณต้นทุนเมนูทั้งหมด"""
        branch_id = request.query_params.get('branch_id')
        
        if branch_id:
            menus = Menu.objects.filter(branch_id=branch_id).select_related('recipe', 'branch')
        else:
            menus = Menu.objects.all().select_related('recipe', 'branch')
        
        results = []
        for menu in menus:
            if not menu.recipe:
                results.append({
                    'menu_id': menu.id,
                    'menu_name': menu.name,
                    'branch_name': menu.branch.name,
                    'error': 'ไม่มีสูตรอาหารผูกอยู่'
                })
                continue
            
            # เรียกใช้ calculate_cost
            recipe_viewset = RecipeViewSet()
            recipe_viewset.request = request
            recipe_viewset.format_kwarg = None
            recipe_viewset.kwargs = {'pk': menu.recipe.id}
            
            # ตั้งค่า actual_selling_price
            request.data['actual_selling_price'] = float(menu.price)
            
            response = recipe_viewset.calculate_cost(request, pk=menu.recipe.id)
            
            if response.status_code == 200:
                result = response.data
                result['menu_id'] = menu.id
                result['menu_name'] = menu.name
                result['menu_price'] = float(menu.price)
                result['branch_name'] = menu.branch.name
                results.append(result)
            else:
                results.append({
                    'menu_id': menu.id,
                    'menu_name': menu.name,
                    'branch_name': menu.branch.name,
                    'error': 'เกิดข้อผิดพลาดในการคำนวณ'
                })
        
        return Response({
            'total_menus': len(results),
            'results': results
        })


class SaleViewSet(viewsets.ModelViewSet):
    queryset = Sale.objects.all()
    serializer_class = SaleSerializer
    
    def get_queryset(self):
        queryset = Sale.objects.all()
        branch_id = self.request.query_params.get('branch_id')
        date_start = self.request.query_params.get('date_start')
        date_end = self.request.query_params.get('date_end')
        payment_method = self.request.query_params.get('payment_method')
        search = self.request.query_params.get('search')
        
        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)
        if date_start:
            queryset = queryset.filter(sale_date__gte=date_start)
        if date_end:
            queryset = queryset.filter(sale_date__lte=date_end)
        if payment_method:
            queryset = queryset.filter(payment_method=payment_method)
        if search:
            queryset = queryset.filter(menu__name__icontains=search)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def daily_sales(self, request):
        from django.db.models import Sum
        from datetime import datetime, timedelta
        
        days = int(request.query_params.get('days', 30))
        start_date = datetime.now() - timedelta(days=days)
        
        sales = Sale.objects.filter(sale_date__gte=start_date).values('sale_date__date').annotate(total=Sum('total_price'))
        return Response(sales)
    
    @action(detail=False, methods=['get'])
    def top_selling(self, request):
        """รายงานเมนูขายดี — เรียงตามจำนวนที่ขายได้มากสุด"""
        from django.db.models import Sum, Count
        from datetime import datetime, timedelta
        
        days = int(request.query_params.get('days', 30))
        branch_id = request.query_params.get('branch_id')
        limit = int(request.query_params.get('limit', 10))
        
        start_date = datetime.now() - timedelta(days=days)
        queryset = Sale.objects.filter(sale_date__gte=start_date)
        
        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)
        
        top_menus = (
            queryset
            .values('menu__id', 'menu__name', 'menu__price')
            .annotate(
                total_quantity=Sum('quantity'),
                total_revenue=Sum('total_price'),
                transaction_count=Count('id'),
            )
            .order_by('-total_quantity')[:limit]
        )
        
        return Response(list(top_menus))
    
    @action(detail=False, methods=['get'])
    def compare_periods(self, request):
        """เปรียบเทียบยอดขายระหว่างสองช่วงเวลา"""
        from django.db.models import Sum, Count
        from datetime import datetime
        
        # ช่วงเวลาปัจจุบัน
        cur_start = request.query_params.get('cur_start')
        cur_end = request.query_params.get('cur_end')
        # ช่วงเวลาเปรียบเทียบ
        prev_start = request.query_params.get('prev_start')
        prev_end = request.query_params.get('prev_end')
        branch_id = request.query_params.get('branch_id')
        
        def _aggregate(start, end, branch_id):
            qs = Sale.objects.all()
            if start:
                qs = qs.filter(sale_date__gte=start)
            if end:
                qs = qs.filter(sale_date__lte=end)
            if branch_id:
                qs = qs.filter(branch_id=branch_id)
            result = qs.aggregate(
                total_revenue=Sum('total_price'),
                total_transactions=Count('id'),
                total_quantity=Sum('quantity'),
            )
            result['total_revenue'] = float(result['total_revenue'] or 0)
            result['total_transactions'] = result['total_transactions'] or 0
            result['total_quantity'] = float(result['total_quantity'] or 0)
            result['avg_transaction'] = result['total_revenue'] / result['total_transactions'] if result['total_transactions'] else 0
            return result
        
        current = _aggregate(cur_start, cur_end, branch_id)
        previous = _aggregate(prev_start, prev_end, branch_id)
        
        def _change(cur, prev):
            if not prev:
                return 100.0 if cur else 0.0
            return round(((cur - prev) / prev) * 100, 1)
        
        return Response({
            'current': current,
            'previous': previous,
            'changes': {
                'revenue_change_pct': _change(current['total_revenue'], previous['total_revenue']),
                'transactions_change_pct': _change(current['total_transactions'], previous['total_transactions']),
                'quantity_change_pct': _change(current['total_quantity'], previous['total_quantity']),
                'avg_transaction_change_pct': _change(current['avg_transaction'], previous['avg_transaction']),
            }
        })
    
    @action(detail=False, methods=['get'])
    def payment_summary(self, request):
        """สรุปยอดขายแยกตามวิธีชำระเงิน"""
        from django.db.models import Sum, Count
        from datetime import datetime, timedelta
        
        days = int(request.query_params.get('days', 30))
        branch_id = request.query_params.get('branch_id')
        
        start_date = datetime.now() - timedelta(days=days)
        queryset = Sale.objects.filter(sale_date__gte=start_date)
        
        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)
        
        summary = (
            queryset
            .values('payment_method')
            .annotate(
                total_revenue=Sum('total_price'),
                transaction_count=Count('id'),
            )
            .order_by('-total_revenue')
        )
        
        # เพิ่ม display name
        payment_map = dict(Sale.PAYMENT_METHOD_CHOICES)
        for item in summary:
            item['payment_method_display'] = payment_map.get(item['payment_method'], item['payment_method'])
            item['total_revenue'] = float(item['total_revenue'] or 0)
        
        return Response(list(summary))
    
    @action(detail=False, methods=['get'])
    def by_weekday(self, request):
        """สรุปยอดขายแยกตามวันในสัปดาห์"""
        from django.db.models import Sum, Count
        from datetime import datetime, timedelta
        
        days = int(request.query_params.get('days', 30))
        branch_id = request.query_params.get('branch_id')
        
        start_date = datetime.now() - timedelta(days=days)
        queryset = Sale.objects.filter(sale_date__gte=start_date)
        
        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)
        
        # ใช้ raw SQL เพื่อ group by day of week
        from django.db.models.functions import ExtractWeekDay
        from django.db.models import F
        
        result = (
            queryset
            .annotate(day_of_week=ExtractWeekDay('sale_date'))
            .values('day_of_week')
            .annotate(
                total_revenue=Sum('total_price'),
                transaction_count=Count('id'),
            )
            .order_by('day_of_week')
        )
        
        weekday_names = {
            1: 'อาทิตย์', 2: 'จันทร์', 3: 'อังคาร', 4: 'พุธ',
            5: 'พฤหัส', 6: 'ศุกร์', 7: 'เสาร์'
        }
        
        for item in result:
            item['day_name'] = weekday_names.get(item['day_of_week'], 'ไม่ทราบ')
            item['total_revenue'] = float(item['total_revenue'] or 0)
        
        return Response(list(result))
    
    @action(detail=False, methods=['get'])
    def export_csv(self, request):
        """Export รายการขายเป็น CSV"""
        import csv
        from django.http import HttpResponse
        from datetime import datetime, timedelta
        
        days = int(request.query_params.get('days', 30))
        branch_id = request.query_params.get('branch_id')
        
        start_date = datetime.now() - timedelta(days=days)
        queryset = Sale.objects.filter(sale_date__gte=start_date).select_related('branch', 'menu')
        
        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)
        
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = f'attachment; filename="sales_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['ID', 'สาขา', 'เมนู', 'จำนวน', 'ราคารวม', 'วิธีชำระ', 'วันที่ขาย', 'หมายเหตุ'])
        
        for sale in queryset:
            writer.writerow([
                sale.id,
                sale.branch.name,
                sale.menu.name,
                sale.quantity,
                sale.total_price,
                sale.get_payment_method_display(),
                sale.sale_date.strftime('%d/%m/%Y %H:%M'),
                sale.note or '',
            ])
        
        return response



    @action(detail=False, methods=['get'])
    def profit_report(self, request):
        """รายงานกำไรขั้นต้น - เปรียบเทียบต้นทุนกับราคาขายจริง"""
        from django.db.models import Sum, Count
        from datetime import datetime, timedelta
        
        # Get query parameters
        days = int(request.query_params.get('days', 30))
        branch_id = request.query_params.get('branch_id')
        date_start = request.query_params.get('date_start')
        date_end = request.query_params.get('date_end')
        
        # Build queryset for sales
        queryset = Sale.objects.all().select_related('menu__recipe__branch', 'menu')
        
        if date_start:
            queryset = queryset.filter(sale_date__gte=date_start)
        if date_end:
            queryset = queryset.filter(sale_date__lte=date_end)
        elif days:
            start_date = datetime.now() - timedelta(days=days)
            queryset = queryset.filter(sale_date__gte=start_date)
            
        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)
        
        # Group by menu for detailed report
        menu_stats = queryset.values(
            'menu__id', 
            'menu__name', 
            'menu__price',
            'menu__recipe__id',
            'menu__recipe__name',
            'menu__recipe__branch__name',
            'menu__recipe__branch__id'
        ).annotate(
            total_quantity=Sum('quantity'),
            total_revenue=Sum('total_price'),
            transaction_count=Count('id')
        ).order_by('-total_revenue')
        
        # Process each menu to calculate profit
        results = []
        for stat in menu_stats:
            menu_id = stat['menu__id']
            if not menu_id:
                continue
                
            try:
                from .models import Menu
                menu = Menu.objects.get(id=menu_id)
                
                # Calculate cost for this menu using existing endpoint logic
                # We'll reuse the menu's calculate_cost method
                from .views import MenuViewSet
                menu_viewset = MenuViewSet()
                menu_viewset.request = request
                
                # Get sales data for this specific menu to calculate totals
                menu_sales = queryset.filter(menu_id=menu_id)
                total_quantity = menu_sales.aggregate(Sum('quantity'))['quantity__sum'] or 0
                total_revenue = menu_sales.aggregate(Sum('total_price'))['total_price__sum'] or 0
                transaction_count = menu_sales.count()
                
                if total_quantity == 0:
                    continue
                    
                # Calculate cost per unit using the menu's calculate_cost
                # We need to create a mock request with the menu's data
                mock_request = type('obj', (object,), {
                    'method': 'POST',
                    'data': {},
                    'query_params': request.query_params
                })()
                
                # Set up the viewset for detail calculation
                detail_viewset = MenuViewSet()
                detail_viewset.request = mock_request
                detail_viewset.kwargs = {'pk': menu_id}
                
                # Try to get the cost calculation
                try:
                    cost_response = detail_viewset.calculate_cost(mock_request, pk=menu_id)
                    if cost_response.status_code == 200:
                        cost_data = cost_response.data
                        cost_per_unit = cost_data.get('total_cost_with_overhead', 0)
                        suggested_price = cost_data.get('suggested_price', 0)
                        actual_price = float(menu.price) if menu.price else 0
                        
                        # Calculate profit
                        cost_total = cost_per_unit * total_quantity
                        profit = total_revenue - cost_total
                        profit_margin = (profit / total_revenue * 100) if total_revenue > 0 else 0
                        
                        results.append({
                            'menu_id': menu_id,
                            'menu_name': stat['menu__name'],
                            'branch_name': stat['menu__recipe__branch__name'],
                            'recipe_name': stat['menu__recipe__name'],
                            'total_quantity': total_quantity,
                            'total_revenue': float(total_revenue),
                            'total_cost': float(cost_total),
                            'total_profit': float(profit),
                            'profit_margin': float(profit_margin),
                            'actual_price': actual_price,
                            'suggested_price': suggested_price,
                            'transaction_count': transaction_count,
                            'cost_per_unit': cost_per_unit,
                            'price_per_unit': actual_price / total_quantity if total_quantity > 0 else 0
                        })
                except Exception as e:
                    # If cost calculation fails, show basic info without profit
                    results.append({
                        'menu_id': menu_id,
                        'menu_name': stat['menu__name'],
                        'branch_name': stat['menu__recipe__branch__name'],
                        'recipe_name': stat['menu__recipe__name'],
                        'total_quantity': total_quantity,
                        'total_revenue': float(total_revenue),
                        'total_cost': 0,
                        'total_profit': 0,
                        'profit_margin': 0,
                        'actual_price': float(menu.price) if menu.price else 0,
                        'suggested_price': 0,
                        'transaction_count': transaction_count,
                        'cost_per_unit': 0,
                        'price_per_unit': 0,
                        'error': f'Could not calculate cost: {str(e)}'
                    })
                    
            except Menu.DoesNotExist:
                continue
        
        # Summary totals
        total_revenue = sum(r['total_revenue'] for r in results)
        total_cost = sum(r['total_cost'] for r in results)
        total_profit = sum(r['total_profit'] for r in results)
        overall_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
        
        return Response({
            'summary': {
                'total_revenue': float(total_revenue),
                'total_cost': float(total_cost),
                'total_profit': float(total_profit),
                'profit_margin': float(overall_margin),
                'total_transactions': sum(r['transaction_count'] for r in results),
                'total_menus_sold': len(results)
            },
            'details': results,
            'filters': {
                'branch_id': branch_id,
                'date_start': date_start,
                'date_end': date_end,
                'days': days
            }
        })

class SettingViewSet(viewsets.ModelViewSet):
    queryset = Setting.objects.all()
    serializer_class = SettingSerializer


# Template Views
class DashboardView(TemplateView):
    template_name = 'jaewhoncost/dashboard.html'
    
    def get_context_data(self, **kwargs):
        from decimal import Decimal
        from datetime import timedelta
        from django.utils import timezone
        
        context = super().get_context_data(**kwargs)
        from .models import Recipe, Menu, Ingredient, Purchase, Sale, Branch
        
        # ข้อมูลสำหรับ Dashboard
        recipes = Recipe.objects.all().prefetch_related('items__ingredient', 'menu_set')[:5]
        recent_sales = Sale.objects.all().select_related('menu')[:10]
        recent_purchases = Purchase.objects.all().select_related('branch')[:5]
        
        # ยอดรวม
        total_recipes = Recipe.objects.count()
        total_menus = Menu.objects.count()
        total_ingredients = Ingredient.objects.count()
        total_sales_count = Sale.objects.count()
        total_purchases = Purchase.objects.count()
        
        # คำนวณรายรับรวมจาก sales
        total_revenue = sum(
            (s.total_price or 0) for s in Sale.objects.all()
        )
        
        # คำนวณต้นทุนรวมจาก purchases
        total_cost = sum(
            (p.total_amount or 0) for p in Purchase.objects.all()
        )
        
        # กำไร = รายได้ - ต้นทุน
        total_profit = total_revenue - total_cost
        
        # ยอดขายเดือนนี้
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_sales = Sale.objects.filter(sale_date__gte=month_start)
        monthly_revenue = sum((s.total_price or 0) for s in month_sales)
        month_purchases = Purchase.objects.filter(purchase_date__gte=month_start)
        monthly_cost = sum((p.total_amount or 0) for p in month_purchases)
        monthly_profit = monthly_revenue - monthly_cost
        
        # เมนูขายดี (top 5)
        from django.db.models import Count, Sum
        top_menus = Sale.objects.values('menu__name').annotate(
            qty=Count('id'),
            revenue=Sum('total_price')
        ).order_by('-qty')[:5]
        
        # จำนวน branches
        total_branches = Branch.objects.count()
        
        context['recent_recipes'] = recipes
        context['recent_sales'] = recent_sales
        context['recent_purchases'] = recent_purchases
        context['total_recipes'] = total_recipes
        context['total_menus'] = total_menus
        context['total_ingredients'] = total_ingredients
        context['total_sales'] = total_sales_count
        context['total_purchases'] = total_purchases
        context['total_branches'] = total_branches
        context['total_revenue'] = total_revenue
        context['total_cost'] = total_cost
        context['total_profit'] = total_profit
        context['monthly_revenue'] = monthly_revenue
        context['monthly_cost'] = monthly_cost
        context['monthly_profit'] = monthly_profit
        context['top_menus'] = top_menus
        
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
    """หน้าคำนวณต้นทุนแบบเต็มรูปแบบ (SPA) — use cost_calculator_form.html"""
    template_name = 'jaewhoncost/cost_calculator_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class CostCalculatorFormView(TemplateView):
    """Deprecated: redirects to CostCalculationView"""
    template_name = 'jaewhoncost/cost_calculator_form.html'


class ImportDataView(TemplateView):
    template_name = 'jaewhoncost/import_data.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['branches'] = Branch.objects.all()
        from datetime import date
        context['today'] = date.today()
        return context

    def post(self, request, *args, **kwargs):
        import tempfile
        import os
        import csv
        from decimal import Decimal, InvalidOperation
        from django.contrib import messages

        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            if self.request.content_type and 'json' in self.request.content_type:
                from django.http import JsonResponse
                return JsonResponse({'error': 'กรุณาเลือกไฟล์'}, status=400)
            messages.error(request, 'กรุณาเลือกไฟล์')
            return self.get(request, *args, **kwargs)

        mode = request.POST.get('mode', 'import_only')
        branch_id = request.POST.get('branch')
        delimiter = request.POST.get('delimiter', ',')
        is_api = 'application/json' in request.content_type if request.content_type else False

        # Read CSV content
        try:
            content = uploaded_file.read().decode('utf-8-sig')  # handles BOM
        except UnicodeDecodeError:
            content = uploaded_file.read().decode('cp874')  # Windows Thai

        lines = content.strip().split('\n')
        if len(lines) < 2:
            if is_api:
                from django.http import JsonResponse
                return JsonResponse({'error': 'ไฟล์ไม่มีข้อมูล'}, status=400)
            messages.error(request, 'ไฟล์ไม่มีข้อมูล')
            return self.get(request, *args, **kwargs)

        # Parse header + data rows
        delimiter_map = {'comma': ',', 'semicolon': ';', 'tab': '\t', 'pipe': '|'}
        delim = delimiter_map.get(delimiter, delimiter)

        reader = csv.DictReader(lines, delimiter=delim)
        rows = list(reader)

        created = 0
        updated = 0
        errors = []

        if mode in ('inventory', 'import_only') and mode != 'purchase':
            # For inventory mode: update ingredient stock or create ingredients
            for i, row in enumerate(rows):
                try:
                    name = row.get('name', '').strip()
                    if not name:
                        errors.append(f'แถว {i+2}: ไม่มีชื่อวัตถุดิบ')
                        continue
                    price = float(row.get('price', 0))
                    unit = row.get('unit', 'g').strip()
                    stock = int(float(row.get('stock', 0)))
                    branch_name = row.get('branch', '').strip()

                    if not branch_id:
                        errors.append(f'แถว {i+2}: ไม่ระบุสาขา')
                        continue

                    ingredient, _c = Ingredient.objects.get_or_create(
                        branch_id=branch_id,
                        name=name,
                        defaults={'price': price, 'unit': unit, 'stock': stock}
                    )
                    if _c:
                        created += 1
                    else:
                        ingredient.stock = stock
                        ingredient.price = price
                        ingredient.unit = unit
                        ingredient.save()
                        updated += 1
                except (ValueError, Exception) as e:
                    errors.append(f'แถว {i+2}: {e}')

        elif mode == 'purchase':
            # For purchase mode: create Purchase + PurchaseItems
            supplier = request.POST.get('supplier', '')
            invoice = request.POST.get('invoice', '')

            if not branch_id:
                if is_api:
                    from django.http import JsonResponse
                    return JsonResponse({'error': 'กรุณาเลือกสาขา'}, status=400)
                messages.error(request, 'กรุณาเลือกสาขา')
                return self.get(request, *args, **kwargs)

            branch = Branch.objects.get(id=branch_id)
            purchase = Purchase.objects.create(
                branch=branch,
                supplier_name=supplier,
                invoice_number=invoice
            )

            for i, row in enumerate(rows):
                try:
                    name = row.get('name', '').strip()
                    if not name:
                        errors.append(f'แถว {i+2}: ไม่มีชื่อวัตถุดิบ')
                        continue
                    quantity = float(row.get('quantity', row.get('stock', 0)))
                    unit_price = float(row.get('unit_price', row.get('price', 0)))
                    unit = row.get('unit', 'g').strip()

                    ingredient, _c = Ingredient.objects.get_or_create(
                        branch=branch,
                        name=name,
                        defaults={'price': unit_price, 'unit': unit, 'stock': 0}
                    )

                    # Create PurchaseItem which auto-updates stock and creates PriceHistory
                    PurchaseItem.objects.create(
                        purchase=purchase,
                        ingredient=ingredient,
                        quantity=quantity,
                        unit_price=unit_price
                    )
                    created += 1
                except Exception as e:
                    errors.append(f'แถว {i+2}: {e}')

        result = {'created': created, 'updated': updated, 'errors': errors[:20]}

        if is_api:
            from django.http import JsonResponse
            return JsonResponse(result)

        if errors:
            messages.error(request, f'นำเข้าสำเร็จ: สร้าง {created}, อัปเดต {updated}, แต่มี error {len(errors)} รายการ')
        else:
            messages.success(request, f'นำเข้าสำเร็จ! สร้าง {created} รายการ, อัปเดต {updated} รายการ')
        return redirect('import_data')


class ReportsView(TemplateView):
    template_name = 'jaewhoncost/reports.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['branches'] = Branch.objects.all()
        return context

    def post(self, request, *args, **kwargs):
        import csv
        import io
        from django.http import HttpResponse, JsonResponse
        from datetime import datetime

        report_type = request.POST.get('report_type')
        branch_id = request.POST.get('branch_id', '')
        date_start = request.POST.get('date_start', '')
        date_end = request.POST.get('date_end', '')
        export_format = request.POST.get('export_format', 'html')  # html, csv, excel

        # Build queryset based on report type
        if report_type == 'sales':
            qs = Sale.objects.all().select_related('menu', 'branch')
            if branch_id:
                qs = qs.filter(branch_id=branch_id)
            if date_start:
                qs = qs.filter(sale_date__gte=date_start)
            if date_end:
                qs = qs.filter(sale_date__lte=date_end)

            headers = ['วันที่', 'เมนู', 'สาขา', 'จำนวน', 'ราคาต่อหน่วย', 'รวม', 'วิธีชำระเงิน']
            rows = []
            for s in qs:
                rows.append([
                    s.sale_date.strftime('%Y-%m-%d %H:%M'),
                    s.menu.name,
                    s.branch.name,
                    s.quantity,
                    float(s.menu.price),
                    float(s.total_price),
                    s.get_payment_method_display() or s.payment_method,
                ])
            title = 'รายงานยอดขาย'

        elif report_type == 'revenue_by_branch':
            from django.db.models import Count, Sum
            qs = Branch.objects.all()
            headers = ['สาขา', 'ยอดขายรวม', 'จำนวนรายการ', 'ต้นทุนรวม', 'กำไร']
            rows = []
            for b in qs:
                total_rev = sum(s.total_price for s in b.sales.all())
                total_cost = sum(p.total_amount for p in b.purchases.all())
                rows.append([
                    b.name,
                    float(total_rev),
                    b.sales.count(),
                    float(total_cost),
                    float(total_rev - total_cost),
                ])
            title = 'รายงานรายได้แยกตามสาขา'

        elif report_type == 'inventory':
            qs = Ingredient.objects.all().select_related('branch')
            if branch_id:
                qs = qs.filter(branch_id=branch_id)
            headers = ['วัตถุดิบ', 'สาขา', 'ราคา/หน่วย', 'คงเหลือ', 'มูลค่ารวม', 'หน่วย', 'อัปเดตล่าสุด']
            rows = []
            for i in qs:
                rows.append([
                    i.name,
                    i.branch.name,
                    float(i.price),
                    i.stock,
                    float(i.price * i.stock),
                    dict(Ingredient.UNIT_CHOICES).get(i.unit, i.unit),
                    i.updated_at.strftime('%Y-%m-%d') if i.updated_at else '-',
                ])
            title = 'รายงานสต็อกวัตถุดิบ'

        elif report_type == 'purchases':
            qs = Purchase.objects.all().select_related('branch')
            if branch_id:
                qs = qs.filter(branch_id=branch_id)
            if date_start:
                qs = qs.filter(purchase_date__gte=date_start)
            if date_end:
                qs = qs.filter(purchase_date__lte=date_end)
            headers = ['วันที่', 'สาขา', 'ผู้จัดจำหน่าย', 'เลขที่ใบแจ้งหนี้', 'ยอดรวม', 'สถานะ', 'หมายเหตุ']
            rows = []
            for p in qs:
                rows.append([
                    p.purchase_date.strftime('%Y-%m-%d %H:%M'),
                    p.branch.name,
                    p.supplier_name or '-',
                    p.invoice_number or '-',
                    float(p.total_amount),
                    p.get_payment_status_display(),
                    p.note or '-',
                ])
            title = 'รายงานการจัดซื้อ'

        elif report_type == 'price_history':
            qs = PriceHistory.objects.all().select_related('ingredient')
            headers = ['วันที่', 'วัตถุดิบ', 'ราคา', 'ปริมาณ', 'หมายเหตุ']
            rows = []
            for ph in qs[:200]:  # limit to avoid huge output
                rows.append([
                    ph.effective_date.strftime('%Y-%m-%d %H:%M'),
                    ph.ingredient.name,
                    float(ph.price),
                    float(ph.quantity_purchased or 0),
                    ph.note or '-',
                ])
            title = 'รายงานประวัติราคา'

        elif report_type == 'menu_cost':
            qs = Menu.objects.all().select_related('recipe', 'branch')
            if branch_id:
                qs = qs.filter(branch_id=branch_id)
            headers = ['เมนู', 'สาขา', 'ราคาขาย', 'ต้นทุนวัตถุดิบ', 'Food Cost %', 'กำไรต่อรายการ']
            rows = []
            for m in qs:
                cost = 0
                if m.recipe:
                    cost = sum(item.quantity * item.ingredient.price for item in m.recipe.items.all())
                fcp = (cost / float(m.price) * 100) if float(m.price) > 0 else 0
                rows.append([
                    m.name,
                    m.branch.name,
                    float(m.price),
                    cost,
                    round(fcp, 1),
                    float(m.price) - cost,
                ])
            title = 'รายงานต้นทุนเมนู'

        else:
            return JsonResponse({'error': 'Invalid report type'}, status=400)

        if export_format == 'csv':
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(['\ufeff' + title])  # BOM for UTF-8
            writer.writerow(headers)
            for row in rows:
                writer.writerow(row)
            resp = HttpResponse(output.getvalue(), content_type='text/csv; charset=utf-8')
            resp['Content-Disposition'] = f'attachment; filename="report_{report_type}.csv"'
            return resp

        # HTML render
        return self.render_to_response({
            'title': title,
            'headers': headers,
            'rows': rows,
            'branches': Branch.objects.all(),
        })


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

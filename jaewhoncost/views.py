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

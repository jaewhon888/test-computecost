from django import forms
from .models import Recipe, Branch
from decimal import Decimal

class CostCalculationForm(forms.Form):
    """ฟอร์มสำหรับคำนวณต้นทุนตามมาตรฐานสากล"""
    
    # เลือกสูตรอาหาร
    recipe = forms.ModelChoiceField(
        queryset=Recipe.objects.all().prefetch_related('items__ingredient', 'branch'),
        label='เลือกสูตรอาหาร',
        widget=forms.Select(attrs={
            'class': 'form-control',
            'onchange': 'calculateCost()'
        })
    )
    
    # เปอร์เซ็นต์ Waste (มาตรฐาน 5-10%)
    waste_percent = forms.DecimalField(
        label='เปอร์เซ็นต์ Waste (การสูญเสีย)',
        initial=5.0,
        min_value=0,
        max_value=100,
        max_digits=5,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.1',
            'oninput': 'calculateCost()'
        }),
        help_text='ค่าเสียเปล่าในการปรุง (มาตรฐาน 5-10%)'
    )
    
    # เปอร์เซ็นต์ Food Cost เป้าหมาย (มาตรฐาน 25-35%)
    target_food_cost_percent = forms.DecimalField(
        label='เปอร์เซ็นต์ Food Cost เป้าหมาย',
        initial=30.0,
        min_value=0,
        max_value=100,
        max_digits=5,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.1',
            'oninput': 'calculateCost()'
        }),
        help_text='อัตราต้นทุนอาหารที่ต้องการ (มาตรฐาน 25-35% สำหรับร้านอาหารไทย)'
    )
    
    # Overhead Costs (ค่าใช้จ่ายอื่นๆ)
    overhead_utilities = forms.DecimalField(
        label='ค่าน้ำค่าไฟ (Utilities)',
        initial=4.80,
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'oninput': 'calculateCost()'
        })
    )
    
    overhead_labor = forms.DecimalField(
        label='ค่าแรง (Labor)',
        initial=16.20,
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'oninput': 'calculateCost()'
        })
    )
    
    overhead_rent = forms.DecimalField(
        label='ค่าเช่า (Rent)',
        initial=6.00,
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'oninput': 'calculateCost()'
        })
    )
    
    overhead_depreciation = forms.DecimalField(
        label='ค่าเสื่อมราคา (Depreciation)',
        initial=1.80,
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'oninput': 'calculateCost()'
        })
    )
    
    overhead_marketing = forms.DecimalField(
        label='ค่าการตลาด (Marketing)',
        initial=1.80,
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'oninput': 'calculateCost()'
        })
    )
    
    overhead_delivery = forms.DecimalField(
        label='ค่าส่ง (Delivery)',
        initial=17.01,
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'oninput': 'calculateCost()'
        })
    )
    
    # ราคาขายจริง (ถ้ามี)
    actual_selling_price = forms.DecimalField(
        label='ราคาขายจริง (ถ้ามี)',
        required=False,
        min_value=0,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'oninput': 'calculateCost()',
            'placeholder': 'เว้นว่างไว้หากยังไม่ได้ตั้งราคาขาย'
        })
    )
    
    def get_overhead_costs(self):
        """ดึงค่า overhead ทั้งหมดเป็น dictionary"""
        return {
            'utilities': self.cleaned_data.get('overhead_utilities') or Decimal('0'),
            'labor': self.cleaned_data.get('overhead_labor') or Decimal('0'),
            'rent': self.cleaned_data.get('overhead_rent') or Decimal('0'),
            'depreciation': self.cleaned_data.get('overhead_depreciation') or Decimal('0'),
            'marketing': self.cleaned_data.get('overhead_marketing') or Decimal('0'),
            'delivery': self.cleaned_data.get('overhead_delivery') or Decimal('0'),
        }

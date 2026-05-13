from rest_framework import serializers
from .models import Owner, Branch, Ingredient, Recipe, RecipeItem, Menu, Sale, Setting, PriceHistory, Purchase, PurchaseItem


class OwnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Owner
        fields = ['id', 'name', 'email', 'phone', 'address', 'logo', 'created_at', 'updated_at']
        extra_kwargs = {
            'logo': {'required': False, 'allow_null': True},
        }


class BranchSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source='owner.name', read_only=True)
    
    class Meta:
        model = Branch
        fields = ['id', 'owner', 'owner_name', 'name', 'address', 'phone', 'created_at', 'updated_at']


class IngredientSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    
    class Meta:
        model = Ingredient
        fields = ['id', 'branch', 'branch_name', 'name', 'price', 'unit', 'stock', 'created_at', 'updated_at']


class RecipeItemSerializer(serializers.ModelSerializer):
    ingredient_name = serializers.CharField(source='ingredient.name', read_only=True)
    ingredient_unit = serializers.CharField(source='ingredient.unit', read_only=True)
    
    class Meta:
        model = RecipeItem
        fields = ['id', 'recipe', 'ingredient', 'ingredient_name', 'ingredient_unit', 'quantity']

class RecipeSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    items = RecipeItemSerializer(many=True, read_only=True)
    menus = serializers.SerializerMethodField()
    
    class Meta:
        model = Recipe
        fields = ['id', 'branch', 'branch_name', 'name', 'description', 'items', 'menus', 'created_at', 'updated_at']
    
    def get_menus(self, obj):
        """Return list of menu IDs and names linked to this recipe"""
        menus = obj.menu_set.all()
        return [{'id': m.id, 'name': m.name} for m in menus]

class MenuSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    recipe_name = serializers.CharField(source='recipe.name', read_only=True)
    food_cost_percent = serializers.SerializerMethodField()
    
    class Meta:
        model = Menu
        fields = ['id', 'branch', 'branch_name', 'recipe', 'recipe_name', 'name', 'price', 'description', 'food_cost_percent', 'created_at', 'updated_at']
    
    def get_food_cost_percent(self, obj):
        """คำนวณ Food Cost % จากต้นทุนวัตถุดิบในสูตร / ราคาขาย*100"""
        if not obj.recipe or not obj.price:
            return None
        total_cost = 0
        for item in obj.recipe.items.all():
            total_cost += float(item.quantity) * float(item.ingredient.price)
        menu_price = float(obj.price)
        if menu_price > 0:
            return round(total_cost / menu_price * 100, 1)
        return None


class SaleSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    menu_name = serializers.CharField(source='menu.name', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    
    class Meta:
        model = Sale
        fields = ['id', 'branch', 'branch_name', 'menu', 'menu_name', 'quantity', 'total_price', 'sale_date', 'payment_method', 'payment_method_display', 'note']


class SettingSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    
    class Meta:
        model = Setting
        fields = ['id', 'branch', 'branch_name', 'business_name', 'tax_rate', 'currency',
                  'overhead_utilities', 'overhead_labor', 'overhead_rent', 
                  'overhead_depreciation', 'overhead_marketing', 'overhead_delivery',
                  'created_at', 'updated_at']


class PriceHistorySerializer(serializers.ModelSerializer):
    ingredient_name = serializers.CharField(source='ingredient.name', read_only=True)
    purchase_id = serializers.IntegerField(source='purchase.id', read_only=True)
    
    class Meta:
        model = PriceHistory
        fields = ['id', 'ingredient', 'ingredient_name', 'price', 'quantity_purchased', 'purchase', 'purchase_id', 'effective_date', 'note']


class PurchaseItemSerializer(serializers.ModelSerializer):
    ingredient_name = serializers.CharField(source='ingredient.name', read_only=True)
    ingredient_unit = serializers.CharField(source='ingredient.unit', read_only=True)
    
    class Meta:
        model = PurchaseItem
        fields = ['id', 'purchase', 'ingredient', 'ingredient_name', 'ingredient_unit', 'quantity', 'unit_price', 'total_price']


class PurchaseSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    items = PurchaseItemSerializer(many=True, read_only=True)
    supplier_name_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Purchase
        fields = ['id', 'branch', 'branch_name', 'supplier_name', 'invoice_number', 'purchase_date', 'total_amount', 'payment_status', 'note', 'items', 'created_at', 'updated_at', 'supplier_name_display']
    
    def get_supplier_name_display(self, obj):
        return obj.get_payment_status_display()


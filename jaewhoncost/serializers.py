from rest_framework import serializers
from .models import Owner, Branch, Ingredient, Recipe, RecipeItem, Menu, Sale, Setting, PriceHistory, Purchase, PurchaseItem


class OwnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Owner
        fields = ['id', 'name', 'email', 'phone', 'address', 'created_at', 'updated_at']


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
    items = RecipeItemSerializer(many=True, read_only=True)  # ✅ ลบ source='items'
    
    class Meta:
        model = Recipe
        fields = ['id', 'branch', 'branch_name', 'name', 'description', 'items', 'created_at', 'updated_at']

class MenuSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    recipe_name = serializers.CharField(source='recipe.name', read_only=True)
    
    class Meta:
        model = Menu
        fields = ['id', 'branch', 'branch_name', 'recipe', 'recipe_name', 'name', 'price', 'description', 'created_at', 'updated_at']


class SaleSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    menu_name = serializers.CharField(source='menu.name', read_only=True)
    
    class Meta:
        model = Sale
        fields = ['id', 'branch', 'branch_name', 'menu', 'menu_name', 'quantity', 'total_price', 'sale_date']


class SettingSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    
    class Meta:
        model = Setting
        fields = ['id', 'branch', 'branch_name', 'business_name', 'tax_rate', 'currency', 'created_at', 'updated_at']


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


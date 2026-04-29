from rest_framework import serializers
from .models import Owner, Branch, Ingredient, Recipe, RecipeItem, Menu, Sale, Setting


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


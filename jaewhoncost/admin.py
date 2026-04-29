# Register your models here.
from django.contrib import admin
from .models import Owner, Branch, Ingredient, Recipe, RecipeItem, Menu, Sale, Setting

# ===== 1. Owner Admin =====
@admin.register(Owner)
class OwnerAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'created_at')
    search_fields = ('name', 'email')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('ข้อมูลเจ้าของร้าน', {
            'fields': ('name', 'email', 'phone', 'address')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


# ===== 2. Branch Admin =====
@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'phone', 'created_at')
    list_filter = ('owner', 'created_at')
    search_fields = ('name', 'address')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('ข้อมูลสาขา', {
            'fields': ('owner', 'name', 'address', 'phone')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


# ===== 3. Ingredient Admin =====
@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'branch', 'price', 'unit', 'stock', 'created_at')
    list_filter = ('branch', 'unit', 'created_at')
    search_fields = ('name', 'branch__name')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('ข้อมูลวัตถุดิบ', {
            'fields': ('branch', 'name', 'price', 'unit', 'stock')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


# ===== 4. Recipe Admin =====
@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('name', 'branch', 'created_at')
    list_filter = ('branch', 'created_at')
    search_fields = ('name', 'branch__name')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('ข้อมูลสูตรอาหาร', {
            'fields': ('branch', 'name', 'description')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


# ===== 5. RecipeItem Admin =====
class RecipeItemInline(admin.TabularInline):
    model = RecipeItem
    extra = 1
    fields = ('ingredient', 'quantity')


# Unregister the previous Recipe admin if it exists
try:
    admin.site.unregister(Recipe)
except admin.sites.NotRegistered:
    pass


@admin.register(Recipe)
class RecipeAdminWithItems(admin.ModelAdmin):
    list_display = ('name', 'branch', 'created_at')
    list_filter = ('branch', 'created_at')
    search_fields = ('name', 'branch__name')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [RecipeItemInline]
    fieldsets = (
        ('ข้อมูลสูตรอาหาร', {
            'fields': ('branch', 'name', 'description')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


# ===== 6. Menu Admin =====
@admin.register(Menu)
class MenuAdmin(admin.ModelAdmin):
    list_display = ('name', 'branch', 'recipe', 'price', 'created_at')
    list_filter = ('branch', 'created_at')
    search_fields = ('name', 'branch__name')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('ข้อมูลเมนู', {
            'fields': ('branch', 'recipe', 'name', 'price', 'description')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


# ===== 7. Sale Admin =====
@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('menu', 'branch', 'quantity', 'total_price', 'sale_date')
    list_filter = ('branch', 'sale_date')
    search_fields = ('menu__name', 'branch__name')
    readonly_fields = ('sale_date',)
    fieldsets = (
        ('ข้อมูลการขาย', {
            'fields': ('branch', 'menu', 'quantity', 'total_price')
        }),
        ('Timestamps', {
            'fields': ('sale_date',),
            'classes': ('collapse',)
        }),
    )


# ===== 8. Setting Admin =====
@admin.register(Setting)
class SettingAdmin(admin.ModelAdmin):
    list_display = ('branch', 'business_name', 'tax_rate', 'currency', 'updated_at')
    list_filter = ('currency', 'updated_at')
    search_fields = ('business_name', 'branch__name')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('ข้อมูลการตั้งค่า', {
            'fields': ('branch', 'business_name', 'tax_rate', 'currency')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


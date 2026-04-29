from django.db import models

# ===== 1. Owner Model =====
class Owner(models.Model):
    """เจ้าของร้าน"""
    name = models.CharField(max_length=100, unique=True)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)
    address = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'เจ้าของร้าน'
        verbose_name_plural = 'เจ้าของร้าน'
    
    def __str__(self):
        return self.name


# ===== 2. Branch Model =====
class Branch(models.Model):
    """สาขา"""
    owner = models.ForeignKey(Owner, on_delete=models.CASCADE, related_name='branches')
    name = models.CharField(max_length=100)
    address = models.TextField()
    phone = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'สาขา'
        verbose_name_plural = 'สาขา'
        unique_together = ['owner', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.owner.name})"


# ===== 3. Ingredient Model =====
class Ingredient(models.Model):
    """วัตถุดิบ"""
    UNIT_CHOICES = [
        ('kg', 'กิโลกรัม'),
        ('g', 'กรัม'),
        ('l', 'ลิตร'),
        ('ml', 'มิลลิลิตร'),
        ('pcs', 'ชิ้น'),
        ('box', 'กล่อง'),
    ]
    
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='ingredients')
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=4)
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES)
    stock = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'วัตถุดิบ'
        verbose_name_plural = 'วัตถุดิบ'
        unique_together = ['branch', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.unit})"


# ===== 4. Recipe Model =====
class Recipe(models.Model):
    """สูตรอาหาร"""
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='recipes')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'สูตรอาหาร'
        verbose_name_plural = 'สูตรอาหาร'
        unique_together = ['branch', 'name']
    
    def __str__(self):
        return self.name


# ===== 5. RecipeItem Model =====
class RecipeItem(models.Model):
    """รายการวัตถุดิบในสูตร"""
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='items')
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=4)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'รายการวัตถุดิบในสูตร'
        verbose_name_plural = 'รายการวัตถุดิบในสูตร'
        unique_together = ['recipe', 'ingredient']
    
    def __str__(self):
        return f"{self.recipe.name} - {self.ingredient.name}"


# ===== 6. Menu Model =====
class Menu(models.Model):
    """เมนู"""
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='menus')
    name = models.CharField(max_length=100)
    recipe = models.ForeignKey(Recipe, on_delete=models.SET_NULL, null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'เมนู'
        verbose_name_plural = 'เมนู'
        unique_together = ['branch', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.price})"


# ===== 7. Sale Model =====
class Sale(models.Model):
    """การขาย"""
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='sales')
    menu = models.ForeignKey(Menu, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    sale_date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'การขาย'
        verbose_name_plural = 'การขาย'
    
    def __str__(self):
        return f"{self.menu.name} x{self.quantity}"


# ===== 8. Setting Model =====
class Setting(models.Model):
    """การตั้งค่า"""
    branch = models.OneToOneField(Branch, on_delete=models.CASCADE, related_name='setting')
    business_name = models.CharField(max_length=100)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    currency = models.CharField(max_length=10, default='THB')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'การตั้งค่า'
        verbose_name_plural = 'การตั้งค่า'
    
    def __str__(self):
        return f"Setting - {self.branch.name}"


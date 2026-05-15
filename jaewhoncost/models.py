from django.db import models

# ===== 1. Owner Model =====
class Owner(models.Model):
    """เจ้าของร้าน"""
    name = models.CharField(max_length=100, unique=True)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)
    address = models.TextField()
    logo = models.ImageField(upload_to='logos/', blank=True, null=True)
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
    sort_order = models.PositiveIntegerField(default=0, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'วัตถุดิบ'
        verbose_name_plural = 'วัตถุดิบ'
        unique_together = ['branch', 'name']
        ordering = ['sort_order', 'id']
    
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
    yield_percent = models.DecimalField(max_digits=5, decimal_places=1, default=100.0,
        verbose_name='Yield (%)', help_text='เปอร์เซ็นต์ Yield ของวัตถุดิบนี้ (100% = ไม่มีเศษ)')
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
    sort_order = models.PositiveIntegerField(default=0, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'เมนู'
        verbose_name_plural = 'เมนู'
        unique_together = ['branch', 'name']
        ordering = ['sort_order', 'id']
    
    def __str__(self):
        return f"{self.name} ({self.price})"


# ===== 7. Sale Model =====
class Sale(models.Model):
    """การขาย"""
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'เงินสด'),
        ('transfer', 'เงินโอน'),
        ('credit_card', 'บัตรเครดิต'),
        ('promptpay', 'พร้อมเพย์'),
        ('other', 'อื่นๆ'),
    ]

    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='sales')
    menu = models.ForeignKey(Menu, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    sale_date = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='cash', verbose_name='วิธีชำระเงิน')
    note = models.CharField(max_length=255, blank=True, verbose_name='หมายเหตุ')
    
    class Meta:
        verbose_name = 'การขาย'
        verbose_name_plural = 'การขาย'
        ordering = ['-sale_date']
    
    def __str__(self):
        return f"{self.menu.name} x{self.quantity}"


# ===== 8. Setting Model =====
class Setting(models.Model):
    """การตั้งค่า"""
    branch = models.OneToOneField(Branch, on_delete=models.CASCADE, related_name='setting')
    business_name = models.CharField(max_length=100)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    currency = models.CharField(max_length=10, default='THB')
    
    # Overhead costs
    overhead_utilities = models.DecimalField(max_digits=10, decimal_places=2, default=4.80, verbose_name='ค่าสาธารณูปโภค')
    overhead_labor = models.DecimalField(max_digits=10, decimal_places=2, default=16.20, verbose_name='ค่าแรงงาน')
    overhead_rent = models.DecimalField(max_digits=10, decimal_places=2, default=6.00, verbose_name='ค่าเช่า')
    overhead_depreciation = models.DecimalField(max_digits=10, decimal_places=2, default=1.80, verbose_name='ค่าเสื่อมราคา')
    overhead_marketing = models.DecimalField(max_digits=10, decimal_places=2, default=1.80, verbose_name='ค่าการตลาด')
    overhead_delivery = models.DecimalField(max_digits=10, decimal_places=2, default=17.01, verbose_name='ค่าจัดส่ง')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'การตั้งค่า'
        verbose_name_plural = 'การตั้งค่า'
    
    def __str__(self):
        return f"Setting - {self.branch.name}"
    
    def get_total_overhead(self):
        """คำนวณรวม overhead ทั้งหมด"""
        return (self.overhead_utilities + self.overhead_labor + self.overhead_rent + 
                self.overhead_depreciation + self.overhead_marketing + self.overhead_delivery)


# ===== 9. PriceHistory Model =====
class PriceHistory(models.Model):
    """ประวัติราคาวัตถุดิบตามช่วงเวลา"""
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, related_name='price_history')
    price = models.DecimalField(max_digits=10, decimal_places=4)
    quantity_purchased = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    purchase = models.ForeignKey('Purchase', on_delete=models.SET_NULL, null=True, blank=True, related_name='price_histories')
    effective_date = models.DateTimeField(auto_now_add=True)
    note = models.CharField(max_length=255, blank=True)
    
    class Meta:
        verbose_name = 'ประวัติราคาวัตถุดิบ'
        verbose_name_plural = 'ประวัติราคาวัตถุดิบ'
        ordering = ['-effective_date']
    
    def __str__(self):
        return f"{self.ingredient.name}: {self.price} บาท ({self.effective_date.strftime('%d/%m/%Y')})"


# ===== 10. Purchase Model =====
class Purchase(models.Model):
    """การจัดซื้อวัตถุดิบ"""
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'รอชำระ'),
        ('paid', 'ชำระแล้ว'),
        ('partial', 'ชำระบางส่วน'),
    ]
    
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='purchases')
    supplier_name = models.CharField(max_length=100, blank=True)
    invoice_number = models.CharField(max_length=50, blank=True)
    purchase_date = models.DateTimeField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'การจัดซื้อ'
        verbose_name_plural = 'การจัดซื้อ'
        ordering = ['-purchase_date']
    
    def __str__(self):
        return f"จัดซื้อ #{self.id} - {self.branch.name} ({self.purchase_date.strftime('%d/%m/%Y')})"
    
    def update_total(self):
        """อัปเดตยอดรวมจากรายการจัดซื้อ"""
        total = sum(item.total_price for item in self.items.all())
        self.total_amount = total
        self.save()


# ===== 11. PurchaseItem Model =====
class PurchaseItem(models.Model):
    """รายการวัตถุดิบในใบจัดซื้อ"""
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, related_name='items')
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=4)
    unit_price = models.DecimalField(max_digits=10, decimal_places=4)
    total_price = models.DecimalField(max_digits=12, decimal_places=2, blank=True)
    
    class Meta:
        verbose_name = 'รายการจัดซื้อ'
        verbose_name_plural = 'รายการจัดซื้อ'
        unique_together = ['purchase', 'ingredient']
    
    def __str__(self):
        return f"{self.ingredient.name} x {self.quantity} {self.ingredient.unit}"
    
    def save(self, *args, **kwargs):
        # คำนวณราคารวม
        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)
        
        # อัปเดตสต็อกและราคาวัตถุดิบ
        ingredient = self.ingredient
        ingredient.stock += int(self.quantity)
        ingredient.price = self.unit_price
        ingredient.save()
        
        # บันทึกประวัติราคา
        PriceHistory.objects.create(
            ingredient=ingredient,
            price=self.unit_price,
            quantity_purchased=self.quantity,
            purchase=self.purchase,
            note=f"จัดซื้อจากใบจัดซื้อ #{self.purchase.id}"
        )
        
        # อัปเดตยอดรวมใบจัดซื้อ
        self.purchase.update_total()


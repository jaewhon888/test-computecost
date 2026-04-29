#!/usr/bin/env python3
"""
Import 3 Jaew Hon menus from CSV into Django system
Menus: 
1. แจ่วฮ้อนผัดแห้ง
2. แจ่วฮ้อนถ้วยด่วนเนื้อ
3. แจ่วฮ้อนถ้วยด่วนหมู
"""
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from jaewhoncost.models import Branch, Ingredient, Recipe, RecipeItem, Menu
from decimal import Decimal

def get_or_create_ingredient(name, unit, price, branch):
    """Create ingredient if not exists"""
    ing, created = Ingredient.objects.get_or_create(
        name=name,
        branch=branch,
        defaults={'unit': unit, 'price': Decimal(str(price))}
    )
    if not created and ing.price != Decimal(str(price)):
        print(f'  Update price: {ing.name} {ing.price} -> {price}')
        ing.price = Decimal(str(price))
        ing.save()
    return ing

def import_jaewhon_menus():
    print('=== เริ่มนำเข้าเมนูแจ่วฮ้อน 3 เมนู ===\n')
    
    # Get first branch (assuming exists)
    branch = Branch.objects.first()
    if not branch:
        print('ERROR: No branch found!')
        return
    print(f'Using branch: {branch.name}\n')
    
    # Define ingredients for all 3 menus
    ingredients_data = [
        # Common ingredients
        ('น้ำแจ่ว', 'ml', 0.008),  # 8 บาท/ลิตร = 0.008 บาท/มล.
        ('กระหล่ำปี', 'kg', 20.00),  # 20 บาท/กก.
        ('ผักบุ้ง', 'kg', 30.00),
        ('ตั้งโอ๋', 'kg', 80.00),
        ('โหระพา', 'kg', 60.00),
        ('ใบเรื่อย', 'kg', 100.00),
        ('เห็ดเข็มทอง', 'kg', 60.00),
        ('ตับ', 'kg', 115.00),
        ('หมึกกรอบ', 'kg', 150.00),
        ('สไบนาง', 'kg', 180.00),
        ('ไข่ไก่', 'pcs', 4.00),  # 4 บาท/ฟอง
        ('กระเทียม', 'kg', 85.00),
        ('น้ำจิ้มหวาน', 'ml', 0.133),  # 30 มล. = 4 บาท
        ('น้ำจิ้มเค็ม', 'ml', 0.10),  # 30 มล. = 3 บาท
        ('วุ้นเส้น', 'kg', 44.00),  # 2.20 บาท/50กรัม
        # Menu specific
        ('ปลาดอลลี่', 'kg', 240.00),
        ('เนื้อวัว', 'kg', 109.00),
        ('เนื้อหมู', 'kg', 70.00),
        ('หมี่หยก', 'kg', 36.60),  # 1.83 บาท/50กรัม
    ]
    
    print('1. Creating/Updating ingredients...')
    ing_map = {}
    for name, unit, price in ingredients_data:
        ing = get_or_create_ingredient(name, unit, price, branch)
        ing_map[name] = ing
        print(f'  ✓ {name} ({unit}) - ฿{price}')
    
    print('\n2. Creating Recipes and RecipeItems...\n')
    
    # Menu 1: แจ่วฮ้อนผัดแห้ง
    print('=== เมนูที่ 1: แจ่วฮ้อนผัดแห้ง ===')
    recipe1, created = Recipe.objects.get_or_create(
        name='แจ่วฮ้อนผัดแห้ง',
        branch=branch,
    )
    if created:
        print(f'  Created Recipe: {recipe1.name}')
    else:
        print(f'  Recipe exists: {recipe1.name}')
        recipe1.items.all().delete()  # Clear old items
    
    # Add items for menu 1
    items1 = [
        ('ปลาดอลลี่', 0.050, 10.25),  # 50 กรัม
        ('น้ำแจ่ว', 250, 2.00),  # 1 กระบวย
        ('กระหล่ำปี', 0.300, 6.00),  # นิดนิด ≈ 300 กรัม
        ('ผักบุ้ง', 0.010, 0),
        ('ตั้งโอ๋', 0.010, 0),
        ('โหระพา', 0.010, 0),
        ('ใบเรื่อย', 0.010, 0),
        ('เห็ดเข็มทอง', 0.010, 0),
        ('หมี่หยก', 0.050, 1.83),  # 50 กรัม
        ('ตับ', 0.040, 4.79),  # 40 กรัม
        ('หมึกกรอบ', 0.030, 6.69),  # 30 กรัม
        ('สไบนาง', 0.040, 7.20),  # 40 กรัม
        ('ไข่ไก่', 1, 4.00),  # 1 ฟอง
        ('กระเทียม', 0.010, 1.00),  # 2 กลีบ ≈ 10 กรัม
        ('น้ำจิ้มหวาน', 30, 4.00),
        ('น้ำจิ้มเค็ม', 30, 3.00),
    ]
    
    for name, qty, cost in items1:
        if name in ing_map and cost > 0:  # Skip items with no cost
            item = RecipeItem.objects.create(
                recipe=recipe1,
                ingredient=ing_map[name],
                quantity=Decimal(str(qty))
            )
            print(f'  + {name}: {qty} {ing_map[name].unit}')
    
    # Menu 2: แจ่วฮ้อนถ้วยด่วนเนื้อ
    print('\n=== เมนูที่ 2: แจ่วฮ้อนถ้วยด่วนเนื้อ ===')
    recipe2, created = Recipe.objects.get_or_create(
        name='แจ่วฮ้อนถ้วยด่วนเนื้อ',
        branch=branch,
    )
    if created:
        print(f'  Created Recipe: {recipe2.name}')
    else:
        print(f'  Recipe exists: {recipe2.name}')
        recipe2.items.all().delete()
    
    items2 = [
        ('เนื้อวัว', 0.100, 11.47),  # 100 กรัม
        ('น้ำแจ่ว', 250, 2.00),
        ('กระหล่ำปี', 0.300, 6.00),
        ('ผักบุ้ง', 0.010, 0),
        ('ตั้งโอ๋', 0.010, 0),
        ('โหระพา', 0.010, 0),
        ('ใบเรื่อย', 0.010, 0),
        ('เห็ดเข็มทอง', 0.010, 0),
        ('วุ้นเส้น', 0.050, 2.20),  # นิดนิด ≈ 50 กรัม
        ('ตับ', 0.040, 4.79),
        ('หมึกกรอบ', 0.030, 6.92),
        ('สไบนาง', 0.040, 7.20),
        ('ไข่ไก่', 1, 0),  # ไม่มีราคาใน CSV
        ('กระเทียม', 0.010, 1.00),
        ('น้ำจิ้มหวาน', 30, 4.00),
        ('น้ำจิ้มเค็ม', 30, 3.00),
    ]
    
    for name, qty, cost in items2:
        if name in ing_map and cost > 0:
            item = RecipeItem.objects.create(
                recipe=recipe2,
                ingredient=ing_map[name],
                quantity=Decimal(str(qty))
            )
            print(f'  + {name}: {qty} {ing_map[name].unit}')
    
    # Menu 3: แจ่วฮ้อนถ้วยด่วนหมู
    print('\n=== เมนูที่ 3: แจ่วฮ้อนถ้วยด่วนหมู ===')
    recipe3, created = Recipe.objects.get_or_create(
        name='แจ่วฮ้อนถ้วยด่วนหมู',
        branch=branch,
    )
    if created:
        print(f'  Created Recipe: {recipe3.name}')
    else:
        print(f'  Recipe exists: {recipe3.name}')
        recipe3.items.all().delete()
    
    items3 = [
        ('เนื้อหมู', 0.100, 7.37),  # 100 กรัม
        ('น้ำแจ่ว', 250, 2.00),
        ('กระหล่ำปี', 0.300, 6.00),
        ('ผักบุ้ง', 0.010, 0),
        ('ตั้งโอ๋', 0.010, 0),
        ('โหระพา', 0.010, 0),
        ('ใบเรื่อย', 0.010, 0),
        ('เห็ดเข็มทอง', 0.010, 0),
        ('วุ้นเส้น', 0.050, 2.20),
        ('ตับ', 0.040, 4.79),
        ('หมึกกรอบ', 0.030, 6.92),
        ('สไบนาง', 0.040, 7.20),
        ('ไข่ไก่', 1, 0),  # ไม่มีราคาใน CSV
        ('กระเทียม', 0.010, 1.00),
        ('น้ำจิ้มหวาน', 30, 4.00),
        ('น้ำจิ้มเค็ม', 30, 3.00),
    ]
    
    for name, qty, cost in items3:
        if name in ing_map and cost > 0:
            item = RecipeItem.objects.create(
                recipe=recipe3,
                ingredient=ing_map[name],
                quantity=Decimal(str(qty))
            )
            print(f'  + {name}: {qty} {ing_map[name].unit}')
    
    # Create Menus and link to Recipes
    print('\n3. Creating/Updating Menus...\n')
    
    menus_data = [
        (recipe1, 'แจ่วฮ้อนผัดแห้ง', 70.00),  # Estimated selling price
        (recipe2, 'แจ่วฮ้อนถ้วยด่วนเนื้อ', 100.00),  # From CSV: 70+ overhead
        (recipe3, 'แจ่วฮ้อนถ้วยด่วนหมู', 90.00),  # From CSV: ~70+ overhead
    ]
    
    for recipe, menu_name, price in menus_data:
        menu, created = Menu.objects.get_or_create(
            name=menu_name,
            branch=branch,
            defaults={'recipe': recipe, 'price': Decimal(str(price))}
        )
        if created:
            print(f'  ✓ Created Menu: {menu_name} - ฿{price}')
        else:
            menu.recipe = recipe
            menu.price = Decimal(str(price))
            menu.save()
            print(f'  ✓ Updated Menu: {menu_name} - ฿{price}')
    
    print('\n=== เสร็จสิ้นการนำเข้า ===')
    print(f'\nสรุป:')
    print(f'- Ingredients: {Ingredient.objects.count()} รายการ')
    print(f'- Recipes: {Recipe.objects.count()} รายการ')
    print(f'- Menus: {Menu.objects.count()} รายการ')

if __name__ == '__main__':
    import_jaewhon_menus()

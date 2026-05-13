import csv
import os
from datetime import datetime
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

from jaewhoncost.models import Owner, Branch, Ingredient, Purchase, PurchaseItem, PriceHistory


class Command(BaseCommand):
    help = 'Import data from CSV or Excel files for inventory adjustment or purchase creation.'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='Path to the CSV or Excel file')
        parser.add_argument(
            '--mode',
            type=str,
            choices=['inventory', 'purchase'],
            required=True,
            help='Mode of operation: inventory (adjust stock) or purchase (create purchase orders)'
        )
        parser.add_argument(
            '--branch',
            type=str,
            help='Branch name (required for inventory mode if not in file)'
        )
        parser.add_argument(
            '--supplier',
            type=str,
            help='Supplier name (for purchase mode)'
        )
        parser.add_argument(
            '--invoice',
            type=str,
            help='Invoice number (for purchase mode)'
        )
        parser.add_argument(
            '--date',
            type=str,
            help='Purchase date in YYYY-MM-DD format (defaults to today)'
        )
        parser.add_argument(
            '--sheet',
            type=str,
            default=0,
            help='Excel sheet name or index (default: first sheet)'
        )
        parser.add_argument(
            '--delimiter',
            type=str,
            default=',',
            help='CSV delimiter (default: comma)'
        )

    def handle(self, *args, **options):
        file_path = options['file_path']
        mode = options['mode']
        branch_name = options.get('branch')
        supplier_name = options.get('supplier')
        invoice_number = options.get('invoice')
        date_str = options.get('date')
        sheet = options['sheet']
        delimiter = options['delimiter']

        if not os.path.exists(file_path):
            raise CommandError(f'File "{file_path}" does not exist.')

        # Determine file type
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.csv':
            data = self.read_csv(file_path, delimiter)
        elif ext in ['.xls', '.xlsx']:
            if not PANDAS_AVAILABLE:
                raise CommandError(' pandas is required to read Excel files. Install pandas or use CSV.')
            data = self.read_excel(file_path, sheet)
        else:
            raise CommandError('Unsupported file format. Use CSV or Excel.')

        if mode == 'inventory':
            self.handle_inventory(data, branch_name)
        else:
            self.handle_purchase(data, branch_name, supplier_name, invoice_number, date_str)

    # ------------------- CSV/Excel reading -------------------
    def read_csv(self, file_path, delimiter):
        with open(file_path, newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=delimiter)
            rows = []
            for row in reader:
                # strip whitespace from keys and values
                row = {k.strip(): v.strip() if isinstance(v, str) else v for k, v in row.items()}
                rows.append(row)
            return rows

    def read_excel(self, file_path, sheet):
        df = pd.read_excel(file_path, sheet_name=sheet, dtype=str)  # read all as string to avoid type issues
        df = df.fillna('')  # replace NaN with empty string
        # convert to list of dicts
        return df.to_dict('records')

    # ------------------- Inventory mode -------------------
    def handle_inventory(self, data, branch_name):
        if not branch_name:
            # try to get branch from first row
            if data and 'branch_name' in data[0]:
                branch_name = data[0]['branch_name']
            else:
                raise CommandError('Branch name must be provided via --branch or column "branch_name" in file.')

        try:
            branch = Branch.objects.get(name__iexact=branch_name)
        except Branch.DoesNotExist:
            raise CommandError(f'Branch "{branch_name}" does not exist.')

        updated = 0
        errors = []

        with transaction.atomic():
            for i, row in enumerate(data, start=2):  # start at line 2 (header is line 1)
                ingredient_name = row.get('ingredient_name') or row.get('ingredient')
                change_str = row.get('change_quantity') or row.get('quantity') or row.get('change')
                note = row.get('note', '')

                if not ingredient_name or change_str is None:
                    errors.append(f'Line {i}: Missing ingredient_name or change_quantity')
                    continue

                try:
                    change = Decimal(change_str)
                except Exception:
                    errors.append(f'Line {i}: Invalid quantity "{change_str}"')
                    continue

                try:
                    ingredient = Ingredient.objects.get(
                        name__iexact=ingredient_name,
                        branch=branch
                    )
                except Ingredient.DoesNotExist:
                    errors.append(f'Line {i}: Ingredient "{ingredient_name}" not found in branch "{branch.name}"')
                    continue
                except Ingredient.MultipleObjectsReturned:
                    errors.append(f'Line {i}: Multiple ingredients match "{ingredient_name}" in branch "{branch.name}"')
                    continue

                new_stock = ingredient.stock + change
                if new_stock < 0:
                    errors.append(f'Line {i}: Adjustment would result in negative stock for "{ingredient.name}" (current {ingredient.stock}, change {change})')
                    continue

                ingredient.stock = new_stock
                ingredient.save()
                updated += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Line {i}: Updated {ingredient.name} stock from {ingredient.stock - change} to {ingredient.stock} ({change})'
                    )
                )

        self.stdout.write(self.style.SUCCESS(f'\nInventory update completed. {updated} records updated.'))
        if errors:
            self.stdout.write(self.style.WARNING(f'Encountered {len(errors)} errors:'))
            for err in errors[:5]:  # limit output
                self.stdout.write(self.style.WARNING(f'  - {err}'))
            if len(errors) > 5:
                self.stdout.write(self.style.WARNING(f'  ... and {len(errors) - 5} more errors.'))

    # ------------------- Purchase mode -------------------
    def handle_purchase(self, data, branch_name, supplier_name, invoice_number, date_str):
        # Determine branch
        if not branch_name:
            if data and 'branch_name' in data[0]:
                branch_name = data[0]['branch_name']
            else:
                raise CommandError('Branch name must be provided via --branch or column "branch_name" in file.')

        try:
            branch = Branch.objects.get(name__iexact=branch_name)
        except Branch.DoesNotExist:
            raise CommandError(f'Branch "{branch_name}" does not exist.')

        # Determine date
        if date_str:
            try:
                purchase_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                raise CommandError('Invalid date format. Use YYYY-MM-DD.')
        else:
            purchase_date = datetime.now().date()

        # Group rows by purchase reference if present, otherwise create one purchase per file
        # We'll assume each row is a line item; if purchase_ref column exists, group by it.
        has_ref = data and 'purchase_ref' in data[0]

        purchases = {}  # ref -> Purchase object
        errors = []
        created_count = 0

        with transaction.atomic():
            for i, row in enumerate(data, start=2):
                ingredient_name = row.get('ingredient_name') or row.get('ingredient')
                quantity_str = row.get('quantity')
                unit_price_str = row.get('unit_price') or row.get('price')
                note = row.get('note', '')
                ref = row.get('purchase_ref') if has_ref else None

                if not ingredient_name or not quantity_str or not unit_price_str:
                    errors.append(f'Line {i}: Missing ingredient_name, quantity, or unit_price')
                    continue

                try:
                    quantity = Decimal(quantity_str)
                    unit_price = Decimal(unit_price_str)
                except Exception:
                    errors.append(f'Line {i}: Invalid quantity or unit_price')
                    continue

                try:
                    ingredient = Ingredient.objects.get(
                        name__iexact=ingredient_name,
                        branch=branch
                    )
                except Ingredient.DoesNotExist:
                    errors.append(f'Line {i}: Ingredient "{ingredient_name}" not found in branch "{branch.name}"')
                    continue
                except Ingredient.MultipleObjectsReturned:
                    errors.append(f'Line {i}: Multiple ingredients match "{ingredient_name}" in branch "{branch.name}"')
                    continue

                # Determine purchase reference
                if has_ref:
                    if not ref:
                        errors.append(f'Line {i}: Missing purchase_ref')
                        continue
                    purchase_key = ref
                else:
                    # single purchase for entire file
                    purchase_key = 'single'

                # Get or create Purchase object
                if purchase_key not in purchases:
                    # Create purchase
                    purchase = Purchase.objects.create(
                        branch=branch,
                        supplier_name=supplier_name or '',
                        invoice_number=invoice_number or '',
                        purchase_date=purchase_date,
                        payment_status='pending',
                        note=f'Imported from file on {datetime.now().strftime("%Y-%m-%d %H:%M")}'
                    )
                    purchases[purchase_key] = purchase
                else:
                    purchase = purchases[purchase_key]

                # Create PurchaseItem
                try:
                    item = PurchaseItem.objects.create(
                        purchase=purchase,
                        ingredient=ingredient,
                        quantity=quantity,
                        unit_price=unit_price
                    )
                except Exception as e:
                    errors.append(f'Line {i}: Failed to create PurchaseItem: {e}')
                    continue

                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Line {i}: Created PurchaseItem for {ingredient.name} x{quantity} @ {unit_price}'
                    )
                )

            # Update totals for each purchase
            for purchase_key, purchase in purchases.items():
                purchase.update_total()
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Purchase #{purchase.id} total updated: {purchase.total_amount}'
                    )
                )

        self.stdout.write(self.style.SUCCESS(f'\nPurchase import completed. {created_count} line items created in {len(purchases)} purchase order(s).'))
        if errors:
            self.stdout.write(self.style.WARNING(f'Encountered {len(errors)} errors:'))
            for err in errors[:5]:
                self.stdout.write(self.style.WARNING(f'  - {err}'))
            if len(errors) > 5:
                self.stdout.write(self.style.WARNING(f'  ... and {len(errors) - 5} more errors.'))

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jaewhoncost', '0005_add_overhead_costs_to_setting'),
    ]

    operations = [
        migrations.AddField(
            model_name='sale',
            name='payment_method',
            field=models.CharField(
                choices=[
                    ('cash', 'เงินสด'),
                    ('transfer', 'เงินโอน'),
                    ('credit_card', 'บัตรเครดิต'),
                    ('promptpay', 'พร้อมเพย์'),
                    ('other', 'อื่นๆ'),
                ],
                default='cash',
                max_length=20,
                verbose_name='วิธีชำระเงิน',
            ),
        ),
        migrations.AddField(
            model_name='sale',
            name='note',
            field=models.CharField(blank=True, max_length=255, verbose_name='หมายเหตุ'),
        ),
        migrations.AlterModelOptions(
            name='sale',
            options={'ordering': ['-sale_date'], 'verbose_name': 'การขาย', 'verbose_name_plural': 'การขาย'},
        ),
    ]

# Исправляет невалидный default='Без НДС' -> default='0' в поле vat_rate

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admin_panel', '0015_category_book_category'),
    ]

    operations = [
        # Обновляем существующие записи с невалидным значением
        migrations.RunSQL(
            sql="UPDATE admin_panel_book SET vat_rate = '0' WHERE vat_rate NOT IN ('0', '10', '20');",
            reverse_sql="-- no reverse",
        ),
        migrations.AlterField(
            model_name='book',
            name='vat_rate',
            field=models.CharField(
                max_length=2,
                choices=[('0', 'Без НДС'), ('10', '10%'), ('20', '20%')],
                verbose_name='Ставка НДС',
                default='0',  # ✅ было 'Без НДС'
            ),
        ),
        migrations.AlterField(
            model_name='book',
            name='photos',
            field=models.JSONField(
                default=list,
                verbose_name='Фотографии',
                blank=True,
                # ✅ убран null=True — JSONField с default=list не нуждается в null
            ),
        ),
    ]

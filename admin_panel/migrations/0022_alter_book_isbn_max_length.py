from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admin_panel', '0021_book_isbn_unique_per_source'),
    ]

    operations = [
        migrations.AlterField(
            model_name='book',
            name='isbn',
            field=models.CharField(
                blank=True,
                max_length=20,
                null=True,
                verbose_name='ISBN',
            ),
        ),
    ]

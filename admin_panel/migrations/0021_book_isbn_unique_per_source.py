from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admin_panel', '0020_book_source'),
    ]

    operations = [
        migrations.AlterField(
            model_name='book',
            name='isbn',
            field=models.CharField(
                blank=True,
                max_length=13,
                null=True,
                verbose_name='ISBN',
            ),
        ),
        migrations.AddConstraint(
            model_name='book',
            constraint=models.UniqueConstraint(
                fields=('isbn', 'source'),
                condition=models.Q(isbn__isnull=False),
                name='unique_isbn_per_source',
            ),
        ),
    ]

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('admin_panel', '0028_remove_book_isbn_unique_per_source'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='eksmobook',
            options={
                'verbose_name': 'Книга',
                'verbose_name_plural': 'База книг',
                'proxy': True,
            },
        ),
    ]

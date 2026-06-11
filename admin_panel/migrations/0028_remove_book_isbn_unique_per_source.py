from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('admin_panel', '0027_update_weight_to_grams'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='book',
            name='unique_isbn_per_source',
        ),
    ]

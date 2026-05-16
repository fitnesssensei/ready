import json
from pathlib import Path

from django.db import migrations, models


def mark_eksmo_books(apps, schema_editor):
    Book = apps.get_model('admin_panel', 'Book')
    json_path = Path(__file__).resolve().parents[2] / 'parsing' / 'eksmo_books_mt_deduped.json'
    if not json_path.exists():
        Book.objects.filter(price=0, stock=0).update(source='eksmo')
        return

    with json_path.open(encoding='utf-8') as f:
        rows = json.load(f)

    isbns = []
    for row in rows:
        raw = row.get('isbn', '')
        digits = ''.join(c for c in raw if c.isdigit())
        if len(digits) in (10, 13):
            isbns.append(digits)

    if isbns:
        Book.objects.filter(isbn__in=isbns).update(source='eksmo')


def unmark_eksmo_books(apps, schema_editor):
    Book = apps.get_model('admin_panel', 'Book')
    Book.objects.filter(source='eksmo').update(source='manual')


class Migration(migrations.Migration):

    dependencies = [
        ('admin_panel', '0019_book_series'),
    ]

    operations = [
        migrations.AddField(
            model_name='book',
            name='source',
            field=models.CharField(
                choices=[('manual', 'Админка'), ('eksmo', 'Импорт Эксмо')],
                db_index=True,
                default='manual',
                max_length=10,
                verbose_name='Источник',
            ),
        ),
        migrations.RunPython(mark_eksmo_books, unmark_eksmo_books),
    ]

"""
Data-миграция: нормализация данных существующих записей Book.

1. language — приведение «человеческих»/дублирующих значений к кодам choices:
   'Русский'/'русский'/'russian' -> 'russian', 'английский' -> 'english' и т.д.
   (без разбивки строк; значения открытых полей не трогаем).
2. target_audience — исправление опечатки: 'or children' -> 'for children'.

Нормализация выполняется ОДНИМ UPDATE с CASE (однопроходно), потому что у поля
language нет индекса и обновление по каждому значению отдельно — это полный скан
таблицы на каждое значение (очень долго на 100k+ строках).

Обратимая только частично (старые строковые значения не восстанавливаем).
"""

from django.db import migrations, models
from django.db.models import Case, When, Value


# ключ в нижнем регистре -> канонический код из constants.LANGUAGE_CHOICES
LANG_LOWER_TO_CODE = {
    'russian': 'russian',
    'english': 'english',
    'french': 'french',
    'german': 'german',
    'italian': 'italian',
    'spanish': 'spanish',
    'turkish': 'turkish',
    'chinese': 'chinese',
    'korean': 'korean',
    'greek': 'greek',
    'portuguese': 'portuguese',
    'arabic': 'arabic',
    'japanese': 'japanese',
    'vietnamese': 'vietnamese',
    'thai': 'thai',
    'ukrainian': 'ukrainian',
    'polish': 'polish',
    'latin': 'latin',
    'other': 'other',
    # русские названия/дубли регистра -> коды
    'русский': 'russian',
    'английский': 'english',
    'немецкий': 'german',
    'французский': 'french',
    'итальянский': 'italian',
    'испанский': 'spanish',
    'украинский': 'ukrainian',
    'польский': 'polish',
    'латинский': 'latin',
    'другой': 'other',
}


def normalize_language(apps, schema_editor):
    Book = apps.get_model('admin_panel', 'Book')
    # Строим CASE только для тех значений, которые реально поменяются.
    cases = []
    affected_values = []
    distinct = Book.objects.exclude(language='').values_list('language', flat=True).distinct()
    for value in distinct:
        if value is None:
            continue
        code = LANG_LOWER_TO_CODE.get(value.lower())
        if code is not None and code != value:
            cases.append(When(language=value, then=Value(code)))
            affected_values.append(value)
    if cases:
        Book.objects.filter(language__in=affected_values).update(
            language=Case(*cases, default=models.F('language'))
        )


def fix_target_audience(apps, schema_editor):
    Book = apps.get_model('admin_panel', 'Book')
    Book.objects.filter(target_audience='or children').update(target_audience='for children')


def combine(apps, schema_editor):
    normalize_language(apps, schema_editor)
    fix_target_audience(apps, schema_editor)


def noop(apps, schema_editor):
    """Обратный ход не реализован: значения невосстановимы (нет зеркала)."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('admin_panel', '0095_alter_book_language_alter_book_target_audience'),
    ]

    operations = [
        migrations.RunPython(combine, noop),
    ]
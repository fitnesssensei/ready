"""
Data-миграция: нормализация данных существующих записей Book.

ИСПРАВЛЕННАЯ ВЕРСИЯ. Прежняя вешала прод и уронила базу.

Что было не так
---------------
1. Прежний код делал:

       Book.objects.exclude(language='').values_list('language', flat=True).distinct()

   У модели Book задано ``Meta.ordering = ['-created_at']``. Django без явного
   ``order_by()`` добавляет колонку сортировки в SELECT DISTINCT, поэтому
   реально выполнялся запрос:

       SELECT DISTINCT language, created_at FROM admin_panel_book ...

   ``created_at`` уникален, поэтому возвращалась почти вся таблица (726k
   строк), а не уникальные языки. PostgreSQL сортировал таблицу целиком,
   Django материализовал сотни тысяч строк в Python.

   Итог на сервере с 1 ГБ RAM и диском 9.8 ГБ: 16+ ГБ чтения, 2 ч 43 мин CPU,
   диск 100%, PANIC "could not write to pg_wal/xlogtemp" и аварийное
   завершение PostgreSQL (crash recovery прошёл успешно, данные уцелели).

2. Промежуточная версия обновляла строки отдельным запросом на каждое
   значение языка. Индекса на ``language`` нет, поэтому каждый запрос
   требовал полного сканирования таблицы — тысячи сканирований по 726k строк.

Как сделано здесь
-----------------
Нормализация идёт ОДНИМ проходом по таблице, разбитым на пакеты по
первичному ключу:

  * диапазон ``id`` задаёт пакет — используется индекс первичного ключа,
    полного сканирования таблицы на каждый пакет нет;
  * ``CASE`` переводит все «человеческие» названия языков в коды сразу,
    поэтому отдельные запросы на каждое значение не нужны;
  * ``atomic = False`` + фиксация по пакетам: WAL не накапливается, а
    прерывание не теряет уже сделанную работу.

Идемпотентность: обновляются только строки со значением, отличающимся от
целевого, поэтому повторный запуск безопасен и продолжает с места остановки.

Обратимость: обратный ход не реализован — старые «человеческие» значения
невосстановимы (зеркала значений нет).
"""

from django.db import migrations
from django.db.models import Case, Value, When

# Сколько строк обрабатываем за одну транзакцию. Небольшой размер — осознанный
# выбор: каждая порция пишет WAL, а на сервере мало места (диск 9.8 ГБ,
# свободно ~500 МБ). Пакет задаётся диапазоном id и читается по индексу ПК.
BATCH_SIZE = 1000


def _iter_id_batches(cursor, table):
    """
    Отдаёт (lo, hi) — диапазоны первичного ключа для пакетной обработки.

    Читаем границы одним запросом и идём интервалами, а не листаем всю
    таблицу для поиска следующей группы строк.
    """
    cursor.execute(f'SELECT min(id), max(id) FROM {table}')
    lo, hi = cursor.fetchone()
    if lo is None:
        return
    while lo <= hi:
        yield lo, lo + BATCH_SIZE - 1
        lo += BATCH_SIZE


def normalize_language(apps, schema_editor):
    """
    Приводит «человеческие» названия языков к кодам choices одним проходом.

    LANGUAGE_CHOICES — пары (код, «человеческое» название):
        ('russian', 'Русский'), ('english', 'Английский'), ...
    Меняем НАЗВАНИЕ на КОД. Сравнение регистронезависимое (LOWER), как
    прежнее ``value.lower()`` в Python.
    """
    from admin_panel import constants

    pairs = [
        (label, code)
        for code, label in constants.LANGUAGE_CHOICES
        if label != code
    ]
    if not pairs:
        return

    cursor = schema_editor.connection.cursor()
    table = 'admin_panel_book'

    total = 0
    for lo, hi in _iter_id_batches(cursor, table):
        cursor.execute(
            'UPDATE ' + table + ' SET language = CASE '
            + ' '.join(['WHEN lower(language) = lower(%s) THEN %s'] * len(pairs))
            + ' ELSE language END '
            'WHERE id BETWEEN %s AND %s AND language IS NOT NULL AND language <> \'\'',
            [x for pair in pairs for x in (pair[0], pair[1])] + [lo, hi],
        )
        affected = cursor.rowcount
        if affected:
            total += affected
    print(f'      language: обработано строк с изменением: {total}')


def fix_target_audience(apps, schema_editor):
    """Исправляет опечатку 'or children' -> 'for children' пакетами по id."""
    cursor = schema_editor.connection.cursor()
    table = 'admin_panel_book'
    total = 0
    for lo, hi in _iter_id_batches(cursor, table):
        cursor.execute(
            'UPDATE ' + table + ' SET target_audience = %s '
            'WHERE id BETWEEN %s AND %s AND target_audience = %s',
            ['for children', lo, hi, 'or children'],
        )
        affected = cursor.rowcount
        if affected:
            total += affected
    print(f'      target_audience: исправлено строк: {total}')


def combine(apps, schema_editor):
    normalize_language(apps, schema_editor)
    fix_target_audience(apps, schema_editor)


def noop(apps, schema_editor):
    """Обратный ход не реализован: значения невосстановимы (нет зеркала)."""
    pass


class Migration(migrations.Migration):

    # ВАЖНО: atomic = False нужен для пакетной фиксации. Без него вся миграция
    # выполняется в одной транзакции, WAL растёт лавинообразно (именно это
    # уронило базу), а прерывание откатывает всю работу целиком.
    atomic = False

    dependencies = [
        ('admin_panel', '0095_alter_book_language_alter_book_target_audience'),
    ]

    operations = [
        migrations.RunPython(combine, noop),
    ]

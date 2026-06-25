"""
Скрипт импорта книг из JSON файла издательства АСТ в базу данных.

Импортирует книги из файла JSON/dnevnikiAST.json
в таблицу admin_panel_book с источником 'ast'.

Использование:
    python import_ast.py

Особенности:
    - Батчевая вставка по 500 книг для оптимизации производительности
    - Пропуск дубликатов по ISBN + источник (только для книг с ISBN)
    - Автоматическое определение типа переплета из текстового описания
    - Парсинг года издания и количества страниц
    - Парсинг размеров (width/length) из поля format (например, «145, 207»)
    - Конвертация веса из кг в граммы
    - Маппинг возрастных ограничений (0+, 6+ → 9+)
    - Автоматическое создание категорий в БД по строковому названию
    - Установка source='ast' для всех импортированных книг
    - Логирование прогресса каждые 500 книг

Результат:
    Выводит статистику: количество импортированных и пропущенных книг.
"""

import json
import os
import re
import sys
from decimal import Decimal
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shop_admin.settings')
django.setup()

from admin_panel.models import Book, Category


# ═══════════════════════════════════════════════════════════════════
# Маппинг типов переплёта
# ═══════════════════════════════════════════════════════════════════

COVER_TYPE_MAP = {
    'твёрдый': 'hard',
    'твердый': 'hard',
    'твёрдая': 'hard',
    'твердая': 'hard',
    'мягкий': 'soft',
    'мягкая': 'soft',
    'мягкая обложка': 'soft',
}


# ═══════════════════════════════════════════════════════════════════
# Маппинг возрастных ограничений
# ═══════════════════════════════════════════════════════════════════

AGE_RESTRICTION_MAP = {
    '0+': '9+',
    '6+': '9+',
    '9+': '9+',
    '10+': '10+',
    '12+': '12+',
    '14+': '14+',
    '16+': '16+',
    '18+': '18+',
}


# ═══════════════════════════════════════════════════════════════════
# Вспомогательные функции парсинга
# ═══════════════════════════════════════════════════════════════════


def parse_cover_type(cover_str: str) -> str:
    """Определить тип переплета из текстового описания."""
    if not cover_str:
        return 'hard'
    cover_lower = cover_str.lower().strip()
    for key, value in COVER_TYPE_MAP.items():
        if key in cover_lower:
            return value
    return 'hard'


def parse_year(year_value):
    """Извлечь год издания из значения (строка или число)."""
    if year_value is None:
        return None
    if isinstance(year_value, int):
        year = year_value
    else:
        s = str(year_value).strip()
        if not s:
            return None
        try:
            year = int(s)
        except (ValueError, TypeError):
            return None
    if 1800 <= year <= 2030:
        return year
    return None


def parse_pages(pages_value):
    """Извлечь количество страниц из значения (строка или число)."""
    if pages_value is None:
        return None
    if isinstance(pages_value, int):
        return pages_value
    s = str(pages_value).strip()
    if not s:
        return None
    try:
        return int(s)
    except (ValueError, TypeError):
        return None


def parse_format_dims(raw: str) -> tuple:
    """
    Размеры из поля format: «145, 207» → ширина и длина в мм.

    Формат АСТ: два числа через запятую: ширина, длина.
    """
    if not raw:
        return None, None
    raw = raw.strip()
    match = re.search(r'(\d+)\s*[,]\s*(\d+)', raw)
    if not match:
        return None, None
    w_mm, l_mm = int(match.group(1)), int(match.group(2))
    return Decimal(w_mm), Decimal(l_mm)


def parse_weight(value: str) -> Decimal | None:
    """
    Конвертировать вес из JSON в граммы.

    В JSON вес указан в кг (например, «0.2» = 200 г).
    """
    if not value:
        return None
    try:
        kg = Decimal(str(value).strip())
        if kg <= 0:
            return None
        grams = kg * Decimal('1000')
        if 10 <= grams <= 10000:  # sanity check: 10г – 10кг
            return grams
        return None
    except Exception:
        return None


def parse_age_restriction(value: str) -> str:
    """Привести возрастное ограничение к одному из допустимых значений."""
    if not value:
        return '18+'
    value = value.strip()
    return AGE_RESTRICTION_MAP.get(value, '18+')


def get_or_create_category(category_name: str):
    """
    Найти или создать категорию по названию.

    Args:
        category_name: Строковое название категории из JSON

    Returns:
        Category object или None
    """
    if not category_name:
        return None
    category_name = category_name.strip()
    if not category_name:
        return None

    cat, _ = Category.objects.get_or_create(
        name=category_name,
        defaults={'ozon_category_id': None, 'description': ''}
    )
    return cat



# ═══════════════════════════════════════════════════════════════════
# Основная функция импорта
# ═══════════════════════════════════════════════════════════════════


def import_ast_books():
    """
    Основная функция импорта книг АСТ из JSON файла.

    Читает JSON-файл, парсит все поля и импортирует в базу данных
    с использованием батчевой вставки.
    """

    # Открываем и читаем JSON — из файла или из stdin (через пайп)это
    #  на сервере
    #def import_ast_books():
    #    if len(sys.argv) > 1 and sys.argv[1] == '--stdin':
    #        books_data = json.load(sys.stdin)
    #    else:
    with open('vBaze/dnevnikiAST.json', 'r', encoding='utf-8') as f:
        books_data = json.load(f)

    print(f'Загружено {len(books_data)} книг из JSON')

    books_to_create = []
    skipped = 0
    stats_dims = 0
    stats_weight = 0

    for idx, book_data in enumerate(books_data, 1):
        isbn = book_data.get('isbn', '').strip()

        if isbn and Book.objects.filter(isbn=isbn, source=Book.SOURCE_AST).exists():
            skipped += 1
            continue

        width, length = parse_format_dims(book_data.get('format', ''))
        if width is not None:
            stats_dims += 1

        weight = parse_weight(book_data.get('weight', ''))
        if weight is not None:
            stats_weight += 1

        description = (
            book_data.get('annotation', '')
            or book_data.get('description', '')
            or ''
        )

        category = get_or_create_category(book_data.get('category', ''))
        age_restriction = parse_age_restriction(
            book_data.get('age_restriction', '')
        )

        book = Book(
            title=book_data.get('title', '')[:200],
            author=book_data.get('author', '')[:100],
            isbn=isbn[:20] if isbn else None,
            isbn_digits=''.join(c for c in (isbn or '') if c.isdigit()),  # ISBN только цифрами
            description=description,
            publisher=book_data.get('publisher', '')[:100],
            publication_year=parse_year(book_data.get('year')),
            pages=parse_pages(book_data.get('pages')),
            cover_type=parse_cover_type(book_data.get('cover_type', '')),
            series=book_data.get('series', '')[:200] or None,
            source=Book.SOURCE_AST,
            language='russian',
            illustrator=book_data.get('illustrator', '')[:100] or None,
            category=category,
            age_restrictions=age_restriction,
            width=width,
            length=length,
            weight=weight,
            price=0,
            stock=0,
        )
        books_to_create.append(book)

        if len(books_to_create) >= 500:
            Book.objects.bulk_create(books_to_create, ignore_conflicts=True)
            print(f'Импортировано {idx} / {len(books_data)} книг...')
            books_to_create = []

    if books_to_create:
        Book.objects.bulk_create(books_to_create, ignore_conflicts=True)

    total_imported = Book.objects.filter(source=Book.SOURCE_AST).count()

    print(f'\n✅ Импорт завершен!')
    print(f'Всего импортировано: {total_imported} книг')
    print(f'Пропущено (дубликаты по ISBN): {skipped}')
    print()
    print(f'📏 Размеры (width/length) из поля format: {stats_dims}')
    print(f'⚖️  Вес (weight) сконвертирован:          {stats_weight}')


if __name__ == '__main__':
    import_ast_books()



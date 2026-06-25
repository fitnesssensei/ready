"""
Скрипт импорта книг из JSON файла в базу данных.

Импортирует книги из файла JSON/xxxx_libex.json
в таблицу admin_panel_book с источником 'eksmo'.

Использование:
    python import_books.py

Особенности:
    - Батчевая вставка по 500 книг для оптимизации производительности
    - Пропуск дубликатов по ISBN + источник (только для книг с ISBN)
    - Книги без ISBN добавляются без проверки на дубликаты
    - Автоматическое определение типа переплета из текстового описания
    - Парсинг года издания и количества страниц из строк
    - Парсинг размеров (width/length/height) из полей format/thickness
      или из текста аннотации (например, «Размеры: 125x200x21 мм»)
    - Парсинг веса из аннотации (например, «Вес: 258 г», «Масса: 708 г»)
    - Установка source='eksmo' для всех импортированных книг
    - Логирование прогресса каждые 500 книг

Результат:
    Выводит статистику: количество импортированных и пропущенных книг,
    а также сколько размеров и веса удалось извлечь.
"""

import json
import os
import re
import sys
from decimal import Decimal
import django

CATEGORY_TO_GENRE = {
    'antic': 'Античная литература',
    'Артбук': 'artbook',        
    'Бизнес': 'business', 
    'Басни': 'fable',
    'Биография': 'biography',
    'Боевик, книга о войне': 'boevic',
    'Военное дело': 'military',
    'Графический роман': 'graphic_novel',
    'Дом и сад': 'home_garden',
    'Детективы, триллеры': 'detective',
    'Драматургия': 'drama',
    'Дошкольное развитие детей': 'early_childhood',
    'Другое': '',
    'Исторический роман': 'history',
    'Красота и здоровье': 'beauty_health',
    'Классики литературы': 'classic',
    'Комикс': 'comic',
    'Кулинария': 'cooking',
    'Литература античная и средних веков': 'antic',
    'Любовный роман, эротика': 'romance',
    'Манга': 'manga',
    'Манхва': 'manhwa',
    'Маньхуа': 'manhua',
    'Медицина': 'medicine',
    'Мемуары': 'memoirs',
    'Мистика': 'mystery',
    'Мемуары, биографии': 'memoirs',
    'Мифы, сказки, фольклор': 'epic_folklore',
    'Молодежная и подростковая литература (Young Adult)': 'young_adult',
    'Приключения, путешествия': 'adventure',
    'Публицистика': 'journalism',
    'Педагогика и логопедия': 'pedagogy',
    'Политика и политология': 'politics',
    'Пособие для вузов, ссузов, аспирантуры': 'university',
    'Пособие для изучения иностранных языков': 'foreign_language',
    'Пособие для подготовки к ЕГЭ': 'exam_prepEGE',
    'Пособие для подготовки к ОГЭ': 'exam_prepOGE',
    'Пособие для подготовки к итоговому тестированию и ВПР': 'exam_prepVPR',
    'Пособие для школы': 'school',
    'Поэзия': 'poetry',
    'Право и юриспруденция': 'law',
    'Приключения': 'adventure',
    'Проза': 'prose',
    'Психология': 'psychology',
    'Путешествия и туризм': 'travel',
    'Ранобэ': 'ranobe',
    'Религия': 'religion',
    'Сатира, юмор': 'satire',
    'Советские писатели': 'sovetsk',
    'Современная литература': 'modern',
    'Саморазвитие': 'self_development',
    'Словарь': 'dictionary',
    'Спорт': 'sports',
    'Триллер': 'thriller',
    'Ужасы, мистика': 'horror',
    'Фантастика': 'fantastic',
    'Фэнтези': 'fantasy',
    'Художественная': 'hudozhka',
    'Хобби и творчество': 'hobby_creativity',
    'Эзотерика и духовные практики': 'esoterica_spirituality',
    'Экономика и финансы': 'economics_finance',
    'Энциклопедия, справочник': 'encyclopedia_reference',
    'Эпос и фольклор': 'epic_folklore',
}

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shop_admin.settings')
django.setup()

from admin_panel.models import Book


# ═══════════════════════════════════════════════════════════════════
# Парсинг размеров и веса (перенесено из update_eksmo_dimensions.py)
# ═══════════════════════════════════════════════════════════════════


def parse_format_dims(raw: str) -> tuple[Decimal | None, Decimal | None]:
    """
    Размеры из поля format: «125x200 мм» → ширина и длина в мм.

    Args:
        raw: Строка вида «115x180 мм» или «125×200 мм»

    Returns:
        tuple (width, length) в мм, или (None, None) если не удалось распарсить
    """
    match = re.search(r'(\d+)\s*[xх×]\s*(\d+)', raw or '', re.IGNORECASE)
    if not match:
        return None, None
    w_mm, l_mm = int(match.group(1)), int(match.group(2))
    return Decimal(w_mm), Decimal(l_mm)


def parse_thickness_mm(raw: str) -> Decimal | None:
    """
    Толщина из поля thickness: «18 мм» → высота в мм.

    Args:
        raw: Строка вида «18 мм»

    Returns:
        Decimal (высота в мм) или None
    """
    match = re.search(r'(\d+)', raw or '')
    if not match:
        return None
    value = int(match.group(1))
    if value <= 0:
        return None
    return Decimal(value)


def parse_dims_from_annotation(annotation: str) -> tuple[Decimal | None, Decimal | None, Decimal | None]:
    """
    Извлечь размеры из текста аннотации.

    Ищет паттерн «Размеры: WxHxD мм» (3 размера) или «Размеры: WxH мм» (2 размера)
    в тексте аннотации.

    Args:
        annotation: Текст аннотации

    Returns:
        tuple (width, length, height) в мм, или (None, None, None)
    """
    if not annotation:
        return None, None, None

    # Ищем «Размеры: 267x214x21 мм» или «Размеры: 267х214х21 мм»
    match_3d = re.search(
        r'[Рр]азмер[а-я]*\s*[:]\s*'
        r'(\d+)\s*[xх×]\s*(\d+)\s*[xх×]\s*(\d+)',
        annotation,
    )
    if match_3d:
        return (
            Decimal(match_3d.group(1)),
            Decimal(match_3d.group(2)),
            Decimal(match_3d.group(3)),
        )

    # Ищем «Размеры: 125x200 мм» (только ширина и длина)
    match_2d = re.search(
        r'[Рр]азмер[а-я]*\s*[:]\s*'
        r'(\d+)\s*[xх×]\s*(\d+)',
        annotation,
    )
    if match_2d:
        return (
            Decimal(match_2d.group(1)),
            Decimal(match_2d.group(2)),
            None,
        )

    return None, None, None


def parse_weight_from_annotation(annotation: str) -> Decimal | None:
    """
    Извлечь вес из текста аннотации.

    Ищет паттерны «Масса: 708 г», «Вес: 258 г», «Вес книги: 258 гр.»
    в тексте аннотации.

    Args:
        annotation: Текст аннотации

    Returns:
        Decimal (вес в граммах) или None
    """
    if not annotation:
        return None

    match = re.search(
        r'(?:Масса|Вес|Вес книги|Weight)\s*[:]\s*'
        r'(\d+)\s*г(?:р)?',
        annotation,
    )
    if match:
        value = int(match.group(1))
        if 10 <= value <= 10000:  # sanity check: 10г – 10кг
            return Decimal(value)

    return None


# ═══════════════════════════════════════════════════════════════════
# Существующие функции парсинга (год, страницы, переплёт)
# ═══════════════════════════════════════════════════════════════════


def parse_cover_type(cover_str):
    """Определить тип переплета из текстового описания."""
    if not cover_str:
        return 'hard'
    cover_lower = cover_str.lower()
    if 'мягк' in cover_lower or 'обложка' in cover_lower:
        return 'soft'
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


# ═══════════════════════════════════════════════════════════════════
# Основная функция импорта
# ═══════════════════════════════════════════════════════════════════


def import_books():
    """
    Основная функция импорта книг из JSON файла.

    Читает JSON-файл, парсит все поля включая размеры (width/length/height)
    и вес книги, и импортирует в базу данных с использованием батчевой вставки.

    Размеры извлекаются (в порядке приоритета):
        1. Из полей format / thickness (если есть в JSON)
        2. Из текста аннотации (паттерны «Размеры: WxHxD мм» / «Размеры: WxH мм»)

    Вес извлекается из аннотации (паттерны «Масса: N г», «Вес: N г»).
    """

    # Открываем и читаем JSON — из файла или из stdin (через пайп)
    if len(sys.argv) > 1 and sys.argv[1] == '--stdin':
        books_data = json.load(sys.stdin)
    else:
        # Открываем и читаем JSON файл с книгами 
        with open('JSON/48000_clean.json', 'r', encoding='utf-8') as f:
            books_data = json.load(f)

    print(f'Загружено {len(books_data)} книг из JSON')

    books_to_create = []
    skipped = 0
    stats_dims_from_format = 0
    stats_dims_from_annotation = 0
    stats_weight_from_annotation = 0

    for idx, book_data in enumerate(books_data, 1):
        isbn = book_data.get('isbn', '').strip()

        if isbn and Book.objects.filter(isbn=isbn, source=Book.SOURCE_EKSMO).exists():
            skipped += 1
            continue

        # ── Парсинг размеров ──────────────────────────────────────
        # 1. Пробуем поля format/thickness (как в exmo_books.json)
        width, length = parse_format_dims(book_data.get('format', ''))
        height = parse_thickness_mm(book_data.get('thickness', ''))

        if width is not None:
            stats_dims_from_format += 1

        # 2. Если нет — пробуем извлечь из аннотации
        annotation = book_data.get('annotation', '') or book_data.get('description', '')
        if width is None:
            ann_w, ann_l, ann_h = parse_dims_from_annotation(annotation)
            if ann_w is not None:
                width, length, height = ann_w, ann_l, ann_h
                stats_dims_from_annotation += 1

        # ── Парсинг веса из аннотации ─────────────────────────────
        weight = parse_weight_from_annotation(annotation)
        if weight is not None:
            stats_weight_from_annotation += 1

        book = Book(
            title=book_data.get('title', '')[:200],
            author=book_data.get('author', '')[:100],
            isbn=isbn[:20] if isbn else None,
            isbn_digits=''.join(c for c in (isbn or '') if c.isdigit()),  # ISBN только цифрами

            description=annotation,
            publisher=book_data.get('publisher', '')[:100],
            #genre=book_data.get('category', '')[:100],
            genre=CATEGORY_TO_GENRE.get(book_data.get('category', '').strip().replace('\xa0', ' '), ''),
            
            publication_year=parse_year(book_data.get('year')),
            pages=parse_pages(book_data.get('pages')),
            cover_type=parse_cover_type(book_data.get('binding')),
            series=book_data.get('series', '')[:200] if book_data.get('series') else None,
            source=Book.SOURCE_EKSMO,
            language=book_data.get('language', 'Русский'),
            width=width,
            length=length,
            height=height,
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

    total_imported = Book.objects.filter(source=Book.SOURCE_EKSMO).count()

    print(f'\n\u2705 Импорт завершен!')
    print(f'Всего импортировано: {total_imported} книг')
    print(f'Пропущено (дубликаты по ISBN): {skipped}')
    print()
    print(f'\U0001f4cf Размеры (width/length/height):')
    print(f'   — из поля format/thickness: {stats_dims_from_format}')
    print(f'   — из текста аннотации:      {stats_dims_from_annotation}')
    print(f'\u2696\ufe0f Вес (weight) из аннотации:   {stats_weight_from_annotation}')


if __name__ == '__main__':
    import_books()


"""
Команда импорта каталога Эксмо из JSON в таблицу Book (source=eksmo).

Запуск:
    python manage.py import_eksmo_books
    python manage.py import_eksmo_books --update
    python manage.py import_eksmo_books --dry-run
    python manage.py import_eksmo_books --file /путь/к/файлу.json
"""

import json
import re
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from admin_panel.models import Book

# Путь к JSON по умолчанию (корень проекта / parsing / …)
DEFAULT_JSON = Path(__file__).resolve().parents[3] / 'parsing' / 'eksmo_books_mt_deduped.json'

# Сколько записей писать в БД за один запрос bulk_create / bulk_update
BATCH_SIZE = 500


def isbn_digits_only(raw: str) -> str:
    """
    Оставляет только цифры ISBN — для проверки длины и сопоставления при --update.
    Пример: «978-5-04-122320-5» → «9785041223205»
    """
    return ''.join(c for c in (raw or '') if c.isdigit())


def parse_isbn(raw: str) -> str | None:
    """
    ISBN сохраняем полностью, как в JSON — с дефисами.
    Проверяем только, что после удаления дефисов остаётся 10 или 13 цифр.
    """
    value = (raw or '').strip()
    if not value:
        return None

    digits = isbn_digits_only(value)
    if len(digits) not in (10, 13):
        return None

    # Обрезаем до max_length поля модели (20 символов)
    return value[:20]


def parse_cover(raw: str) -> str:
    """
    Тип переплёта для модели Book: 'hard' или 'soft'.
    В JSON приходит текст вида «Твердый переплет» / «Мягкая обложка».
    """
    text = raw or ''
    if 'Мягк' in text or 'мягк' in text:
        return 'soft'
    if 'Тверд' in text or 'тверд' in text:
        return 'hard'
    return 'hard'


def parse_int(raw) -> int | None:
    """Безопасно превращает строку из JSON в int (год, страницы)."""
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        return None


def parse_format_dims(raw: str) -> tuple[Decimal | None, Decimal | None]:
    """
    Размеры из поля format: «125x200 мм» → ширина и длина в см.
    """
    match = re.search(r'(\d+)\s*[xх×]\s*(\d+)', raw or '', re.IGNORECASE)
    if not match:
        return None, None
    w_mm, l_mm = int(match.group(1)), int(match.group(2))
    return Decimal(w_mm) / 10, Decimal(l_mm) / 10


def parse_thickness_cm(raw: str) -> Decimal | None:
    """
    Толщина из поля thickness: «21 мм» → высота в см (2.1).
    """
    match = re.search(r'(\d+)', raw or '')
    if not match:
        return None
    value = int(match.group(1))
    if value <= 0:
        return None
    return Decimal(value) / 10


def book_from_row(row: dict) -> Book | None:
    """
    Собирает объект Book из одной записи JSON.
    Возвращает None, если ISBN отсутствует или невалиден.
    """
    isbn = parse_isbn(row.get('isbn', ''))
    if not isbn:
        return None

    width, length = parse_format_dims(row.get('format', ''))
    height = parse_thickness_cm(row.get('thickness', ''))

    return Book(
        source=Book.SOURCE_EKSMO,
        title=(row.get('title') or '')[:200],
        author=(row.get('author') or '')[:100],
        author_oblozh=(row.get('author') or '')[:100],
        publisher=(row.get('publisher') or '')[:100],
        series=(row.get('series') or '')[:200] or None,
        publication_year=parse_int(row.get('year')),
        cover_type=parse_cover(row.get('cover', '')),
        pages=parse_int(row.get('pages')),
        description=row.get('description') or '',
        isbn=isbn,
        width=width,
        length=length,
        height=height,
        price=Decimal('0'),
        stock=0,
        photos=[],
    )


def build_existing_by_isbn_digits(source: str) -> dict[str, Book]:
    """
    Словарь «только цифры ISBN» → запись в БД.
    Нужен для --update: в БД могли остаться ISBN без дефисов, в JSON — с дефисами.
    """
    result: dict[str, Book] = {}
    for book in Book.objects.filter(source=source).exclude(isbn__isnull=True).exclude(isbn=''):
        key = isbn_digits_only(book.isbn)
        if key:
            result[key] = book
    return result


class Command(BaseCommand):
    help = 'Импорт книг из parsing/eksmo_books_mt_deduped.json в таблицу Book (каталог Эксмо)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default=str(DEFAULT_JSON),
            help='Путь к JSON-файлу',
        )
        parser.add_argument(
            '--update',
            action='store_true',
            help='Обновить существующие записи по ISBN (сопоставление по цифрам, сохранение с дефисами)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Только проверить данные, без записи в БД',
        )

    def handle(self, *args, **options):
        json_path = Path(options['file'])

        # --- Чтение файла ---
        if not json_path.exists():
            self.stderr.write(self.style.ERROR(f'Файл не найден: {json_path}'))
            return

        with json_path.open(encoding='utf-8') as f:
            rows = json.load(f)

        if not isinstance(rows, list):
            self.stderr.write(self.style.ERROR('JSON должен быть массивом объектов'))
            return

        # --- Преобразование строк JSON в объекты Book ---
        books: list[Book] = []
        skipped = 0
        for row in rows:
            book = book_from_row(row)
            if book is None:
                skipped += 1
                continue
            books.append(book)

        self.stdout.write(
            f'Записей в файле: {len(rows)}, к импорту: {len(books)}, пропущено: {skipped}'
        )

        if options['dry_run']:
            self.stdout.write(self.style.WARNING('Dry-run: в БД ничего не записано'))
            return

        # Поля, которые обновляем при --update (включая isbn с дефисами)
        update_fields = [
            'source',
            'isbn',
            'title',
            'author',
            'author_oblozh',
            'publisher',
            'series',
            'publication_year',
            'cover_type',
            'pages',
            'description',
            'width',
            'length',
            'height',
        ]

        with transaction.atomic():
            if options['update']:
                # Ищем уже загруженные книги Эксмо по цифрам ISBN
                existing = build_existing_by_isbn_digits(Book.SOURCE_EKSMO)
                to_create: list[Book] = []
                to_update: list[Book] = []

                for book in books:
                    key = isbn_digits_only(book.isbn)
                    if key in existing:
                        obj = existing[key]
                        obj.source = Book.SOURCE_EKSMO
                        for field in update_fields:
                            setattr(obj, field, getattr(book, field))
                        to_update.append(obj)
                    else:
                        to_create.append(book)

                if to_create:
                    Book.objects.bulk_create(to_create, batch_size=BATCH_SIZE)
                if to_update:
                    Book.objects.bulk_update(to_update, update_fields, batch_size=BATCH_SIZE)

                created, updated = len(to_create), len(to_update)
            else:
                # Первичный импорт: пропускаем дубликаты по уникальному (isbn, source)
                before = Book.objects.filter(source=Book.SOURCE_EKSMO).count()
                Book.objects.bulk_create(books, ignore_conflicts=True, batch_size=BATCH_SIZE)
                after = Book.objects.filter(source=Book.SOURCE_EKSMO).count()
                created = after - before
                updated = len(books) - created

        self.stdout.write(
            self.style.SUCCESS(
                f'Готово: создано {created}, обновлено {updated}, '
                f'каталог Эксмо в БД: {Book.objects.filter(source=Book.SOURCE_EKSMO).count()}'
            )
        )

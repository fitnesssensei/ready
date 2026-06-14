"""
Команда для заполнения/обновления размеров (width/length/height)
у существующих книг Эксмо, у которых они отсутствуют.

Берёт данные из JSON-файла каталога Эксмо, парсит поля:
    format="115x180 мм"     → width=11.5, length=18.0 см
    thickness="18 мм"       → height=1.8 см

Запуск:
    python manage.py update_eksmo_dimensions
    python manage.py update_eksmo_dimensions --file vBaze/exmo_books.json
    python manage.py update_eksmo_dimensions --dry-run
    python manage.py update_eksmo_dimensions --force
"""

import json
import re
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db.models import Q

from admin_panel.models import Book


def parse_thickness_cm(raw: str) -> Decimal | None:
    """Толщина из поля thickness: «21 мм» → высота в см (2.1)."""
    match = re.search(r'(\d+)', raw or '')
    if not match:
        return None
    value = int(match.group(1))
    if value <= 0:
        return None
    return Decimal(value) / 10


def isbn_digits_only(raw: str) -> str:
    """Оставляет только цифры ISBN для сопоставления."""
    return ''.join(c for c in (raw or '') if c.isdigit())


def parse_format_dims(raw: str) -> tuple[Decimal | None, Decimal | None]:
    """Размеры из поля format: «125x200 мм» → ширина и длина в см."""
    match = re.search(r'(\d+)\s*[xх×]\s*(\d+)', raw or '', re.IGNORECASE)
    if not match:
        return None, None
    w_mm, l_mm = int(match.group(1)), int(match.group(2))
    return Decimal(w_mm) / 10, Decimal(l_mm) / 10


class Command(BaseCommand):
    help = 'Обновление размеров (width/length/height) для книг Эксмо из JSON каталога'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default=str(Path(__file__).resolve().parents[3] / 'vBaze' / 'exmo_books.json'),
            help='Путь к JSON-файлу каталога Эксмо',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Только показать, что будет обновлено, без записи в БД',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Обновлять размеры даже если они уже заполнены',
        )

    def handle(self, *args, **options):
        json_path = Path(options['file'])
        dry_run = options['dry_run']
        force = options['force']

        # 1. Загрузка JSON
        if not json_path.exists():
            self.stderr.write(self.style.ERROR(f'Файл не найден: {json_path}'))
            return

        with json_path.open(encoding='utf-8') as f:
            rows = json.load(f)

        self.stdout.write(f'Загружено {len(rows)} записей из {json_path.name}')

        # 2. Сбор данных о размерах из JSON (isbn_digits -> (width, length, height))
        json_dims: dict[str, tuple] = {}
        skipped_no_isbn = 0
        skipped_no_dims = 0

        for row in rows:
            isbn_key = isbn_digits_only(row.get('isbn', ''))
            if not isbn_key:
                skipped_no_isbn += 1
                continue

            width, length = parse_format_dims(row.get('format', ''))
            height = parse_thickness_cm(row.get('thickness', ''))

            if width is None and length is None and height is None:
                skipped_no_dims += 1
                continue

            json_dims[isbn_key] = (width, length, height)

        self.stdout.write(
            f'  — с ISBN: {len(rows) - skipped_no_isbn}, '
            f'без ISBN: {skipped_no_isbn}, '
            f'без размеров: {skipped_no_dims}'
        )
        self.stdout.write(f'  — книг с размерами в JSON: {len(json_dims)}')

        if not json_dims:
            self.stdout.write(self.style.WARNING('Нет данных для обновления.'))
            return

        # 3. Поиск книг в БД
        qs = Book.objects.filter(source=Book.SOURCE_EKSMO).exclude(isbn__isnull=True).exclude(isbn='')

        if not force:
            qs = qs.filter(
                Q(width__isnull=True) | Q(length__isnull=True) | Q(height__isnull=True)
            )

        # Индекс: isbn_digits -> Book
        db_books: dict[str, Book] = {}
        for book in qs.iterator():
            key = isbn_digits_only(book.isbn)
            if key:
                db_books[key] = book

        self.stdout.write(f'  — книг в БД, подходящих под обновление: {len(db_books)}')

        # 4. Сопоставление
        to_update: list[Book] = []
        matched = 0
        not_found_in_json = 0

        for isbn_key, book in db_books.items():
            dims = json_dims.get(isbn_key)
            if dims is None:
                not_found_in_json += 1
                continue

            width, length, height = dims
            changed = False

            if book.width is None and width is not None:
                book.width = width
                changed = True
            if book.length is None and length is not None:
                book.length = length
                changed = True
            if book.height is None and height is not None:
                book.height = height
                changed = True

            if changed:
                to_update.append(book)
                matched += 1

        self.stdout.write(
            f'  — найдено в JSON: {matched}, нет в JSON: {not_found_in_json}'
        )

        if not to_update:
            self.stdout.write(self.style.SUCCESS(
                'Все книги уже имеют размеры. Ничего не обновлено.'
            ))
            return

        self.stdout.write(f'\nБудет обновлено {len(to_update)} книг(и)')

        if dry_run:
            self.stdout.write(self.style.WARNING('Dry-run: изменения не применены'))
            self._print_sample(to_update[:5])
            return

        # 5. Батчевое обновление
        batch_size = 500
        updated_total = 0
        for i in range(0, len(to_update), batch_size):
            batch = to_update[i:i + batch_size]
            Book.objects.bulk_update(batch, ['width', 'length', 'height'],
                                     batch_size=batch_size)
            updated_total += len(batch)
            self.stdout.write(f'  Обновлено {updated_total} / {len(to_update)}')

        self.stdout.write(
            self.style.SUCCESS(f'\nГотово: обновлено {updated_total} книг(и)')
        )

    def _print_sample(self, sample: list[Book]):
        """Показывает несколько примеров того, что будет обновлено."""
        if not sample:
            return
        self.stdout.write('\nПримеры:')
        for book in sample:
            self.stdout.write(
                f'  [ID={book.id}] {book.title[:50]}... '
                f'→ width={book.width}, length={book.length}, '
                f'height={book.height}'
            )

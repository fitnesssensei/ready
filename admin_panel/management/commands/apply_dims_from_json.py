"""
Management-команда: заполняет размеры книг из compact JSON-файла.

Берёт файл vBaze/dims_only.json (1.4 МБ), где ключ = ISBN (только цифры),
значение = {w, l, h} в мм, и обновляет поля width/length/height у книг
в БД, у которых эти поля пустые.

Запуск:
    python manage.py apply_dims_from_json
    python manage.py apply_dims_from_json --file vBaze/dims_only.json
    python manage.py apply_dims_from_json --dry-run
    python manage.py apply_dims_from_json --force
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db.models import Q

from admin_panel.models import Book


def isbn_digits(raw: str) -> str:
    return ''.join(c for c in (raw or '') if c.isdigit())


class Command(BaseCommand):
    help = 'Заполняет размеры книг (width/length/height) из compact JSON файла'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default=str(Path(__file__).resolve().parents[3] / 'vBaze' / 'dims_only.json'),
            help='Путь к JSON-файлу с размерами',
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
            dims_data = json.load(f)

        self.stdout.write(f'Загружено {len(dims_data)} ISBN с размерами из {json_path.name}')

        if not dims_data:
            self.stdout.write(self.style.WARNING('Нет данных для обновления.'))
            return

        # 2. Поиск книг в БД
        qs = Book.objects.filter(source=Book.SOURCE_EKSMO).exclude(
            isbn__isnull=True
        ).exclude(isbn='')

        if not force:
            qs = qs.filter(
                Q(width__isnull=True) | Q(length__isnull=True) | Q(height__isnull=True)
            )

        # Индекс: isbn_digits -> Book
        db_books: dict[str, Book] = {}
        for book in qs.iterator():
            key = isbn_digits(book.isbn)
            if key:
                db_books[key] = book

        self.stdout.write(f'  — книг в БД, подходящих под обновление: {len(db_books)}')

        if not db_books:
            self.stdout.write(self.style.SUCCESS('Все книги уже имеют размеры. Ничего не обновлено.'))
            return

        # 3. Сопоставление
        to_update: list[Book] = []
        matched = 0
        not_found_in_json = 0

        for isbn_key, book in db_books.items():
            dims = dims_data.get(isbn_key)
            if dims is None:
                not_found_in_json += 1
                continue

            changed = False

            if book.width is None and 'w' in dims:
                book.width = dims['w']
                changed = True
            if book.length is None and 'l' in dims:
                book.length = dims['l']
                changed = True
            if book.height is None and 'h' in dims:
                book.height = dims['h']
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

        # 4. Батчевое обновление
        batch_size = 500
        updated_total = 0
        for i in range(0, len(to_update), batch_size):
            batch = to_update[i:i + batch_size]
            Book.objects.bulk_update(
                batch, ['width', 'length', 'height'], batch_size=batch_size
            )
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
                f'  [ID={book.id}] ISBN={book.isbn} {book.title[:50]}... '
                f'→ width={book.width}, length={book.length}, '
                f'height={book.height}'
            )

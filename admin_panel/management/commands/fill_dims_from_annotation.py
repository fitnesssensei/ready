"""
Заполняет размеры (width/length/height) из текста аннотации (description)
для книг, у которых размеры пустые.

Ищет паттерны в description:
  - «Размеры: 267x214x21 мм» (3 размера)
  - «Размеры: 125x200 мм» (2 размера, без высоты)
  - «Размер: 297x226x12 мм»

Запуск:
    python manage.py fill_dims_from_annotation
    python manage.py fill_dims_from_annotation --source eksmo
    python manage.py fill_dims_from_annotation --source manual
    python manage.py fill_dims_from_annotation --all
    python manage.py fill_dims_from_annotation --dry-run
"""

import re
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand
from django.db.models import Q

from admin_panel.models import Book


def parse_dims_from_annotation(annotation: str) -> tuple[Decimal | None, Decimal | None, Decimal | None]:
    """
    Извлечь размеры из текста аннотации.

    Ищет паттерн «Размеры: WxHxD мм» (3 размера) или «Размеры: WxH мм» (2 размера)
    в тексте аннотации.
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
        try:
            return (
                Decimal(match_3d.group(1)),
                Decimal(match_3d.group(2)),
                Decimal(match_3d.group(3)),
            )
        except InvalidOperation:
            pass

    # Ищем «Размеры: 125x200 мм» (только ширина и длина)
    match_2d = re.search(
        r'[Рр]азмер[а-я]*\s*[:]\s*'
        r'(\d+)\s*[xх×]\s*(\d+)',
        annotation,
    )
    if match_2d:
        try:
            return (
                Decimal(match_2d.group(1)),
                Decimal(match_2d.group(2)),
                None,
            )
        except InvalidOperation:
            pass

    return None, None, None


class Command(BaseCommand):
    help = 'Заполняет размеры книг из текста аннотации (description)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            type=str,
            choices=['eksmo', 'manual'],
            default=None,
            help='Источник книг: eksmo или manual (по умолчанию все)'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Проверить все книги (даже с уже заполненными размерами)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Только показать, что будет обновлено, без записи в БД',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        source = options['source']
        check_all = options['all']

        # 1. Выбираем книги
        qs = Book.objects.exclude(description='').exclude(description__isnull=True)

        if source:
            qs = qs.filter(source=source)

        if not check_all:
            qs = qs.filter(
                Q(width__isnull=True) | Q(length__isnull=True) | Q(height__isnull=True)
            )

        total = qs.count()
        self.stdout.write(f'Найдено книг с описанием для проверки: {total}')

        if total == 0:
            self.stdout.write(self.style.SUCCESS('Нет книг для обновления.'))
            return

        # 2. Проходим по книгам, парсим размеры
        to_update: list[Book] = []
        found_3d = 0
        found_2d = 0
        not_found = 0

        for book in qs.iterator():
            w, l, h = parse_dims_from_annotation(book.description)

            if w is None and l is None and h is None:
                not_found += 1
                continue

            changed = False

            if w is not None and book.width is None:
                book.width = w
                changed = True
            if l is not None and book.length is None:
                book.length = l
                changed = True
            if h is not None and book.height is None:
                book.height = h
                changed = True

            if changed:
                to_update.append(book)
                if h is not None:
                    found_3d += 1
                else:
                    found_2d += 1

        self.stdout.write(f'  — найдено 3 размера (w+l+h): {found_3d}')
        self.stdout.write(f'  — найдено 2 размера (w+l):   {found_2d}')
        self.stdout.write(f'  — не найдено в аннотации:     {not_found}')

        if not to_update:
            self.stdout.write(self.style.SUCCESS('Нет книг для обновления.'))
            return

        self.stdout.write(f'\nБудет обновлено {len(to_update)} книг(и)')

        if dry_run:
            self.stdout.write(self.style.WARNING('Dry-run: изменения не применены'))
            self._print_sample(to_update[:5])
            return

        # 3. Батчевое обновление
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
        if not sample:
            return
        self.stdout.write('\nПримеры найденных размеров:')
        for book in sample:
            self.stdout.write(
                f'  [ID={book.id}] {book.title[:50]}... '
                f'→ width={book.width}, length={book.length}, height={book.height}'
            )

"""
Конвертирует существующие размеры книг из см → мм.

До этой команды размеры (width/length/height) сохранялись в сантиметрах,
но поля модели всегда подразумевали миллиметры.
Команда умножает существующие значения на 10.

Запуск:
    python manage.py convert_dims_to_mm
    python manage.py convert_dims_to_mm --dry-run
"""

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db.models import Q

from admin_panel.models import Book

BATCH_SIZE = 500


class Command(BaseCommand):
    help = 'Конвертирует размеры книг из см → мм (умножает width/length/height на 10)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Только показать, что будет обновлено, без записи в БД',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        qs = Book.objects.filter(
            Q(width__isnull=False) | Q(length__isnull=False) | Q(height__isnull=False)
        )

        total = qs.count()
        if total == 0:
            self.stdout.write(self.style.WARNING('Нет книг с размерами для конвертации.'))
            return

        self.stdout.write(f'Найдено книг с размерами: {total}')

        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'Dry-run: будет обновлено {total} книг(и)')
            )
            return

        # Конвертируем и обновляем батчами
        to_update: list[Book] = []
        updated_total = 0

        for book in qs.iterator():
            for field in ('width', 'length', 'height'):
                val = getattr(book, field, None)
                if val is not None:
                    setattr(book, field, val * Decimal('10'))
            to_update.append(book)

            if len(to_update) >= BATCH_SIZE:
                Book.objects.bulk_update(to_update, ['width', 'length', 'height'],
                                         batch_size=BATCH_SIZE)
                updated_total += len(to_update)
                self.stdout.write(f'  Обновлено {updated_total} / {total}')
                to_update = []

        if to_update:
            Book.objects.bulk_update(to_update, ['width', 'length', 'height'],
                                     batch_size=BATCH_SIZE)
            updated_total += len(to_update)

        self.stdout.write(
            self.style.SUCCESS(f'Готово: обновлено {updated_total} книг(и)')
        )




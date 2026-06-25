"""
Management-команда для заполнения поля isbn_digits у книг, у которых есть ISBN,
но isbn_digits пустой.

Запуск:
    python manage.py fill_isbn_digits
    python manage.py fill_isbn_digits --dry-run  # только показать сколько книг будет обновлено
"""
from django.core.management.base import BaseCommand
from admin_panel.models import Book


def normalize_isbn(value):
    return ''.join(c for c in (value or '') if c.isdigit())


class Command(BaseCommand):
    help = 'Заполняет isbn_digits для книг с ISBN, у которых isbn_digits пустой'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Только показать количество, без записи в БД',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        queryset = Book.objects.filter(
            isbn_digits=''
        ).exclude(
            isbn__isnull=True
        ).exclude(
            isbn=''
        )

        total = queryset.count()

        if total == 0:
            self.stdout.write(self.style.SUCCESS('✅ Нет книг с пустым isbn_digits — всё ок!'))
            return

        if dry_run:
            self.stdout.write(f'📊 Будет обновлено: {total} книг')
            return

        batch_size = 1000
        updated = 0

        self.stdout.write(f'Обновляется {total} книг...')

        for book in queryset.iterator(chunk_size=batch_size):
            book.isbn_digits = normalize_isbn(book.isbn)
            book.save(update_fields=['isbn_digits'])
            updated += 1
            if updated % batch_size == 0:
                self.stdout.write(f'  Обновлено {updated} из {total}')

        self.stdout.write(self.style.SUCCESS(f'✅ Готово! Обновлено {updated} книг.'))

"""
Management-команда переноса локальных фото книг в Яндекс Object Storage.

Что делает:
1. Берёт книги, у которых в `Book.photos` есть относительные пути (`book_photos/...`).
2. Заливает файл из `MEDIA_ROOT` в бакет по детерминированному ключу
   `book_photos/<sku|id-pk>/<имя файла>` — повторный запуск перезапишет тот же объект.
3. Заменяет путь в `Book.photos` на публичную https-ссылку.
   Абсолютные ссылки (уже в облаке) пропускает, отсутствующие файлы считает
   и оставляет как есть — команда не падает из-за одного битого пути.

Запуск:
    python manage.py upload_book_photos --dry-run      # посчитать, ничего не меняя
    python manage.py upload_book_photos --limit 10     # пробная партия
    python manage.py upload_book_photos                # полный перенос
    python manage.py upload_book_photos --sku 978-5-04-123456-7
"""
import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from admin_panel import storage_s3
from admin_panel.models import Book


class Command(BaseCommand):
    help = (
        'Переносит локальные фото книг в Яндекс Object Storage '
        'и заменяет пути на публичные ссылки'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Только показать, что будет перенесено, без загрузки и записи в БД',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            help='Обработать не более N книг (0 — все)',
        )
        parser.add_argument(
            '--sku',
            action='append',
            default=[],
            help='Обработать только указанные артикулы (можно несколько раз)',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Размер порции чтения из БД и прогресса (по умолчанию 100)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        limit = options['limit']
        skus = options['sku']
        batch_size = options['batch_size'] or 100

        # Без флага и ключей команда молча ничего бы не сделала — лучше явная ошибка.
        if not storage_s3.is_enabled():
            raise CommandError(
                'Загрузка в Object Storage выключена: включите PHOTO_S3_ENABLED '
                'и заполните YC_S3_* в .env'
            )

        queryset = Book.objects.only('id', 'sku', 'photos').exclude(photos__isnull=True)
        if skus:
            queryset = queryset.filter(sku__in=skus)
        queryset = queryset.order_by('id')

        stats = {'books': 0, 'photos': 0, 'updated': 0, 'cloud': 0,
                 'missing': 0, 'errors': 0}

        # Постранично по id, без server-side курсора (.iterator()): на некоторых
        # конфигурациях PostgreSQL/pgbouncer именованные курсоры «исчезают»
        # между чанками (psycopg2.errors.InvalidCursorName).
        last_id = 0
        while True:
            batch = list(queryset.filter(id__gt=last_id)[:batch_size])
            if not batch:
                break

            for book in batch:
                last_id = book.id

                if not book.photos:
                    continue
                if limit and stats['books'] >= limit:
                    break

                stats['books'] += 1
                new_photos, changed = self._process_book(book, stats, dry_run)

                if changed:
                    stats['updated'] += 1
                    if not dry_run:
                        book.photos = new_photos
                        book.save(update_fields=['photos'])

                if stats['books'] % batch_size == 0:
                    self.stdout.write(f'  ... обработано книг: {stats["books"]}')

            if limit and stats['books'] >= limit:
                break

        self._report(stats, dry_run)

    def _process_book(self, book, stats, dry_run):
        """Переносит фото одной книги. Возвращает (новый список, были ли изменения)."""
        new_photos = []
        changed = False

        for photo in book.photos:
            if not photo:
                continue

            # Уже облачная ссылка — второй раз не заливаем.
            if photo.startswith(('http://', 'https://')):
                stats['cloud'] += 1
                new_photos.append(photo)
                continue

            local_path = os.path.join(settings.MEDIA_ROOT, photo)
            if not os.path.exists(local_path):
                stats['missing'] += 1
                self.stderr.write(f'  ⚠ файл не найден: {photo}')
                new_photos.append(photo)
                continue

            try:
                # unique=False: имя файла сохраняем, чтобы повторный запуск был идемпотентным.
                key = storage_s3.build_object_key(book, photo, unique=False)
            except storage_s3.PhotoStorageError as exc:
                stats['errors'] += 1
                self.stderr.write(f'  ✗ {photo}: {exc}')
                new_photos.append(photo)
                continue

            if dry_run:
                stats['photos'] += 1
                changed = True
                self.stdout.write(f'  → {photo} → {key}')
                new_photos.append(photo)
                continue

            try:
                with open(local_path, 'rb') as file_obj:
                    url = storage_s3.upload_book_photo(file_obj, book, key=key)
            except (OSError, storage_s3.PhotoStorageError) as exc:
                # Одна ошибка не должна останавливать перенос остальных книг.
                stats['errors'] += 1
                self.stderr.write(f'  ✗ {photo}: {exc}')
                new_photos.append(photo)
                continue

            stats['photos'] += 1
            changed = True
            new_photos.append(url)

        return new_photos, changed

    def _report(self, stats, dry_run):
        """Итоговая сводка: цифры + подсказка, что делать при ошибках."""
        prefix = '📊 [dry-run] ' if dry_run else '✅ '
        self.stdout.write(
            prefix
            + f'книг: {stats["books"]}, '
            + f'фото к переносу: {stats["photos"]}, '
            + f'обновлено книг: {stats["updated"]}, '
            + f'уже в облаке: {stats["cloud"]}, '
            + f'нет файла: {stats["missing"]}, '
            + f'ошибок: {stats["errors"]}'
        )
        if stats['errors']:
            self.stdout.write(self.style.WARNING(
                'Часть фото не перенесена — исправьте ошибки выше и запустите команду ещё раз.'
            ))
        elif dry_run:
            self.stdout.write('Запустите без --dry-run, чтобы перенести файлы.')
        else:
            self.stdout.write(self.style.SUCCESS('Готово.'))

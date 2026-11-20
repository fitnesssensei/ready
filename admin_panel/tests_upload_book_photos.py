"""Тесты management-команды `upload_book_photos` (перенос локальных фото в облако).

Тесты на TestCase: нужна БД (книги реально создаются и сохраняются),
но сеть не используется — `upload_book_photo` подменяется моком.
MEDIA_ROOT указывает на временный каталог, поэтому файлы проекта не трогаются.

Проверяем:
- команда не работает при выключенном облаке;
- dry-run ничего не заливает и не пишет в БД;
- успешный перенос заменяет путь на публичную ссылку и идемпотентен;
- отсутствующий файл и ошибка загрузки не ломают прогон по остальным книгам;
- фильтры --limit и --sku.
"""

import os
import shutil
import tempfile
from io import StringIO
from unittest.mock import patch

from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings

from admin_panel.models import ManualBook
from admin_panel.storage_s3 import PhotoStorageError

CLOUD_BASE = 'https://storage.yandexcloud.net/gory-knig'


class UploadBookPhotosCommandTests(TestCase):
    """Перенос фото: замена путей, идемпотентность, обработка ошибок."""

    def setUp(self):
        # Изолируем медиа: команда читает файлы только из временного каталога.
        self.media_root = tempfile.mkdtemp(prefix='photos-test-')
        self.addCleanup(shutil.rmtree, self.media_root, ignore_errors=True)
        self.override = override_settings(MEDIA_ROOT=self.media_root, MEDIA_URL='/media/')
        self.override.enable()
        self.addCleanup(self.override.disable)

    def _make_local_photo(self, relative_path):
        """Создаёт локальный файл внутри временного MEDIA_ROOT."""
        full_path = os.path.join(self.media_root, relative_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'wb') as fh:
            fh.write(b'\xff\xd8\xff\xe0test')
        return relative_path

    def _make_book(self, sku, photos):
        return ManualBook.objects.create(sku=sku, title=f'Книга {sku}', photos=photos)

    def _run(self, *args, **kwargs):
        """Запуск команды с перехватом вывода."""
        out, err = StringIO(), StringIO()
        call_command('upload_book_photos', *args, stdout=out, stderr=err, **kwargs)
        return out.getvalue(), err.getvalue()

    def test_command_requires_enabled_cloud(self):
        with patch('admin_panel.storage_s3.is_enabled', return_value=False):
            with self.assertRaises(CommandError):
                self._run()

    def test_dry_run_does_not_upload_or_save(self):
        photo = self._make_local_photo('book_photos/01.jpg')
        book = self._make_book('T-1', [photo])

        with patch('admin_panel.storage_s3.is_enabled', return_value=True), \
                patch('admin_panel.storage_s3.upload_book_photo') as upload:
            out, _ = self._run('--dry-run')

        book.refresh_from_db()
        upload.assert_not_called()
        self.assertEqual(book.photos, [photo])
        self.assertIn('book_photos/T-1/01.jpg', out)  # ключ показан для проверки

    def test_uploads_and_replaces_path_with_url(self):
        photo = self._make_local_photo('book_photos/01.jpg')
        book = self._make_book('T-1', [photo])
        url = f'{CLOUD_BASE}/book_photos/T-1/01.jpg'

        with patch('admin_panel.storage_s3.is_enabled', return_value=True), \
                patch('admin_panel.storage_s3.upload_book_photo', return_value=url) as upload:
            self._run()

        book.refresh_from_db()
        self.assertEqual(book.photos, [url])
        self.assertEqual(upload.call_args.kwargs['key'], 'book_photos/T-1/01.jpg')

    def test_missing_local_file_is_skipped(self):
        book = self._make_book('T-2', ['book_photos/нет-такого.jpg'])

        with patch('admin_panel.storage_s3.is_enabled', return_value=True), \
                patch('admin_panel.storage_s3.upload_book_photo') as upload:
            _, err = self._run()

        book.refresh_from_db()
        upload.assert_not_called()
        self.assertEqual(book.photos, ['book_photos/нет-такого.jpg'])
        self.assertIn('файл не найден', err)

    def test_cloud_photo_is_not_uploaded_again(self):
        url = f'{CLOUD_BASE}/book_photos/T-3/01.jpg'
        book = self._make_book('T-3', [url])

        with patch('admin_panel.storage_s3.is_enabled', return_value=True), \
                patch('admin_panel.storage_s3.upload_book_photo') as upload:
            self._run()

        book.refresh_from_db()
        upload.assert_not_called()
        self.assertEqual(book.photos, [url])

    def test_second_run_is_idempotent(self):
        photo = self._make_local_photo('book_photos/02.jpg')
        book = self._make_book('T-4', [photo])
        url = f'{CLOUD_BASE}/book_photos/T-4/02.jpg'

        with patch('admin_panel.storage_s3.is_enabled', return_value=True), \
                patch('admin_panel.storage_s3.upload_book_photo', return_value=url) as upload:
            self._run()
            # Второй прогон: путей больше нет, заливать нечего.
            self._run()

        book.refresh_from_db()
        self.assertEqual(upload.call_count, 1)
        self.assertEqual(book.photos, [url])

    def test_upload_error_keeps_path_and_continues(self):
        broken = self._make_local_photo('book_photos/broken.jpg')
        good = self._make_local_photo('book_photos/good.jpg')
        book_broken = self._make_book('T-5', [broken])
        book_good = self._make_book('T-6', [good])
        good_url = f'{CLOUD_BASE}/book_photos/T-6/good.jpg'

        def fake_upload(file_obj, book, key=None):
            if book.sku == 'T-5':
                raise PhotoStorageError('403 AccessDenied')
            return good_url

        with patch('admin_panel.storage_s3.is_enabled', return_value=True), \
                patch('admin_panel.storage_s3.upload_book_photo', side_effect=fake_upload):
            _, err = self._run()

        book_broken.refresh_from_db()
        book_good.refresh_from_db()
        # Ошибка одной книги не мешает переносу остальных.
        self.assertEqual(book_broken.photos, [broken])
        self.assertEqual(book_good.photos, [good_url])
        self.assertIn('AccessDenied', err)

    def test_limit_option_processes_only_first_books(self):
        first = self._make_local_photo('book_photos/a.jpg')
        second = self._make_local_photo('book_photos/b.jpg')
        self._make_book('T-7', [first])
        self._make_book('T-8', [second])

        with patch('admin_panel.storage_s3.is_enabled', return_value=True), \
                patch('admin_panel.storage_s3.upload_book_photo',
                      return_value=f'{CLOUD_BASE}/x.jpg') as upload:
            self._run('--limit', 1)

        self.assertEqual(upload.call_count, 1)

    def test_sku_filter(self):
        first = self._make_local_photo('book_photos/a.jpg')
        second = self._make_local_photo('book_photos/b.jpg')
        self._make_book('T-9', [first])
        self._make_book('T-10', [second])

        with patch('admin_panel.storage_s3.is_enabled', return_value=True), \
                patch('admin_panel.storage_s3.upload_book_photo',
                      return_value=f'{CLOUD_BASE}/x.jpg') as upload:
            self._run(sku=['T-10'])

        self.assertEqual(upload.call_count, 1)
        uploaded_book = upload.call_args.args[1]
        self.assertEqual(uploaded_book.sku, 'T-10')

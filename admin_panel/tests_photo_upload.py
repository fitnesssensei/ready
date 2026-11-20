"""Тесты сохранения фото книги из админки (`BaseBookAdmin.save_model`).

Проверяем сквозной сценарий «админка → фото»:
- при включённом облаке в `Book.photos` попадает публичная https-ссылка;
- папка строится по уже сохранённой книге (pk есть);
- при ошибке облака или выключенном флаге файл сохраняется локально,
  а администратор видит предупреждение;
- без новых файлов в облако не ходим и лишний раз книгу не сохраняем;
- лимит 10 фото соблюдается ДО загрузки (без «мусора» в бакете).

База данных нужна: `Book` при создании обращается к категории по умолчанию,
а админка делает реальные `save()`. Сеть не используется — облако замокано.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase

from admin_panel.admin import ManualBookAdmin
from admin_panel.models import ManualBook
from admin_panel.storage_s3 import PhotoStorageError

CLOUD_URL = 'https://storage.yandexcloud.net/gory-knig/book_photos/T-1/abc.jpg'


def make_request(user, files=None):
    """POST-запрос админки с файлами и рабочим хранилищем сообщений.

    Файлы передаём прямо в `data`: RequestFactory сам разложит их в request.FILES.
    """
    request = RequestFactory().post('/admin/admin_panel/manualbook/add/', data=files or {})
    request.user = user
    request.session = {}  # FallbackStorage пишет сюда, если cookie не хватает
    request._messages = FallbackStorage(request)
    return request


def make_files(count=1, name='photo.jpg'):
    """Набор «загруженных» файлов формы (содержимое не важно — облако замокано)."""
    return [SimpleUploadedFile(name, b'\xff\xd8\xff\xe0test', content_type='image/jpeg')
            for _ in range(count)]


def make_form(existing_photos=None):
    """Заглушка ModelForm: админке нужно только cleaned_data['photos']."""
    return SimpleNamespace(cleaned_data={'photos': existing_photos or []})


class SaveModelPhotoTests(TestCase):
    """Сохранение книги с фотографиями: облако, локальный fallback, лимит."""

    def setUp(self):
        self.user = User.objects.create_user('tester', password='secret')
        self.admin = ManualBookAdmin(ManualBook, AdminSite())
        self.book = ManualBook(sku='T-1', title='Тестовая книга')

    def test_photo_uploaded_to_cloud_and_saved_as_url(self):
        request = make_request(self.user, {'photos': make_files()})

        with patch('admin_panel.admin.storage_s3.is_enabled', return_value=True), \
                patch('admin_panel.admin.storage_s3.upload_book_photo',
                      return_value=CLOUD_URL) as upload:
            self.admin.save_model(request, self.book, make_form(), change=False)

        self.book.refresh_from_db()
        self.assertEqual(self.book.photos, [CLOUD_URL])
        upload.assert_called_once()
        # В облако уходит уже сохранённая книга: иначе папка была бы id-new.
        uploaded_book = upload.call_args.args[1]
        self.assertEqual(uploaded_book.pk, self.book.pk)

    def test_existing_photos_are_preserved(self):
        request = make_request(self.user, {'photos': make_files()})
        form = make_form(['book_photos/old.jpg'])

        with patch('admin_panel.admin.storage_s3.is_enabled', return_value=True), \
                patch('admin_panel.admin.storage_s3.upload_book_photo',
                      return_value=CLOUD_URL):
            self.admin.save_model(request, self.book, form, change=False)

        self.book.refresh_from_db()
        self.assertEqual(self.book.photos, ['book_photos/old.jpg', CLOUD_URL])

    def test_photo_saved_locally_when_cloud_fails(self):
        request = make_request(self.user, {'photos': make_files()})

        with patch('admin_panel.admin.storage_s3.is_enabled', return_value=True), \
                patch('admin_panel.admin.storage_s3.upload_book_photo',
                      side_effect=PhotoStorageError('сеть недоступна')), \
                patch('admin_panel.admin.default_storage') as storage:
            storage.save.return_value = 'book_photos/local.jpg'
            self.admin.save_model(request, self.book, make_form(), change=False)

        self.book.refresh_from_db()
        # Книга сохранена, фото локальное — падения из-за облака быть не должно.
        self.assertEqual(self.book.photos, ['book_photos/local.jpg'])
        self.assertTrue(storage.save.called)
        # Администратор должен увидеть предупреждение, а не молчаливое «всё ок».
        warnings = [m.message for m in request._messages]
        self.assertTrue(any('локально' in str(m) for m in warnings), warnings)

    def test_photo_saved_locally_when_cloud_disabled(self):
        request = make_request(self.user, {'photos': make_files()})

        with patch('admin_panel.admin.storage_s3.is_enabled', return_value=False), \
                patch('admin_panel.admin.storage_s3.upload_book_photo') as upload, \
                patch('admin_panel.admin.default_storage') as storage:
            storage.save.return_value = 'book_photos/local.jpg'
            self.admin.save_model(request, self.book, make_form(), change=False)

        self.book.refresh_from_db()
        upload.assert_not_called()
        self.assertEqual(self.book.photos, ['book_photos/local.jpg'])

    def test_no_files_means_no_cloud_call(self):
        request = make_request(self.user, {})
        form = make_form(['book_photos/old.jpg'])

        with patch('admin_panel.admin.storage_s3.is_enabled', return_value=True), \
                patch('admin_panel.admin.storage_s3.upload_book_photo') as upload:
            self.admin.save_model(request, self.book, form, change=False)

        self.book.refresh_from_db()
        upload.assert_not_called()
        self.assertEqual(self.book.photos, ['book_photos/old.jpg'])

    def test_ten_photo_limit_checks_before_upload(self):
        # 9 уже есть + 2 новых файла → в облако уходит только один.
        existing = [f'book_photos/{i}.jpg' for i in range(9)]
        request = make_request(self.user, {'photos': make_files(count=2)})

        with patch('admin_panel.admin.storage_s3.is_enabled', return_value=True), \
                patch('admin_panel.admin.storage_s3.upload_book_photo',
                      side_effect=[CLOUD_URL]) as upload:
            self.admin.save_model(request, self.book, make_form(existing), change=False)

        self.book.refresh_from_db()
        self.assertEqual(upload.call_count, 1)
        self.assertEqual(len(self.book.photos), 10)

    def test_no_free_slots_skips_upload(self):
        # У книги уже 10 фото — загружать нечего, в облако не ходим.
        existing = [f'book_photos/{i}.jpg' for i in range(10)]
        request = make_request(self.user, {'photos': make_files(count=2)})

        with patch('admin_panel.admin.storage_s3.is_enabled', return_value=True), \
                patch('admin_panel.admin.storage_s3.upload_book_photo') as upload:
            self.admin.save_model(request, self.book, make_form(existing), change=False)

        self.book.refresh_from_db()
        upload.assert_not_called()
        self.assertEqual(self.book.photos, existing)

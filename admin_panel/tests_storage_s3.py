"""Тесты загрузки фото книг в Yandex Object Storage (`admin_panel.storage_s3`).

Тесты на SimpleTestCase: база данных не нужна, сеть не используется —
клиент boto3 подменяется мок-объектом, поэтому тесты быстрые и детерминированные.

Проверяем контракт модуля:
- когда загрузка считается включённой;
- как строится ключ объекта и папка книги;
- как строится публичная ссылка (в т.ч. экранирование кириллицы);
- какие параметры уходят в `put_object`;
- что ошибки boto3 превращаются в `PhotoStorageError`.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError
from django.test import SimpleTestCase, override_settings

from admin_panel.storage_s3 import (
    CACHE_CONTROL,
    PhotoStorageError,
    build_object_key,
    build_public_url,
    is_enabled,
    resolve_photo_url,
    upload_book_photo,
)
from admin_panel.widgets import MultipleImageWidget

# Настройки «как в бою»: бакет gory-knig, ключи заданы.
S3_SETTINGS = dict(
    PHOTO_S3_ENABLED=True,
    YC_S3_BUCKET='gory-knig',
    YC_S3_ACCESS_KEY='test-access-key',
    YC_S3_SECRET_KEY='test-secret-key',
    YC_S3_ENDPOINT='https://storage.yandexcloud.net',
    YC_S3_REGION='ru-central1',
    YC_S3_PUBLIC_BASE_URL='https://storage.yandexcloud.net/gory-knig',
    YC_S3_TIMEOUT=15,
    YC_S3_MAX_ATTEMPTS=3,
)

JPEG_BYTES = b'\xff\xd8\xff\xe0test-jpeg-bytes'


def make_book(pk, sku):
    """Заглушка книги: storage_s3 читает только `pk` и `sku`.

    Реальная модель Book в `__init__` вызывает `default=get_default_category`,
    то есть делает SQL-запрос. Тестам этого модуля БД не нужна, поэтому
    используем простой объект с двумя атрибутами.
    """
    return SimpleNamespace(pk=pk, sku=sku)


class FakeUploadedFile:
    """Минимальная замена UploadedFile: нужны только name, seek и read.

    Не используем SimpleUploadedFile, чтобы не тянуть лишние зависимости формы:
    модуль storage_s3 работает с любым файловым объектом.
    """

    def __init__(self, name, content=JPEG_BYTES):
        self.name = name
        self._content = content

    def seek(self, position):
        """Заглушка seek — фиксируем переданную позицию в атрибуте."""
        self.seek_called_with = position

    def read(self):
        return self._content


class IsEnabledTests(SimpleTestCase):
    """Флаг включения: нужны и PHOTO_S3_ENABLED, и бакет, и оба ключа."""

    @override_settings(**S3_SETTINGS)
    def test_enabled_with_all_settings(self):
        self.assertTrue(is_enabled())

    @override_settings(**{**S3_SETTINGS, 'PHOTO_S3_ENABLED': False})
    def test_disabled_by_flag(self):
        self.assertFalse(is_enabled())

    @override_settings(**{**S3_SETTINGS, 'YC_S3_SECRET_KEY': ''})
    def test_disabled_without_secret_key(self):
        # Пустой ключ — самая частая причина 403, поэтому проверяем отдельно.
        self.assertFalse(is_enabled())

    @override_settings(**{**S3_SETTINGS, 'YC_S3_BUCKET': ''})
    def test_disabled_without_bucket(self):
        self.assertFalse(is_enabled())


class ObjectKeyTests(SimpleTestCase):
    """Ключ объекта: book_photos/<папка книги>/<uuid>.<ext>."""

    def test_key_uses_sku_folder(self):
        book = make_book(7, 'AB-12')
        key = build_object_key(book, 'photo.jpg')
        self.assertTrue(key.startswith('book_photos/AB-12/'), key)
        self.assertTrue(key.endswith('.jpg'))

    def test_key_falls_back_to_pk_when_sku_empty(self):
        book = make_book(42, '')
        self.assertTrue(build_object_key(book, 'a.png').startswith('book_photos/id-42/'))

    def test_key_falls_back_to_pk_for_cyrillic_sku(self):
        # Кириллический артикул после чистки пустой → используем id-<pk>.
        book = make_book(5, 'Книга 1')
        self.assertTrue(build_object_key(book, 'a.png').startswith('book_photos/id-5/'))

    def test_key_sanitizes_slashes_in_sku(self):
        # Слэш в артикуле создал бы лишний уровень папок.
        book = make_book(1, 'AB/12 7')
        self.assertTrue(build_object_key(book, 'a.jpg').startswith('book_photos/AB-12-7/'))

    def test_key_normalizes_extension_case(self):
        book = make_book(1, 'AB-1')
        self.assertTrue(build_object_key(book, 'PHOTO.JPG').endswith('.jpg'))

    def test_unsupported_extension_raises(self):
        book = make_book(1, 'AB-1')
        with self.assertRaises(PhotoStorageError):
            build_object_key(book, 'scan.bmp')

    def test_key_is_unique_for_same_book(self):
        book = make_book(1, 'AB-1')
        self.assertNotEqual(build_object_key(book, 'a.jpg'), build_object_key(book, 'a.jpg'))

    def test_non_unique_key_keeps_filename_for_migration(self):
        # Перенос существующих фото должен быть идемпотентным: имя сохраняем.
        book = make_book(1, 'AB-1')
        self.assertEqual(
            build_object_key(book, 'book_photos/01.jpg', unique=False),
            'book_photos/AB-1/01.jpg',
        )

    def test_non_unique_key_is_stable_between_calls(self):
        book = make_book(1, 'AB-1')
        self.assertEqual(
            build_object_key(book, 'book_photos/01.jpg', unique=False),
            build_object_key(book, 'book_photos/01.jpg', unique=False),
        )

    def test_non_unique_key_sanitizes_spaces(self):
        book = make_book(1, 'AB-1')
        # Кириллица и пробелы вырезаются, но имя файла остаётся узнаваемым.
        self.assertEqual(
            build_object_key(book, 'book_photos/фото 1.jpg', unique=False),
            'book_photos/AB-1/1.jpg',
        )


class PublicUrlTests(SimpleTestCase):
    """Публичная ссылка для Ozon."""

    @override_settings(**S3_SETTINGS)
    def test_url_is_built_from_base_and_key(self):
        url = build_public_url('book_photos/AB-12/abc.jpg')
        self.assertEqual(
            url, 'https://storage.yandexcloud.net/gory-knig/book_photos/AB-12/abc.jpg'
        )

    @override_settings(**S3_SETTINGS)
    def test_url_quotes_non_ascii(self):
        url = build_public_url('book_photos/книга/abc.jpg')
        self.assertIn('%D0%BA%D0%BD%D0%B8%D0%B3%D0%B0', url)
        self.assertNotIn(' ', url)

    @override_settings(**{**S3_SETTINGS, 'YC_S3_PUBLIC_BASE_URL': ''})
    def test_url_requires_base(self):
        with self.assertRaises(PhotoStorageError):
            build_public_url('book_photos/AB/abc.jpg')


class UploadBookPhotoTests(SimpleTestCase):
    """Загрузка: параметры put_object, возвращаемый URL и обработка ошибок."""

    def setUp(self):
        self.book = make_book(7, 'AB-12')
        self.file = FakeUploadedFile('photo.jpg')

    @override_settings(**S3_SETTINGS)
    @patch('admin_panel.storage_s3._get_client')
    def test_upload_sends_expected_put_object(self, get_client):
        client = MagicMock()
        get_client.return_value = client

        url = upload_book_photo(self.file, self.book)

        client.put_object.assert_called_once()
        kwargs = client.put_object.call_args.kwargs
        self.assertEqual(kwargs['Bucket'], 'gory-knig')
        self.assertTrue(kwargs['Key'].startswith('book_photos/AB-12/'))
        self.assertEqual(kwargs['ContentType'], 'image/jpeg')
        self.assertEqual(kwargs['CacheControl'], CACHE_CONTROL)
        self.assertEqual(kwargs['Body'], JPEG_BYTES)
        self.assertEqual(self.file.seek_called_with, 0)  # курсор файла сброшен

        # Возвращается именно публичная ссылка, а не ключ и не signed URL.
        public_prefix = 'https://storage.yandexcloud.net/gory-knig/book_photos/AB-12/'
        self.assertTrue(url.startswith(public_prefix), url)
        self.assertTrue(url.endswith('.jpg'))

    @override_settings(**{**S3_SETTINGS, 'PHOTO_S3_ENABLED': False})
    @patch('admin_panel.storage_s3._get_client')
    def test_upload_raises_when_disabled(self, get_client):
        with self.assertRaises(PhotoStorageError):
            upload_book_photo(self.file, self.book)
        get_client.assert_not_called()  # без флага в сеть не ходим

    @override_settings(**S3_SETTINGS)
    @patch('admin_panel.storage_s3._get_client')
    def test_upload_wraps_client_error(self, get_client):
        client = MagicMock()
        client.put_object.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access Denied'}}, 'PutObject'
        )
        get_client.return_value = client

        # Ошибка должна попасть в лог модуля — этого ждёт поддержка при 403.
        with self.assertLogs('admin_panel.storage_s3', level='ERROR'):
            with self.assertRaises(PhotoStorageError):
                upload_book_photo(self.file, self.book)

    @override_settings(**S3_SETTINGS)
    @patch('admin_panel.storage_s3._get_client')
    def test_upload_rejects_unsupported_format_before_request(self, get_client):
        # Неподдерживаемый формат отсекаем до сети: лишний запрос и мусор в бакете не нужны.
        with self.assertRaises(PhotoStorageError):
            upload_book_photo(FakeUploadedFile('scan.bmp'), self.book)
        get_client.assert_not_called()

class ResolvePhotoUrlTests(SimpleTestCase):
    """Полный URL фото: облачные ссылки не трогаем, локальные пути дополняем."""

    @override_settings(MEDIA_BASE_URL='/media/')
    def test_absolute_url_passes_through(self):
        url = 'https://storage.yandexcloud.net/gory-knig/book_photos/AB/a.jpg'
        self.assertEqual(resolve_photo_url(url), url)

    @override_settings(MEDIA_BASE_URL='/media/')
    def test_relative_path_gets_media_prefix(self):
        self.assertEqual(
            resolve_photo_url('book_photos/a.jpg'), '/media/book_photos/a.jpg'
        )

    @override_settings(MEDIA_BASE_URL='/media/')
    def test_custom_base_url(self):
        # views.py передаёт свою базу (может быть абсолютной), поэтому проверяем приоритет.
        self.assertEqual(
            resolve_photo_url('book_photos/a.jpg', 'https://example.com/media'),
            'https://example.com/media/book_photos/a.jpg',
        )

    def test_empty_path_returns_empty_string(self):
        self.assertEqual(resolve_photo_url(''), '')


class WidgetPhotoUrlTests(SimpleTestCase):
    """Виджет фото: превью должно работать и для облачных ссылок, и для локальных."""

    @override_settings(MEDIA_BASE_URL='/media/')
    def test_relative_photo_uses_media_prefix(self):
        html = MultipleImageWidget().render('photos', ['book_photos/a.jpg'])
        self.assertIn('src="/media/book_photos/a.jpg"', html)
        # В data-path остаётся исходный путь — он уходит обратно в JSONField.
        self.assertIn('data-path="book_photos/a.jpg"', html)

    @override_settings(MEDIA_BASE_URL='/media/')
    def test_absolute_photo_is_not_prefixed(self):
        url = 'https://storage.yandexcloud.net/gory-knig/book_photos/AB/a.jpg'
        html = MultipleImageWidget().render('photos', [url])
        self.assertIn(f'src="{url}"', html)
        self.assertNotIn('/media/https://', html)

    def test_empty_list_renders_placeholder(self):
        html = MultipleImageWidget().render('photos', [])
        self.assertIn('Нет загруженных фотографий', html)

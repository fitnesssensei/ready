"""Загрузка фотографий книг в Yandex Object Storage (S3-совместимый API).

Модуль отвечает только за транспорт: принимает файл, кладёт объект в бакет
и возвращает публичный https-URL. Такой URL отдаёт сам файл (`image/jpeg`)
без авторизации и капчи, поэтому подходит для Ozon — в отличие от публичных
ссылок Яндекс Диска.

Особенности реализации:
- клиент boto3 создаётся лениво и один раз на процесс (`lru_cache`);
- таймауты и повторы берутся из настроек `YC_S3_TIMEOUT` / `YC_S3_MAX_ATTEMPTS`,
  чтобы недоступность облака не подвешивала сохранение книги в админке;
- любые ошибки boto3 заворачиваются в `PhotoStorageError` с понятным текстом,
  а решение «сохранить локально / показать предупреждение» принимает вызывающий
  код (BookAdmin), а не этот модуль.
"""

import logging
import mimetypes
import re
import uuid
from functools import lru_cache
from urllib.parse import quote

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings

logger = logging.getLogger(__name__)

# Расширения, которые считаем фотографиями книги. Остальные не принимаем:
# лучше явная ошибка, чем объект с неверным Content-Type в бакете.
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp', 'gif'}

# Имена объектов уникальны (uuid), поэтому контент можно кешировать «навсегда».
CACHE_CONTROL = 'public, max-age=31536000, immutable'


class PhotoStorageError(Exception):
    """Ошибка загрузки фото в Object Storage: сеть, права, квота, настройки."""


def is_enabled():
    """Включена ли загрузка в облако и заполнены ли бакет и ключи.

    Отдельная функция нужна и админке (решает, куда сохранять), и тестам.
    Пустые ключи в .env — самая частая причина 403, поэтому проверяем их явно.
    """
    return bool(
        settings.PHOTO_S3_ENABLED
        and settings.YC_S3_BUCKET
        and settings.YC_S3_ACCESS_KEY
        and settings.YC_S3_SECRET_KEY
    )


@lru_cache(maxsize=1)
def _get_client():
    """S3-клиент Яндекс Облака. Кешируется: создание клиента небесплатно.

    В тестах подменяется через `patch('admin_panel.storage_s3._get_client')`,
    поэтому реальная сеть в тестах не используется.
    """
    return boto3.client(
        's3',
        endpoint_url=settings.YC_S3_ENDPOINT,
        region_name=settings.YC_S3_REGION,
        aws_access_key_id=settings.YC_S3_ACCESS_KEY,
        aws_secret_access_key=settings.YC_S3_SECRET_KEY,
        config=Config(
            signature_version='s3v4',
            # path-style даёт ссылки вида https://storage.yandexcloud.net/<bucket>/<key>
            # — ровно то, что мы строим в build_public_url().
            s3={'addressing_style': 'path'},
            connect_timeout=settings.YC_S3_TIMEOUT,
            read_timeout=settings.YC_S3_TIMEOUT,
            # Повторы на 429/5xx и сетевых ошибках делает сам botocore.
            retries={'max_attempts': settings.YC_S3_MAX_ATTEMPTS, 'mode': 'standard'},
        ),
    )


# Всё, что не буквы/цифры/точка/дефис/подчёркивание, превращаем в дефис:
# артикулы бывают с пробелами, кириллицей и слэшами, а слэш создал бы лишний уровень.
_SKU_RE = re.compile(r'[^A-Za-z0-9._-]+')
# Папка из одного артикула полезна только если в нём есть латинские буквы.
_ASCII_LETTER_RE = re.compile(r'[A-Za-z]')


def _book_folder(book):
    """Папка книги внутри бакета: артикул, иначе `id-<pk>`.

    Папка на книгу нужна, чтобы в бакете можно было глазами найти фото
    конкретной книги, не открывая админку.
    """
    sku = (getattr(book, 'sku', '') or '').strip()
    folder = _SKU_RE.sub('-', sku).strip('-._')
    # Кириллический или чисто цифровой артикул даёт нечитаемую папку («1», «-»),
    # поэтому в таком случае используем id-<pk> — он всегда осмысленный.
    if not folder or not _ASCII_LETTER_RE.search(folder):
        folder = f'id-{book.pk}' if getattr(book, 'pk', None) else 'id-new'
    return folder[:60]


def build_object_key(book, filename, unique=True):
    """Собирает ключ объекта: `book_photos/<папка книги>/<имя>.<ext>`.

    unique=True (обычная загрузка из админки): имя — uuid, чтобы новое фото
    не перезаписало старое и объект можно было кешировать навсегда.

    unique=False (перенос существующих файлов командой): сохраняем исходное имя
    (только чистим опасные символы), чтобы повторный запуск команды
    перезаписывал тот же объект, а не плодил копии.
    """
    if filename and '/' in filename:
        filename = filename.rsplit('/', 1)[-1]
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext not in ALLOWED_EXTENSIONS:
        raise PhotoStorageError(f'Неподдерживаемый формат файла: {filename!r}')

    if unique:
        name = f'{uuid.uuid4().hex}.{ext}'
    else:
        # Точка сохраняется: имя вида «01.jpg» остаётся читаемым.
        # Крайние дефисы убираем, чтобы не получать ключи вида «-1.jpg».
        name = re.sub(r'[^A-Za-z0-9._-]+', '-', filename).strip('-._') or f'photo.{ext}'

    return f'book_photos/{_book_folder(book)}/{name}'


def build_public_url(key):
    """Публичная ссылка на объект.

    Кириллицу и не-ASCII в папке кодируем: браузеры её поймут, а Ozon
    получает корректный URL без пробелов.
    """
    base = (settings.YC_S3_PUBLIC_BASE_URL or '').rstrip('/')
    if not base:
        raise PhotoStorageError('Не задан YC_S3_PUBLIC_BASE_URL (или YC_S3_BUCKET)')
    return f'{base}/{quote(key, safe="/")}'


def resolve_photo_url(photo_path, base_url=None):
    """Полная ссылка на фото — для админки, превью и экспорта в Ozon.

    В `Book.photos` теперь могут лежать два вида значений:
    - абсолютные ссылки `https://storage.yandexcloud.net/...` (фото уже в облаке);
    - относительные пути `book_photos/<uuid>.jpg` (старые книги и локальный режим).

    Абсолютные отдаём как есть, относительные дополняем базой media —
    ровно как это делал прежний код (`MEDIA_BASE_URL` + путь).
    """
    if not photo_path:
        return ''
    if photo_path.startswith(('http://', 'https://')):
        return photo_path
    base = settings.MEDIA_BASE_URL if base_url is None else base_url
    return f'{(base or "").rstrip("/")}/{photo_path.lstrip("/")}'


def upload_book_photo(uploaded_file, book, key=None):
    """Загружает фото книги в бакет и возвращает публичный URL.

    `key` можно передать явно — это нужно команде переноса существующих фото,
    которой важно попадать в тот же объект при повторном запуске.

    Ошибки сети, прав и квоты превращаются в `PhotoStorageError`:
    текст исключения попадает в лог и в сообщение админки.
    """
    if not is_enabled():
        raise PhotoStorageError(
            'Загрузка в Object Storage выключена: проверьте PHOTO_S3_ENABLED и ключи в .env'
        )

    key = key or build_object_key(book, uploaded_file.name)
    content_type = mimetypes.guess_type(uploaded_file.name)[0] or 'application/octet-stream'

    try:
        # Файл мог быть прочитан раньше (например, при валидации формы) — сбрасываем курсор.
        uploaded_file.seek(0)
        _get_client().put_object(
            Bucket=settings.YC_S3_BUCKET,
            Key=key,
            Body=uploaded_file.read(),
            ContentType=content_type,
            CacheControl=CACHE_CONTROL,
        )
    except (ClientError, BotoCoreError) as exc:
        logger.exception('Не удалось загрузить фото в Object Storage: %s', key)
        raise PhotoStorageError(f'Ошибка загрузки фото в облако: {exc}') from exc

    url = build_public_url(key)
    logger.debug('Фото загружено в Object Storage: %s', url)
    return url

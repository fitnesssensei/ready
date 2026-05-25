"""
Скрипт импорта книг из JSON файла в базу данных.

Импортирует книги из файла parsing/eksmo_books_mt_deduped.json
в таблицу admin_panel_book с источником 'eksmo'.

Использование:
    python import_books.py

Особенности:
    - Батчевая вставка по 500 книг для оптимизации производительности
    - Пропуск дубликатов по ISBN и источнику
    - Автоматическое определение типа переплета из текстового описания
    - Парсинг года издания и количества страниц из строк
    - Установка source='eksmo' для всех импортированных книг
    - Логирование прогресса каждые 500 книг

Результат:
    Выводит статистику: количество импортированных и пропущенных книг
"""

import json
import os
import django

# Настройка Django окружения для работы с моделями
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shop_admin.settings')
django.setup()

from admin_panel.models import Book


def parse_cover_type(cover_str):
    """
    Определить тип переплета из текстового описания.

    Args:
        cover_str: Строка с описанием переплета (например, "Мягкая обложка", "Твердый переплет")

    Returns:
        str: 'soft' для мягкого переплета, 'hard' для твердого (по умолчанию)

    Примеры:
        >>> parse_cover_type("Мягкая обложка")
        'soft'
        >>> parse_cover_type("Твердый переплет")
        'hard'
        >>> parse_cover_type("")
        'hard'
    """
    if not cover_str:
        return 'hard'
    cover_lower = cover_str.lower()
    # Проверяем наличие ключевых слов для мягкого переплета
    if 'мягк' in cover_lower or 'обложка' in cover_lower:
        return 'soft'
    return 'hard'


def parse_year(year_str):
    """
    Извлечь год издания из строки.

    Args:
        year_str: Строка с годом (может быть пустой или содержать нечисловые символы)

    Returns:
        int or None: Год издания (1800-2030) или None, если не удалось распарсить

    Примеры:
        >>> parse_year("2024")
        2024
        >>> parse_year("")
        None
        >>> parse_year("abc")
        None
        >>> parse_year("1500")  # Слишком старый год
        None
    """
    if not year_str or not year_str.strip():
        return None
    try:
        year = int(year_str.strip())
        # Валидация: год должен быть в разумных пределах
        if 1800 <= year <= 2030:
            return year
    except (ValueError, TypeError):
        pass
    return None


def parse_pages(pages_str):
    """
    Извлечь количество страниц из строки.

    Args:
        pages_str: Строка с количеством страниц

    Returns:
        int or None: Количество страниц или None, если не удалось распарсить

    Примеры:
        >>> parse_pages("256")
        256
        >>> parse_pages("")
        None
        >>> parse_pages("abc")
        None
    """
    if not pages_str or not pages_str.strip():
        return None
    try:
        return int(pages_str.strip())
    except (ValueError, TypeError):
        return None


def import_books():
    """
    Основная функция импорта книг из JSON файла.

    Читает файл parsing/eksmo_books_mt_deduped.json и импортирует книги
    в базу данных с использованием батчевой вставки.

    Процесс:
        1. Загрузка JSON файла
        2. Обработка каждой книги:
           - Проверка наличия ISBN
           - Проверка на дубликаты (ISBN + источник)
           - Парсинг полей (год, страницы, тип переплета)
           - Добавление в список для вставки
        3. Батчевая вставка каждые 500 книг
        4. Вывод статистики

    Raises:
        FileNotFoundError: Если файл parsing/eksmo_books_mt_deduped.json не найден
        json.JSONDecodeError: Если файл содержит невалидный JSON
    """
    # Открываем и читаем JSON файл с книгами
    with open('parsing/eksmo_books_mt_deduped.json', 'r', encoding='utf-8') as f:
        books_data = json.load(f)

    print(f'Загружено {len(books_data)} книг из JSON')

    # Списки для накопления книг и статистики
    books_to_create = []
    skipped = 0

    # Обрабатываем каждую книгу из JSON
    for idx, book_data in enumerate(books_data, 1):
        isbn = book_data.get('isbn', '').strip()

        # Пропустить книги без ISBN (обязательное поле для уникальности)
        if not isbn:
            skipped += 1
            continue

        # Проверить, существует ли книга с таким ISBN и источником
        # Это предотвращает дубликаты при повторном запуске скрипта
        if Book.objects.filter(isbn=isbn, source=Book.SOURCE_EKSMO).exists():
            skipped += 1
            continue

        # Создаем объект книги с обработанными данными
        book = Book(
            # Обрезаем строки до максимальной длины полей модели
            title=book_data.get('title', '')[:200],
            author=book_data.get('author', '')[:100],
            isbn=isbn[:20],
            description=book_data.get('description', ''),
            publisher=book_data.get('publisher', '')[:100],

            # Парсим год издания из строки
            publication_year=parse_year(book_data.get('year')),

            # Парсим количество страниц из строки
            pages=parse_pages(book_data.get('pages')),

            # Определяем тип переплета из текстового описания
            cover_type=parse_cover_type(book_data.get('cover')),

            # Серия (может быть None)
            series=book_data.get('series', '')[:200] if book_data.get('series') else None,

            # Источник: все книги из этого импорта - Эксмо
            source=Book.SOURCE_EKSMO,

            # Язык по умолчанию - русский
            language='Русский',

            # Цена и остаток по умолчанию (будут заполнены позже)
            price=0,
            stock=0,
        )
        books_to_create.append(book)

        # Батчевая вставка каждые 500 книг для оптимизации
        # Это значительно быстрее, чем вставлять по одной книге
        if len(books_to_create) >= 500:
            Book.objects.bulk_create(books_to_create, ignore_conflicts=True)
            print(f'Импортировано {idx} / {len(books_data)} книг...')
            books_to_create = []

    # Вставить оставшиеся книги (меньше 500)
    if books_to_create:
        Book.objects.bulk_create(books_to_create, ignore_conflicts=True)

    # Подсчитываем итоговое количество импортированных книг
    total_imported = Book.objects.filter(source=Book.SOURCE_EKSMO).count()

    # Выводим статистику
    print(f'\n✅ Импорт завершен!')
    print(f'Всего импортировано: {total_imported} книг')
    print(f'Пропущено (дубликаты или без ISBN): {skipped}')


if __name__ == '__main__':
    import_books()

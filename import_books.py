import json
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shop_admin.settings')
django.setup()

from admin_panel.models import Book

def parse_cover_type(cover_str):
    """Определить тип переплета"""
    if not cover_str:
        return 'hard'
    cover_lower = cover_str.lower()
    if 'мягк' in cover_lower or 'обложка' in cover_lower:
        return 'soft'
    return 'hard'

def parse_year(year_str):
    """Извлечь год из строки"""
    if not year_str or not year_str.strip():
        return None
    try:
        year = int(year_str.strip())
        if 1800 <= year <= 2030:
            return year
    except (ValueError, TypeError):
        pass
    return None

def parse_pages(pages_str):
    """Извлечь количество страниц"""
    if not pages_str or not pages_str.strip():
        return None
    try:
        return int(pages_str.strip())
    except (ValueError, TypeError):
        return None

def import_books():
    with open('parsing/eksmo_books_mt_deduped.json', 'r', encoding='utf-8') as f:
        books_data = json.load(f)

    print(f'Загружено {len(books_data)} книг из JSON')

    books_to_create = []
    skipped = 0

    for idx, book_data in enumerate(books_data, 1):
        isbn = book_data.get('isbn', '').strip()

        # Пропустить книги без ISBN
        if not isbn:
            skipped += 1
            continue

        # Проверить, существует ли книга с таким ISBN и источником
        if Book.objects.filter(isbn=isbn, source=Book.SOURCE_EKSMO).exists():
            skipped += 1
            continue

        book = Book(
            title=book_data.get('title', '')[:200],
            author=book_data.get('author', '')[:100],
            isbn=isbn[:20],
            description=book_data.get('description', ''),
            publisher=book_data.get('publisher', '')[:100],
            publication_year=parse_year(book_data.get('year')),
            pages=parse_pages(book_data.get('pages')),
            cover_type=parse_cover_type(book_data.get('cover')),
            series=book_data.get('series', '')[:200] if book_data.get('series') else None,
            source=Book.SOURCE_EKSMO,
            language='Русский',
            price=0,
            stock=0,
        )
        books_to_create.append(book)

        # Батчевая вставка каждые 500 книг
        if len(books_to_create) >= 500:
            Book.objects.bulk_create(books_to_create, ignore_conflicts=True)
            print(f'Импортировано {idx} / {len(books_data)} книг...')
            books_to_create = []

    # Вставить оставшиеся книги
    if books_to_create:
        Book.objects.bulk_create(books_to_create, ignore_conflicts=True)

    total_imported = Book.objects.filter(source=Book.SOURCE_EKSMO).count()
    print(f'\n✅ Импорт завершен!')
    print(f'Всего импортировано: {total_imported} книг')
    print(f'Пропущено (дубликаты или без ISBN): {skipped}')

if __name__ == '__main__':
    import_books()

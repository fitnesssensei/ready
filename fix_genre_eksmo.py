"""
Скрипт исправления поля genre для уже импортированных книг Эксмо.

Использование:
    python fix_genre_eksmo.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shop_admin.settings')
django.setup()

from admin_panel.models import Book

CATEGORY_TO_GENRE = {
    'Боевик, книга о войне': 'boevic',
    'Детективы, триллеры': 'detective',
    'Другое': '',
    'Исторический роман': 'history',
    'Классики литературы': 'prose',
    'Литература античная и средних веков': 'antic',
    'Любовный роман, эротика': 'romance',
    'Мемуары, биографии': 'memoirs',
    'Мифы, сказки, фольклор': 'epic_folklore',
    'Поэзия': 'poetry',
    'Приключения, путешествия': 'adventure',
    'Публицистика': 'journalism',
    'Сатира, юмор': 'satire',
    'Советские писатели': 'sovetsk',
    'Современная литература': 'prose',
    'Ужасы, мистика': 'horror',
    'Фантастика, фэнтези': 'fantastic',
    'Художественная': 'hudozhka',
}


def fix_genre():
    books = Book.objects.filter(source=Book.SOURCE_EKSMO)
    total = books.count()
    updated = 0
    skipped = 0

    for book in books:
        old_val = (book.genre or '').strip()
        if not old_val:
            skipped += 1
            continue
        new_val = CATEGORY_TO_GENRE.get(old_val.replace('\xa0', ' '))
        if new_val is None:
            # Значение не найдено в маппинге — возможно, уже исправлено
            skipped += 1
            continue
        if new_val == old_val:
            skipped += 1
            continue
        book.genre = new_val
        book.save(update_fields=['genre'])
        updated += 1

    print(f'Всего книг Эксмо: {total}')
    print(f'Исправлено: {updated}')
    print(f'Пропущено (уже ок / пусто / неизвестно): {skipped}')


if __name__ == '__main__':
    fix_genre()

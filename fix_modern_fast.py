import os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shop_admin.settings')
import django
django.setup()

import json
from admin_panel.models import Book

# Загружаем JSON и собираем все isbn для 'Современная литература'
with open('JSON/36200_libex.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

modern_isbns = set()
for item in data:
    if item.get('category', '').strip() == 'Современная литература':
        isbn = item.get('isbn', '').strip()
        if isbn:
            modern_isbns.add(isbn)

print(f'ISBN в JSON: {len(modern_isbns)}')

# Обновляем по isbn пачками
updated = 0
isbn_list = list(modern_isbns)
for i in range(0, len(isbn_list), 500):
    chunk = isbn_list[i:i+500]
    u = Book.objects.filter(source='eksmo', isbn__in=chunk).exclude(genre='modern').update(genre='modern')
    updated += u
    if (i+1) % 1000 == 0:
        print(f'  обработано ISBN: {i+500}')

print(f'По ISBN обновлено: {updated}')

# Теперь собираем названия для оставшихся 'prose'
still_prose = Book.objects.filter(source='eksmo', genre='prose').only('id', 'title')
print(f'Осталось prose: {still_prose.count()}')

# Собираем все названия из JSON
modern_titles = set()
for item in data:
    if item.get('category', '').strip() == 'Современная литература':
        title = item.get('title', '').strip()
        if title:
            modern_titles.add(title)

print(f'Названий в JSON: {len(modern_titles)}')

# Идём по still_prose и проверяем название
updated2 = 0
batch = []
for book in still_prose:
    if book.title in modern_titles:
        batch.append(book.id)
    if len(batch) >= 500:
        Book.objects.filter(id__in=batch).update(genre='modern')
        updated2 += len(batch)
        batch = []

if batch:
    Book.objects.filter(id__in=batch).update(genre='modern')
    updated2 += len(batch)

print(f'По названиям обновлено: {updated2}')
print(f'Всего обновлено: {updated + updated2}')
total = Book.objects.filter(source='eksmo', genre='modern').count()
print(f'Всего modern: {total}')

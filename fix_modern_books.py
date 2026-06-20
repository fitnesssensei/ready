import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shop_admin.settings')
import django
django.setup()

import json
from admin_panel.models import Book

with open('JSON/36200_libex.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Собираем названия книг с category='Современная литература'
titles = set()
for item in data:
    if item.get('category', '').strip() == 'Современная литература':
        title = item.get('title', '').strip()
        if title:
            titles.add(title)

print(f'Найдено в JSON: {len(titles)} названий')

updated = 0
for t in titles:
    books = Book.objects.filter(source='eksmo', title__iexact=t)
    if not books.exists():
        books = Book.objects.filter(source='eksmo', title__icontains=t[:40])
    for book in books:
        if book.genre != 'modern':
            book.genre = 'modern'
            book.save(update_fields=['genre'])
            updated += 1

print(f'Исправлено: {updated}')
total = Book.objects.filter(source='eksmo', genre='modern').count()
print(f'Всего книг с genre=modern: {total}')

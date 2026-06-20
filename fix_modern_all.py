import os, re, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shop_admin.settings')
import django
django.setup()

import json
from admin_panel.models import Book

def clean(s):
    s = re.sub(r'<[^>]+>', '', s)
    s = s.replace('&quot;', '"').replace('&amp;', '&')
    return s.strip().lower()

print('Загружаю JSON...')
with open('JSON/36200_libex.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Собираем очищенные названия из JSON
json_titles = set()
for item in data:
    if item.get('category', '').strip() == 'Современная литература':
        t = clean(item.get('title', ''))
        if t:
            json_titles.add(t)

print(f'Уникальных названий в JSON: {len(json_titles)}')

# Загружаем все книги Эксмо в память
print('Загружаю книги из БД...')
all_books = list(Book.objects.filter(source='eksmo').only('id', 'title', 'genre'))
print(f'Книг в БД: {len(all_books)}')

# Ищем совпадения
to_update = []
for book in all_books:
    if book.genre == 'modern':
        continue
    bt = clean(book.title)
    if bt in json_titles:
        to_update.append(book.id)

print(f'Найдено книг для обновления: {len(to_update)}')

# Обновляем пачками
updated = 0
for i in range(0, len(to_update), 500):
    chunk = to_update[i:i+500]
    u = Book.objects.filter(id__in=chunk).update(genre='modern')
    updated += u

print(f'Исправлено: {updated}')
total = Book.objects.filter(source='eksmo', genre='modern').count()
print(f'Всего modern: {total}')

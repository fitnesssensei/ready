"""
Команда для подготовки книг Эксмо к экспорту на Ozon.

⚠️ Закомментировано — часть интеграции с Ozon Seller API.

Запуск (если раскомментировать):
    python manage.py prepare_eksmo_for_ozon
    python manage.py prepare_eksmo_for_ozon --price 500
    python manage.py prepare_eksmo_for_ozon --category-id 2345346
"""

# from decimal import Decimal
# from django.core.management.base import BaseCommand
# from django.db import transaction
#
# from admin_panel.models import Book, Category
#
#
# class Command(BaseCommand):
#     help = 'Подготовка книг Эксмо к экспорту на Ozon (установка категории и цен)'
#
#     def add_arguments(self, parser):
#         parser.add_argument(
#             '--price',
#             type=float,
#             default=500.0,
#             help='Базовая цена для книг без цены (по умолчанию 500)',
#         )
#         parser.add_argument(
#             '--category-id',
#             type=str,
#             help='Ozon Category ID для книг (если не указан, используется первая доступная)',
#         )
#
#     def handle(self, *args, **options):
#         base_price = Decimal(str(options['price']))
#         category_id = options['category_id']
#
#         if category_id:
#             category = Category.objects.filter(ozon_category_id=category_id).first()
#             if not category:
#                 self.stderr.write(self.style.ERROR(f'Категория с ID {category_id} не найдена'))
#                 return
#         else:
#             category = Category.objects.first()
#             if not category:
#                 self.stderr.write(self.style.ERROR('Нет доступных категорий. Создайте категорию в админке.'))
#                 return
#
#         self.stdout.write(f'Используется категория: {category.name} (Ozon ID: {category.ozon_category_id})')
#
#         eksmo_books = Book.objects.filter(source=Book.SOURCE_EKSMO)
#
#         books_without_category = eksmo_books.filter(category__isnull=True)
#         books_without_price = eksmo_books.filter(price=0)
#
#         self.stdout.write(f'\\nКниг без категории: {books_without_category.count()}')
#         self.stdout.write(f'Книг без цены: {books_without_price.count()}')
#
#         with transaction.atomic():
#             if books_without_category.exists():
#                 updated_cat = books_without_category.update(category=category)
#                 self.stdout.write(self.style.SUCCESS(f'Установлена категория для {updated_cat} книг'))
#
#             if books_without_price.exists():
#                 updated_price = books_without_price.update(price=base_price)
#                 self.stdout.write(self.style.SUCCESS(f'Установлена цена {base_price} для {updated_price} книг'))
#
#         ready_for_export = eksmo_books.filter(
#             category__isnull=False,
#             price__gt=0
#         ).count()
#
#         self.stdout.write(
#             self.style.SUCCESS(
#                 f'\\nГотово! Книг Эксмо готовых к экспорту: {ready_for_export} из {eksmo_books.count()}'
#             )
#         )

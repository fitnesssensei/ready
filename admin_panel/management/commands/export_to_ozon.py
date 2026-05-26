"""
Команда для экспорта книг на Ozon через API.

⚠️ Закомментировано — часть интеграции с Ozon Seller API.

Запуск (если раскомментировать):
    python manage.py export_to_ozon
    python manage.py export_to_ozon --source eksmo
    python manage.py export_to_ozon --limit 100
    python manage.py export_to_ozon --dry-run
"""

# from django.core.management.base import BaseCommand
# from django.db.models import Q
#
# from admin_panel.models import Book
# from admin_panel.ozon_api import OzonAPI, OzonAPIError, book_to_ozon_item
#
#
# class Command(BaseCommand):
#     help = 'Экспорт книг на Ozon через API'
#
#     def add_arguments(self, parser):
#         parser.add_argument(
#             '--source',
#             type=str,
#             choices=['manual', 'eksmo'],
#             help='Источник книг для экспорта (manual или eksmo)',
#         )
#         parser.add_argument(
#             '--limit',
#             type=int,
#             help='Максимальное количество книг для экспорта',
#         )
#         parser.add_argument(
#             '--dry-run',
#             action='store_true',
#             help='Только показать данные, без отправки на Ozon',
#         )
#
#     def handle(self, *args, **options):
#         queryset = Book.objects.all()
#
#         if options['source']:
#             queryset = queryset.filter(source=options['source'])
#
#         queryset = queryset.filter(
#             category__isnull=False,
#             price__gt=0
#         ).select_related('category')
#
#         if options['limit']:
#             queryset = queryset[:options['limit']]
#
#         books = list(queryset)
#
#         if not books:
#             self.stdout.write(self.style.WARNING('Нет книг для экспорта'))
#             return
#
#         self.stdout.write(f'Найдено книг для экспорта: {len(books)}')
#
#         items = []
#         for book in books:
#             try:
#                 item = book_to_ozon_item(book)
#                 items.append(item)
#             except Exception as e:
#                 self.stderr.write(
#                     self.style.ERROR(f'Ошибка при обработке книги {book.id} ({book.title}): {e}')
#                 )
#
#         self.stdout.write(f'Подготовлено товаров: {len(items)}')
#
#         if options['dry_run']:
#             self.stdout.write(self.style.WARNING('Dry-run режим: данные не отправлены'))
#             if items:
#                 import json
#                 self.stdout.write('\\nПример первого товара:')
#                 self.stdout.write(json.dumps(items[0], ensure_ascii=False, indent=2))
#             return
#
#         try:
#             api = OzonAPI()
#             self.stdout.write('Отправка товаров на Ozon...')
#
#             batch_size = 100
#             total_sent = 0
#             task_ids = []
#
#             for i in range(0, len(items), batch_size):
#                 batch = items[i:i + batch_size]
#                 result = api.import_products(batch)
#
#                 if 'result' in result and 'task_id' in result['result']:
#                     task_id = result['result']['task_id']
#                     task_ids.append(task_id)
#                     total_sent += len(batch)
#                     self.stdout.write(
#                         self.style.SUCCESS(
#                             f'Отправлено {len(batch)} товаров, task_id: {task_id}'
#                         )
#                     )
#                 else:
#                     self.stderr.write(
#                         self.style.ERROR(f'Неожиданный ответ API: {result}')
#                     )
#
#             self.stdout.write(
#                 self.style.SUCCESS(
#                     f'\\nГотово! Отправлено {total_sent} товаров.\\n'
#                     f'Task IDs для проверки статуса: {\", \".join(map(str, task_ids))}\\n'
#                     f'Проверить статус: python manage.py check_ozon_import --task-id <ID>'
#                 )
#             )
#
#         except OzonAPIError as e:
#             self.stderr.write(self.style.ERROR(f'Ошибка Ozon API: {e}'))
#         except Exception as e:
#             self.stderr.write(self.style.ERROR(f'Неожиданная ошибка: {e}'))


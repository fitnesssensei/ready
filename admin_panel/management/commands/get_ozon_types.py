"""
Команда для получения типов товаров (type_id) для категории Ozon.

⚠️ Закомментировано — часть интеграции с Ozon Seller API.

Запуск (если раскомментировать):
    python manage.py get_ozon_types --category-id 2345346
"""

# import json
# from django.core.management.base import BaseCommand
#
# from admin_panel.ozon_api import OzonAPI, OzonAPIError
#
#
# class Command(BaseCommand):
#     help = 'Получить типы товаров для категории Ozon'
#
#     def add_arguments(self, parser):
#         parser.add_argument(
#             '--category-id',
#             type=int,
#             required=True,
#             help='ID категории Ozon',
#         )
#
#     def handle(self, *args, **options):
#         category_id = options['category_id']
#
#         try:
#             api = OzonAPI()
#             self.stdout.write(f'Получение типов товаров для категории {category_id}...')
#
#             result = api.get_product_types(category_id)
#
#             self.stdout.write('\\nОтвет API:')
#             self.stdout.write(json.dumps(result, ensure_ascii=False, indent=2))
#
#             if 'result' in result:
#                 types = result['result']
#                 if types:
#                     self.stdout.write(self.style.SUCCESS(f'\\nНайдено типов: {len(types)}'))
#                     for t in types:
#                         type_id = t.get('id', 'N/A')
#                         type_name = t.get('name', 'N/A')
#                         self.stdout.write(f'  - ID: {type_id}, Название: {type_name}')
#                 else:
#                     self.stdout.write(self.style.WARNING('Типы товаров не найдены'))
#
#         except OzonAPIError as e:
#             self.stderr.write(self.style.ERROR(f'Ошибка Ozon API: {e}'))
#         except Exception as e:
#             self.stderr.write(self.style.ERROR(f'Неожиданная ошибка: {e}'))

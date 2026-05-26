"""
Команда для получения атрибутов категории Ozon.

⚠️ Закомментировано — часть интеграции с Ozon Seller API.

Запуск (если раскомментировать):
    python manage.py get_ozon_category_info --category-id 2345346
"""

# import json
# from django.core.management.base import BaseCommand
#
# from admin_panel.ozon_api import OzonAPI, OzonAPIError
#
#
# class Command(BaseCommand):
#     help = 'Получить информацию об атрибутах категории Ozon'
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
#             self.stdout.write(f'Получение атрибутов категории {category_id}...')
#
#             result = api.get_category_attributes(category_id)
#
#             self.stdout.write('\\nОтвет API:')
#             self.stdout.write(json.dumps(result, ensure_ascii=False, indent=2))
#
#         except OzonAPIError as e:
#             self.stderr.write(self.style.ERROR(f'Ошибка Ozon API: {e}'))
#         except Exception as e:
#             self.stderr.write(self.style.ERROR(f'Неожиданная ошибка: {e}'))

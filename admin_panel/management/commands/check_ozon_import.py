"""
Команда для проверки статуса импорта товаров на Ozon.

⚠️ Закомментировано — часть интеграции с Ozon Seller API.

Запуск (если раскомментировать):
    python manage.py check_ozon_import --task-id 123456789
"""

# from django.core.management.base import BaseCommand
#
# from admin_panel.ozon_api import OzonAPI, OzonAPIError
#
#
# class Command(BaseCommand):
#     help = 'Проверка статуса импорта товаров на Ozon'
#
#     def add_arguments(self, parser):
#         parser.add_argument(
#             '--task-id',
#             type=int,
#             required=True,
#             help='ID задачи импорта (task_id из результата export_to_ozon)',
#         )
#
#     def handle(self, *args, **options):
#         task_id = options['task_id']
#
#         try:
#             api = OzonAPI()
#             self.stdout.write(f'Проверка статуса задачи {task_id}...')
#
#             result = api.get_import_info(task_id)
#
#             if 'result' not in result:
#                 self.stderr.write(self.style.ERROR(f'Неожиданный ответ API: {result}'))
#                 return
#
#             info = result['result']
#
#             status = info.get('status', 'unknown')
#             total = info.get('total', 0)
#
#             self.stdout.write(f'\\nСтатус: {status}')
#             self.stdout.write(f'Всего товаров: {total}')
#
#             items = info.get('items', [])
#
#             if items:
#                 success_count = sum(1 for item in items if item.get('status') == 'imported')
#                 error_count = sum(1 for item in items if item.get('status') == 'failed')
#
#                 self.stdout.write(f'Успешно импортировано: {success_count}')
#                 self.stdout.write(f'Ошибок: {error_count}')
#
#                 if error_count > 0:
#                     self.stdout.write('\\nТовары с ошибками:')
#                     for item in items:
#                         if item.get('status') == 'failed':
#                             offer_id = item.get('offer_id', 'unknown')
#                             errors = item.get('errors', [])
#                             self.stderr.write(f'\\n  Артикул: {offer_id}')
#                             for error in errors:
#                                 self.stderr.write(f'    - {error.get("message", "Неизвестная ошибка")}')
#
#             self.stdout.write(self.style.SUCCESS('\\nГотово!'))
#
#         except OzonAPIError as e:
#             self.stderr.write(self.style.ERROR(f'Ошибка Ozon API: {e}'))
#         except Exception as e:
#             self.stderr.write(self.style.ERROR(f'Неожиданная ошибка: {e}'))

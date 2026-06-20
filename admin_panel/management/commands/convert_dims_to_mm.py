"""
⚠️ КОМАНДА ОТКЛЮЧЕНА — данные в БД уже хранятся в мм.

Ранее предполагалось, что размеры (width/length/height) сохранены в сантиметрах,
и команда умножает их на 10 для конвертации в мм.
Однако импорт и парсинг всегда сохраняли значения в мм.

Запуск этой команды ИСПОРТИТ данные — увеличит размеры в 10 раз.
Если случайно запустили — создайте команду для деления на 10.
"""

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db.models import Q

from admin_panel.models import Book

BATCH_SIZE = 500


class Command(BaseCommand):
    help = '⚠️ ОТКЛЮЧЕНО: размеры в БД уже в мм, умножать на 10 НЕЛЬЗЯ'

    # def add_arguments(self, parser):
    #     parser.add_argument(
    #         '--dry-run',
    #         action='store_true',
    #         help='Только показать, что будет обновлено, без записи в БД',
    #     )

    def handle(self, *args, **options):
        self.stdout.write(self.style.ERROR(
            'ОТМЕНЕНО: размеры в БД уже хранятся в мм. '
            'Запуск этой команды испортит данные!'
        ))
        self.stdout.write(self.style.WARNING(
            'См. docstring в файле convert_dims_to_mm.py для подробностей.'
        ))
        # Ничего не делаем — защита от случайного запуска

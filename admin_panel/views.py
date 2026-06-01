import logging
import os

import yaml
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, Alignment
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render

from .models import Book, OzonTemplate

logger = logging.getLogger(__name__)


def dashboard(request):
    return render(request, 'admin_panel/dashboard.html')


def products(request):
    return render(request, 'admin_panel/products.html')


def orders(request):
    return render(request, 'admin_panel/orders.html')


def customers(request):
    return render(request, 'admin_panel/customers.html')


def export_books_to_ozon_template(request):
    """
    Экспорт выбранных книг в шаблон Ozon.

    Загружает активный шаблон Excel из модели OzonTemplate и заполняет его
    данными выбранных книг с автоматическим маппингом полей.

    Args:
        request: HTTP запрос с атрибутом ozon_export_queryset (queryset книг)

    Returns:
        HttpResponse с заполненным Excel файлом для загрузки на Ozon
        или сообщение об ошибке, если шаблон не найден

    Особенности:
        - Использует последний активный шаблон из OzonTemplate
        - Автоматически преобразует единицы измерения:
          * Вес: кг → граммы (умножение на 1000)
          * Размеры: см → мм (умножение на 10)
        - Заполняет обязательные поля Ozon значениями по умолчанию
        - Обрабатывает ошибки с понятными сообщениями

    Структура шаблона Ozon:
        - Лист: "Шаблон"
        - Строка заголовков: 2
        - Начало данных: строка 5
    """
    # Получить книги из запроса или все книги, если не указано
    if hasattr(request, 'ozon_export_queryset'):
        books = request.ozon_export_queryset
    else:
        books = Book.objects.select_related('category').all()

    # Получить активный шаблон из базы данных
    template = OzonTemplate.objects.filter(is_active=True).first()

    # Проверка наличия активного шаблона
    if not template:
        return HttpResponse(
            "Ошибка: Не найден активный шаблон Ozon. Загрузите шаблон через админку в разделе 'Шаблоны Ozon'.",
            content_type='text/plain; charset=utf-8',
            status=400
        )

    # Построить полный путь к файлу шаблона
    template_path = os.path.join(settings.MEDIA_ROOT, template.file.name)

    # Проверка существования файла на диске
    if not os.path.exists(template_path):
        return HttpResponse(
            f"Ошибка: Файл шаблона не найден: {template.file.name}",
            content_type='text/plain; charset=utf-8',
            status=404
        )

    # Базовый URL для построения ссылок на медиа-файлы (фото)
    # Используем MEDIA_BASE_URL из настроек (для внешнего доступа к фото Ozon)
    media_base_url = getattr(settings, 'MEDIA_BASE_URL', request.build_absolute_uri(settings.MEDIA_URL))

    try:
        # Загрузить Excel файл шаблона
        wb = load_workbook(template_path)

        # Открыть лист "Шаблон" (стандартное название в шаблонах Ozon)
        if 'Шаблон' not in wb.sheetnames:
            return HttpResponse(
                "Ошибка: В шаблоне не найден лист 'Шаблон'",
                content_type='text/plain; charset=utf-8',
                status=400
            )

        ws = wb['Шаблон']

        # Заголовки находятся в строке 2 (не в первой!)
        header_row = 2
        headers = {}

        # Читаем все заголовки и сохраняем их позиции (номера колонок)
        for col_num in range(1, ws.max_column + 1):
            cell_value = ws.cell(row=header_row, column=col_num).value
            if cell_value:
                # Нормализуем название колонки: убираем переносы строк, приводим к нижнему регистру
                header_clean = str(cell_value).replace('\n', ' ').strip().lower()
                headers[header_clean] = col_num

        # Маппинг наших полей на колонки Ozon
        # Используем lambda функции для гибкого преобразования данных
        field_mapping = {
            # Основные поля
            'артикул*': lambda book: book.sku or '',
            'название товара': lambda book: book.title,

            # Цены
            'цена, руб.*': lambda book: float(book.price) if book.price else '',
            'цена до скидки, руб.': lambda book: float(book.old_price) if book.old_price else '',
            'ндс, %*': lambda book: book.vat_rate or '0',

            # Размеры и вес (ВАЖНО: преобразование единиц измерения!)
            # Вес: кг → граммы (умножаем на 1000)
            'вес в упаковке, г*': lambda book: int(float(book.weight) * 1000) if book.weight else '',
            # Размеры: см → мм (умножаем на 10)
            'ширина упаковки, мм*': lambda book: int(float(book.width) * 10) if book.width else '',
            'высота упаковки, мм*': lambda book: int(float(book.height) * 10) if book.height else '',
            'длина упаковки, мм*': lambda book: int(float(book.length) * 10) if book.length else '',

            # Информация об авторе и издании
            'автор на обложке': lambda book: book.author_oblozh or '',
            'автор': lambda book: book.author or '',
            'тип обложки': lambda book: book.get_cover_type_display(),

            # Обязательные поля Ozon с фиксированными значениями
            'тип*': lambda book: 'Букинистическое издание',  # Тип товара для букинистики
            'бренд*': lambda book: book.publisher or 'Нет бренда',  # Бренд = издательство
            'тн вэд коды еаэс*': lambda book: '4901990000',  # Код ТН ВЭД для книг

            # Дополнительная информация
            'издательство': lambda book: book.publisher or '',
            'серия': lambda book: book.series or '',
            'год выпуска': lambda book: book.publication_year or '',
            'язык издания': lambda book: book.language or 'Русский',
            'количество страниц': lambda book: book.pages or '',
            'isbn': lambda book: book.isbn or '',
            'аннотация': lambda book: book.description or '',

            # Фотографии: book.photos хранит список относительных путей
            # Преобразуем в полные URL для загрузки Ozon
            'ссылка на главное фото*': lambda book: (
                f'{media_base_url}{book.photos[0]}' if book.photos else ''
            ),
            'ссылки на дополнительные фото': lambda book: (
                ' '.join(f'{media_base_url}{photo}' for photo in book.photos[1:])
                if len(book.photos) > 1 else ''
            ),
        }

        # Начинаем заполнять с 5-й строки (после заголовков и описаний)
        current_row = 5

        # Обрабатываем каждую книгу
        for idx, book in enumerate(books, 1):
            # Номер строки в первой колонке
            ws.cell(row=current_row, column=1).value = idx

            # Заполняем остальные поля согласно маппингу
            for header_name, col_num in headers.items():
                if header_name in field_mapping:
                    try:
                        # Вызываем lambda функцию для получения значения
                        value = field_mapping[header_name](book)
                        ws.cell(row=current_row, column=col_num).value = value
                    except Exception as e:
                        # Логируем ошибку, но продолжаем работу
                        logger.warning(f"Ошибка при заполнении поля '{header_name}' для книги {book.id}: {e}")
                        ws.cell(row=current_row, column=col_num).value = ''

            current_row += 1

        # Создать HTTP ответ с заполненным шаблоном
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        # Имя файла содержит количество экспортированных книг
        response['Content-Disposition'] = f'attachment; filename="ozon_export_{len(books)}_books.xlsx"'

        # Сохраняем книгу Excel в ответ
        wb.save(response)
        return response

    except Exception as e:
        # Обработка любых непредвиденных ошибок
        logger.error(f"Ошибка при экспорте в шаблон Ozon: {e}")
        return HttpResponse(
            f"Ошибка при обработке шаблона: {str(e)}",
            content_type='text/plain; charset=utf-8',
            status=500
        )


def export_books_to_excel(request):
    """
    Экспорт выбранных книг в стандартный Excel файл.

    Создает Excel файл (.xlsx) со всеми данными книг в табличном формате.
    Используется библиотека openpyxl для работы с Excel.

    Args:
        request: HTTP запрос с атрибутом excel_export_queryset (queryset книг)

    Returns:
        HttpResponse с Excel файлом для скачивания

    Особенности:
        - 25 колонок с полной информацией о книгах
        - Форматированные заголовки (жирный шрифт, выравнивание)
        - Автоматическая ширина колонок (макс. 50 символов)
        - Преобразование Decimal в float для корректного отображения
    """
    # Получить книги из запроса или все книги, если не указано
    if hasattr(request, 'excel_export_queryset'):
        books = request.excel_export_queryset
    else:
        books = Book.objects.select_related('category').all()

    # Создаем новую книгу Excel
    wb = Workbook()
    ws = wb.active
    ws.title = "Книги"

    # Заголовки колонок - все основные поля книги
    headers = [
        'ID', 'Артикул', 'Название', 'Автор', 'Автор на обложке', 'Жанр',
        'Издательство', 'Серия', 'Год издания', 'Язык', 'Сохранность',
        'Тип переплёта', 'Страниц', 'ISBN', 'Цена', 'Старая цена',
        'НДС', 'Остаток', 'Вес (кг)', 'Длина (см)', 'Ширина (см)',
        'Высота (см)', 'Категория', 'Источник', 'Дата создания'
    ]

    # Записываем заголовки в первую строку с форматированием
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num)
        cell.value = header
        cell.font = Font(bold=True)  # Жирный шрифт
        cell.alignment = Alignment(horizontal='center', vertical='center')  # Выравнивание

    # Записываем данные книг начиная со второй строки
    for row_num, book in enumerate(books, 2):
        # Основная информация
        ws.cell(row=row_num, column=1).value = book.id
        ws.cell(row=row_num, column=2).value = book.sku or ''
        ws.cell(row=row_num, column=3).value = book.title
        ws.cell(row=row_num, column=4).value = book.author
        ws.cell(row=row_num, column=5).value = book.author_oblozh
        ws.cell(row=row_num, column=6).value = book.genre
        ws.cell(row=row_num, column=7).value = book.publisher
        ws.cell(row=row_num, column=8).value = book.series or ''
        ws.cell(row=row_num, column=9).value = book.publication_year or ''
        ws.cell(row=row_num, column=10).value = book.language

        # Сохранность (преобразуем код в читаемое значение)
        ws.cell(row=row_num, column=11).value = book.get_condition_display() if book.condition else ''

        # Тип переплёта (преобразуем код в читаемое значение)
        ws.cell(row=row_num, column=12).value = book.get_cover_type_display()

        ws.cell(row=row_num, column=13).value = book.pages or ''
        ws.cell(row=row_num, column=14).value = book.isbn or ''

        # Цены (преобразуем Decimal в float)
        ws.cell(row=row_num, column=15).value = float(book.price) if book.price else 0
        ws.cell(row=row_num, column=16).value = float(book.old_price) if book.old_price else ''

        # НДС (преобразуем код в читаемое значение)
        ws.cell(row=row_num, column=17).value = book.get_vat_rate_display()

        ws.cell(row=row_num, column=18).value = book.stock

        # Размеры и вес (преобразуем Decimal в float)
        ws.cell(row=row_num, column=19).value = float(book.weight) if book.weight else ''
        ws.cell(row=row_num, column=20).value = float(book.length) if book.length else ''
        ws.cell(row=row_num, column=21).value = float(book.width) if book.width else ''
        ws.cell(row=row_num, column=22).value = float(book.height) if book.height else ''

        # Категория (название, если есть)
        ws.cell(row=row_num, column=23).value = book.category.name if book.category else ''

        # Источник (преобразуем код в читаемое значение)
        ws.cell(row=row_num, column=24).value = book.get_source_display()

        # Дата создания (форматируем)
        ws.cell(row=row_num, column=25).value = book.created_at.strftime('%Y-%m-%d %H:%M:%S')

    # Автоматическая ширина колонок на основе содержимого
    for column in ws.columns:
        max_length = 0
        column_letter = column[0].column_letter

        # Находим максимальную длину текста в колонке
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass

        # Устанавливаем ширину с небольшим запасом, но не более 50 символов
        adjusted_width = min(max_length + 2, 50)
        ws.column_dimensions[column_letter].width = adjusted_width

    # Создаем HTTP ответ с Excel файлом
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="books_export.xlsx"'

    # Сохраняем книгу Excel в ответ
    wb.save(response)
    return response


# def export_ozon_yml(request):
#     """
#     Экспорт книг в YML-формат для загрузки на Ozon.
#
#     ✅ FIX:
#     - OZON_SHOP_ID берётся из settings (не захардкожен)
#     - import yaml перенесён в начало файла
#     - убрана дублирующая логика — файлы сохраняются только в admin.py
#     """
#     if hasattr(request, 'ozon_export_queryset'):
#         books = request.ozon_export_queryset
#     else:
#         books = Book.objects.select_related('category').all()
#
#     # ── Валидация обязательных полей ─────────────────────────────────────────
#     validation_errors = []
#     valid_books = []
#
#     for book in books:
#         errors = []
#
#         if not book.title:
#             errors.append('Название')
#         if not book.price or book.price <= 0:
#             errors.append('Цена')
#         if not book.category or not book.category.ozon_category_id:
#             errors.append('Категория Озон')
#         if book.stock is None or book.stock < 0:
#             errors.append('Остаток на складе')
#         if not book.photos:
#             errors.append('Фотографии')
#
#         if errors:
#             validation_errors.append({
#                 'book_id': book.id,
#                 'title': book.title or 'Без названия',
#                 'errors': errors,
#             })
#         else:
#             valid_books.append(book)
#
#     if validation_errors:
#         lines = ["Следующие товары не могут быть экспортированы (не заполнены обязательные поля):\n"]
#         for err in validation_errors:
#             lines.append(
#                 f"  • Книга ID {err['book_id']}: «{err['title']}» — "
#                 f"отсутствуют: {', '.join(err['errors'])}"
#             )
#         return HttpResponse('\n'.join(lines), content_type='text/plain; charset=utf-8')
#
#     if not valid_books:
#         return HttpResponse(
#             "Нет товаров для экспорта. Убедитесь, что у товаров заполнены все обязательные поля.",
#             content_type='text/plain; charset=utf-8',
#         )
#
#     # ── Формирование YML ─────────────────────────────────────────────────────
#     offers = []
#     base_url = request.build_absolute_uri('/')
#
#     for book in valid_books:
#         pictures = [
#             f"{base_url}media/{photo}"
#             for photo in (book.photos or [])
#         ]
#
#         offer = {
#             'offer_id': str(book.id),
#             'name': book.title,
#             'price': float(book.price),
#             'currency_code': 'RUB',
#             'category_id': book.category.ozon_category_id,
#             'vendor': book.publisher or '',
#             'author': book.author or '',
#             'year': book.publication_year or 0,
#             'isbn': book.isbn or '',
#             'description': book.description or '',
#             'stock': book.stock,
#             'vat': book.vat_rate or '0',
#         }
#
#         if book.old_price:
#             offer['old_price'] = float(book.old_price)
#         if pictures:
#             offer['pictures'] = pictures
#         if book.weight:
#             offer['weight'] = float(book.weight)
#         if book.length and book.width and book.height:
#             offer['depth'] = float(book.length)
#             offer['width'] = float(book.width)
#             offer['height'] = float(book.height)
#
#         offers.append(offer)
#
#     # ✅ FIX: shop_id из настроек, а не захардкоженная заглушка
#     yml_data = {
#         'shop_id': settings.OZON_SHOP_ID,
#         'offers': offers,
#     }
#
#     payload = yaml.dump(
#         yml_data,
#         allow_unicode=True,
#         default_flow_style=False,
#         sort_keys=False,
#     )
#
#     response = HttpResponse(payload, content_type='text/yaml; charset=utf-8')
#     response['Content-Disposition'] = 'attachment; filename="ozon_export.yml"'
#     return response

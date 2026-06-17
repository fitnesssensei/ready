import logging
import os

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, Alignment
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render

from .models import Book, OzonTemplate

logger = logging.getLogger(__name__)


# Маппинг жанров книг на колонки направлений Ozon (колонки 47-72)
GENRE_COLUMN_MAPPING = {
    'business': 47,
    'self_development': 48,
    'psychology': 48,
    'scientific': 49,
    'medicine': 50,
    'law': 51,
    'art_culture': 52,
    'artbook': 52,
    'history': 53,
    'journalism': 54,
    'esoterica_spirituality': 55,
    'cooking': 56,
    'hobby_creativity': 57,
    'home_garden': 58,
    'beauty_health': 59,
    'sports': 59,
    'religion': 60,
    'information_technology': 61,
    'encyclopedia_reference': 63,
    'travel': 64,
    'prose': 65,
    'detective': 66,
    'fantasy': 67,
    'fantastic': 68,
    'romance': 69,
    'epic_folklore': 70,
    'poetry': 71,
    'comic': 72,
    'graphic_novel': 72,
    'manga': 72,
    'manhwa': 72,
    'manhua': 72,
    'ranobe': 72,
}


BOOK_TYPE_OZON_MAPPING = {
    'printed book': 'Печатная книга',
    'second': 'Second-hand книга',
    'bookinist': 'Букинистическое издание',
    'print_on_demand': 'Печать по требованию',
}


BOOK_TYPE_DISPLAY_MAPPING = {
    'printed book': 'Печатная книга',
    'second': 'Б/У',
    'bookinist': 'Букинистическое издание',
    'print_on_demand': 'Печать по требованию',
}


def _ozon_book_type(book: Book) -> str:
    return BOOK_TYPE_OZON_MAPPING.get(book.book_type, 'Печатная книга')


def _ozon_book_type_display(book: Book) -> str:
    return BOOK_TYPE_DISPLAY_MAPPING.get(book.book_type, 'Печатная книга')


def _format_dimensions_cm(book: Book) -> str:
    if book.length and book.width and book.height:
        try:
            l_cm = round(float(book.length) / 10, 1)
            w_cm = round(float(book.width) / 10, 1)
            h_cm = round(float(book.height) / 10, 1)
            return f"{l_cm} x {w_cm} x {h_cm}"
        except (ValueError, TypeError):
            pass
    return ''


def _format_dimensions_mm(book: Book) -> str:
    if book.length and book.width and book.height:
        try:
            return f"{int(float(book.length))} x {int(float(book.width))} x {int(float(book.height))}"
        except (ValueError, TypeError):
            pass
    return ''


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
    Загружает активный шаблон Excel из модели OzonTemplate и заполняет
    данными книг с автоматическим маппингом всех 78 колонок шаблона.
    Особенности:
        - Маппинг всех колонок шаблона на поля модели Book
        - Автоматическое определение направления (колонки 47-72)
        - Форматирование размеров в см и мм
        - Тип* и Тип книги определяются из book_type
    """
    if hasattr(request, 'ozon_export_queryset'):
        books = request.ozon_export_queryset
    else:
        books = Book.objects.select_related('category').all()
    template = OzonTemplate.objects.filter(is_active=True).first()
    if not template:
        return HttpResponse(
            "Ошибка: Не найден активный шаблон Ozon. Загрузите шаблон через админку.",
            content_type='text/plain; charset=utf-8',
            status=400
        )
    template_path = os.path.join(settings.MEDIA_ROOT, template.file.name)
    if not os.path.exists(template_path):
        return HttpResponse(
            f"Ошибка: Файл шаблона не найден: {template.file.name}",
            content_type='text/plain; charset=utf-8',
            status=404
        )
    media_base_url = getattr(settings, 'MEDIA_BASE_URL',
                              request.build_absolute_uri(settings.MEDIA_URL))
    try:
        wb = load_workbook(template_path)
        if 'Шаблон' not in wb.sheetnames:
            return HttpResponse(
                "Ошибка: В шаблоне не найден лист 'Шаблон'",
                content_type='text/plain; charset=utf-8',
                status=400
            )
        ws = wb['Шаблон']
        header_row = 2
        headers = {}
        for col_num in range(1, ws.max_column + 1):
            cell_value = ws.cell(row=header_row, column=col_num).value
            if cell_value:
                header_clean = str(cell_value).replace('\n', ' ').strip().lower()
                headers[header_clean] = col_num
        field_mapping = {
            'артикул*': lambda book: book.sku or '',
            'название товара': lambda book: book.title or '',
            'цена, руб.*': lambda book: float(book.price) if book.price else '',
            'цена до скидки, руб.': lambda book: float(book.old_price) if book.old_price else '',
            'ндс, %*': lambda book: int(book.vat_rate) if book.vat_rate else 0,
            'sku': lambda book: book.sku or '',
            'штрихкод (серийный номер / ean)': lambda book: book.isbn or '',
            'вес в упаковке, г*': lambda book: int(float(book.weight)) if book.weight else '',
            'ширина упаковки, мм*': lambda book: int(float(book.width)) if book.width else '',  # убрал  / 10 
            'высота упаковки, мм*': lambda book: int(float(book.height)) if book.height else '',  # убрал  / 10
            'длина упаковки, мм*': lambda book: int(float(book.length)) if book.length else '',  # убрал  / 10
            'ссылка на главное фото*': lambda book: (
                f'{media_base_url}{book.photos[0]}' if book.photos else ''
            ),
            'ссылки на дополнительные фото': lambda book: (
                ', '.join(f'{media_base_url}{photo}' for photo in book.photos[1:])
                if len(book.photos) > 1 else ''
            ),
            'артикул фото': lambda book: book.sku or '',
            'автор на обложке*': lambda book: (
                book.author_oblozh if book.author_oblozh else (book.author or '')
            ),
            'автор': lambda book: book.author or '',
            'тип обложки': lambda book: book.get_cover_type_display() or '',
            'тип книги': lambda book: _ozon_book_type_display(book),
            'тип*': lambda book: _ozon_book_type(book),
            'бренд*': lambda book: book.publisher or 'Нет бренда',
            'тн вэд коды еаэс*': lambda book: book.tnved_code or '',
            'направление*': lambda book: book.get_genre_display() or '',
            'целевая аудитория литературы': lambda book: book.get_target_audience_display() or '',
            '#хештеги': lambda book: book.hashtags or '',
            'аннотация': lambda book: book.description or '',
            'издательство': lambda book: book.publisher or '',
            'серия': lambda book: book.series or '',
            'год выпуска': lambda book: book.publication_year or '',
            'тип бумаги в книге': lambda book: book.get_paper_type_display() or '',
            'язык издания': lambda book: book.get_language_display() or 'Русский',
            'количество страниц': lambda book: book.pages or '',
            #'размер упаковки (длина х ширина х высота), см': lambda book: _format_dimensions_cm(book),
            #'размеры, мм': lambda book: _format_dimensions_mm(book),
            'вес товара, г': lambda book: int(float(book.weight)) if book.weight else '',
            'isbn': lambda book: book.isbn or '',
            'сохранность книги': lambda book: book.get_condition_display() or '',
            'возрастные ограничения': lambda book: book.get_age_restrictions_display() or '',
            'признак 18+': lambda book: 'да' if book.age_restrictions == '18+' else '',
        }
        GENRE_TO_DISPLAY = {code: display for code, display in Book.GENRE}
        current_row = 5
        for idx, book in enumerate(books, 1):
            ws.cell(row=current_row, column=1).value = idx
            for header_name, col_num in headers.items():
                if header_name in field_mapping:
                    try:
                        value = field_mapping[header_name](book)
                        ws.cell(row=current_row, column=col_num).value = value
                    except Exception as e:
                        logger.warning(
                            f"Ошибка при заполнении '{header_name}' "
                            f"для книги {book.id} ({book.sku}): {e}"
                        )
                        ws.cell(row=current_row, column=col_num).value = ''
            if book.genre and book.genre in GENRE_COLUMN_MAPPING:
                col_num = GENRE_COLUMN_MAPPING[book.genre]
                display_name = GENRE_TO_DISPLAY.get(book.genre, '')
                if display_name:
                    ws.cell(row=current_row, column=col_num).value = display_name
            current_row += 1
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="ozon_export_{len(books)}_books.xlsx"'
        wb.save(response)
        return response
    except Exception as e:
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
        'НДС', 'Остаток', 'Вес (г)', 'Длина (мм)', 'Ширина (мм)',
        'Высота (мм)', 'Категория', 'Источник', 'Дата создания'
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

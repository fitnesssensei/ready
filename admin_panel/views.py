import base64
import logging
import os
import unicodedata

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, Alignment
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render

from .models import Book, OzonTemplate

logger = logging.getLogger(__name__)




BOOK_TYPE_OZON_MAPPING = {
    'printed book': 'Печатная книга',
    'second': 'Second-hand книга',
    'bookinist': 'Букинистика',
    'print_on_demand': 'Печать по требованию',
}


BOOK_TYPE_DISPLAY_MAPPING = {
    'printed book': 'Печатная книга',
    'second': 'Б/У',
    'bookinist': 'Букинистика',
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
def _slugify_name(name: str) -> str:
    """ASCII-safe slug for filenames: lower, replace spaces with _, strip non-ascii."""
    normalized = unicodedata.normalize('NFKD', name)
    ascii_bytes = normalized.encode('ascii', 'ignore').decode('ascii')
    slug = ascii_bytes.lower().replace(' ', '_').replace('/', '_')
    slug = ''.join(ch for ch in slug if ch.isalnum() or ch == '_')
    return slug[:50] or 'template'


def _ozon_headers_and_mapping(ws, media_base_url):
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
        'штрихкод (серийный номер / ean)': lambda book: '',
        'isbn': lambda book: book.isbn or '',
        'isbn*': lambda book: book.isbn or '',
        'вес в упаковке, г*': lambda book: int(float(book.weight)) if book.weight else '',
        'ширина упаковки, мм*': lambda book: int(float(book.width)) if book.width else '',
        'высота упаковки, мм*': lambda book: int(float(book.height)) if book.height else '',
        'длина упаковки, мм*': lambda book: int(float(book.length)) if book.length else '',
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
        'тип книги': lambda book: _ozon_book_type(book),
        'тип*': lambda book: 'Печатная книга',
        'бренд*': lambda book: book.publisher or 'Нет бренда',
        'тн вэд коды еаэс*': lambda book: book.tnved_code or '',
        'направление*': lambda book: book.get_genre_display() or '',
        'целевая аудитория литературы': lambda book: book.get_target_audience_display() or '',
        '#хештеги': lambda book: book.hashtags or '',
        'аннотация': lambda book: book.description or '',
        'иллюстратор': lambda book: book.illustrator or '',
        'переводчик': lambda book: book.translator or '',
        'издательство': lambda book: book.publisher or '',
        'серия': lambda book: book.series or '',
        'год выпуска': lambda book: book.publication_year or '',
        'тип бумаги в книге': lambda book: book.get_paper_type_display() or '',
        'язык издания': lambda book: book.get_language_display() or 'Русский',
        'количество страниц': lambda book: book.pages or '',
        'вес товара, г': lambda book: int(float(book.weight)) if book.weight else '',
        'сохранность книги': lambda book: book.get_condition_display() or '',
        'возрастные ограничения': lambda book: book.get_age_restrictions_display() or '',
        'признак 18+': lambda book: book.is_adult,
    }
    return headers, field_mapping


def _fill_ozon_sheet(ws, books, headers, field_mapping):
    current_row = 5
    for idx, book in enumerate(books, 1):
        ws.cell(row=current_row, column=1).value = idx
        for header_name, col_num in headers.items():
            mapper = field_mapping.get(header_name) or field_mapping.get(header_name.rstrip('*'))
            if mapper:
                try:
                    value = mapper(book)
                    ws.cell(row=current_row, column=col_num).value = value
                except Exception as e:
                    logger.warning(
                        f"Ошибка при заполнении '{header_name}' "
                        f"для книги {book.id} ({book.sku}): {e}"
                    )
                    ws.cell(row=current_row, column=col_num).value = ''
        current_row += 1


def export_books_to_ozon_template(request):
    """
    Экспорт выбранных книг в шаблон(ы) Ozon.
    Поддерживает несколько активных шаблонов с распределением по publication_year.
    Если активен 1 шаблон — возвращает один .xlsx.
    Если >= 2 — возвращает ZIP-архив (.zip) со всеми сгенерированными .xlsx файлами.
    """
    import tempfile

    if hasattr(request, 'ozon_export_queryset'):
        books = list(request.ozon_export_queryset.select_related('category').all())
    else:
        books = list(Book.objects.select_related('category').all())

    templates = list(OzonTemplate.objects.filter(is_active=True).order_by('year_from'))
    if not templates:
        return HttpResponse(
            "Ошибка: Не найден активный шаблон Ozon. Загрузите шаблон через админку.",
            content_type='text/plain; charset=utf-8',
            status=400
        )

    media_base_url = getattr(settings, 'MEDIA_BASE_URL',
                              request.build_absolute_uri(settings.MEDIA_URL))

    def _in_range(book_year, tpl):
        if book_year is None:
            return False
        if tpl.year_from is not None and book_year < tpl.year_from:
            return False
        if tpl.year_to is not None and book_year > tpl.year_to:
            return False
        return True

    templates_any_range = [
        t for t in templates
        if t.year_from is None and t.year_to is None
    ]
    templates_with_range = [
        t for t in templates
        if t.year_from is not None or t.year_to is not None
    ]

    def _range_width(tpl):
        if tpl.year_from is None and tpl.year_to is None:
            return float('inf')
        a = tpl.year_from if tpl.year_from is not None else float('-inf')
        b = tpl.year_to if tpl.year_to is not None else float('inf')
        return b - a

    templates_with_range.sort(key=lambda t: (_range_width(t), -(t.year_from or 0)))

    template_groups = {t: [] for t in templates}

    for book in books:
        placed = False
        for tpl in templates_with_range:
            if _in_range(book.publication_year, tpl):
                template_groups[tpl].append(book)
                placed = True
                break
        if not placed:
            if templates_any_range:
                tpl = min(
                    templates_any_range,
                    key=lambda t: len(template_groups[t])
                )
                template_groups[tpl].append(book)
            elif templates:
                template_groups[templates[0]].append(book)

    def _build_xlsx(tpl, tpl_books):
        tpl_path = os.path.join(settings.MEDIA_ROOT, tpl.file.name)
        if not os.path.exists(tpl_path):
            raise FileNotFoundError(f"Файл шаблона не найден: {tpl.file.name}")
        wb = load_workbook(tpl_path)
        if 'Шаблон' not in wb.sheetnames:
            raise ValueError(f"В шаблоне '{tpl.name}' нет листа 'Шаблон'")
        ws = wb['Шаблон']
        headers, field_mapping = _ozon_headers_and_mapping(ws, media_base_url)
        _fill_ozon_sheet(ws, tpl_books, headers, field_mapping)
        tmp = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
        wb.save(tmp.name)
        tmp.close()
        return tmp.name, len(tpl_books)

    results = []
    for tpl in templates:
        tpl_books = template_groups.get(tpl, [])
        if not tpl_books:
            continue
        tmp_path, count = _build_xlsx(tpl, tpl_books)
        results.append((tpl, tpl_books, tmp_path, count))

    if not results:
        return HttpResponse(
            "Нет книг, попадающих под условия активных шаблонов.",
            content_type='text/plain; charset=utf-8',
            status=400
        )

    # --- Один шаблон → возвращаем .xlsx напрямую ---
    if len(results) == 1:
        tpl, tpl_books, tmp_path, count = results[0]
        with open(tmp_path, 'rb') as f:
            file_data = f.read()
        os.unlink(tmp_path)
        filename = f"{_slugify_name(tpl.name)}_{count}_books.xlsx"
        response = HttpResponse(
            file_data,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    # --- Несколько шаблонов → возвращаем ZIP-архив ---
    from io import BytesIO
    import zipfile

    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for tpl, tpl_books, tmp_path, count in results:
            filename = f"{_slugify_name(tpl.name)}_{count}_books.xlsx"
            zf.write(tmp_path, arcname=filename)
            os.unlink(tmp_path)

    zip_buffer.seek(0)
    response = HttpResponse(
        zip_buffer.getvalue(),
        content_type='application/zip'
    )
    response['Content-Disposition'] = 'attachment; filename="ozon_templates_export.zip"'
    return response


def export_books_to_excel(request):
    """
    Экспорт выбранных книг в стандартный Excel файл.
    Создает Excel файл (.xlsx) со всеми данными книг в табличном формате.
    Используется библиотека openpyxl для работы с Excel.
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

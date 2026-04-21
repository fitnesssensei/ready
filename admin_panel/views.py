import logging

import yaml
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render

from .models import Book

logger = logging.getLogger(__name__)


def dashboard(request):
    return render(request, 'admin_panel/dashboard.html')


def products(request):
    return render(request, 'admin_panel/products.html')


def orders(request):
    return render(request, 'admin_panel/orders.html')


def customers(request):
    return render(request, 'admin_panel/customers.html')


def export_ozon_yml(request):
    """
    Экспорт книг в YML-формат для загрузки на Ozon.

    ✅ FIX:
    - OZON_SHOP_ID берётся из settings (не захардкожен)
    - import yaml перенесён в начало файла
    - убрана дублирующая логика — файлы сохраняются только в admin.py
    """
    if hasattr(request, 'ozon_export_queryset'):
        books = request.ozon_export_queryset
    else:
        books = Book.objects.select_related('category').all()

    # ── Валидация обязательных полей ─────────────────────────────────────────
    validation_errors = []
    valid_books = []

    for book in books:
        errors = []

        if not book.title:
            errors.append('Название')
        if not book.price or book.price <= 0:
            errors.append('Цена')
        if not book.category or not book.category.ozon_category_id:
            errors.append('Категория Озон')
        if book.stock is None or book.stock < 0:
            errors.append('Остаток на складе')
        if not book.photos:
            errors.append('Фотографии')

        if errors:
            validation_errors.append({
                'book_id': book.id,
                'title': book.title or 'Без названия',
                'errors': errors,
            })
        else:
            valid_books.append(book)

    if validation_errors:
        lines = ["Следующие товары не могут быть экспортированы (не заполнены обязательные поля):\n"]
        for err in validation_errors:
            lines.append(
                f"  • Книга ID {err['book_id']}: «{err['title']}» — "
                f"отсутствуют: {', '.join(err['errors'])}"
            )
        return HttpResponse('\n'.join(lines), content_type='text/plain; charset=utf-8')

    if not valid_books:
        return HttpResponse(
            "Нет товаров для экспорта. Убедитесь, что у товаров заполнены все обязательные поля.",
            content_type='text/plain; charset=utf-8',
        )

    # ── Формирование YML ─────────────────────────────────────────────────────
    offers = []
    base_url = request.build_absolute_uri('/')

    for book in valid_books:
        pictures = [
            f"{base_url}media/{photo}"
            for photo in (book.photos or [])
        ]

        offer = {
            'offer_id': str(book.id),
            'name': book.title,
            'price': float(book.price),
            'currency_code': 'RUB',
            'category_id': book.category.ozon_category_id,
            'vendor': book.publisher or '',
            'author': book.author or '',
            'year': book.publication_year or 0,
            'isbn': book.isbn or '',
            'description': book.description or '',
            'stock': book.stock,
            'vat': book.vat_rate or '0',
        }

        if book.old_price:
            offer['old_price'] = float(book.old_price)
        if pictures:
            offer['pictures'] = pictures
        if book.weight:
            offer['weight'] = float(book.weight)
        if book.length and book.width and book.height:
            offer['depth'] = float(book.length)
            offer['width'] = float(book.width)
            offer['height'] = float(book.height)

        offers.append(offer)

    # ✅ FIX: shop_id из настроек, а не захардкоженная заглушка
    yml_data = {
        'shop_id': settings.OZON_SHOP_ID,
        'offers': offers,
    }

    payload = yaml.dump(
        yml_data,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
    )

    response = HttpResponse(payload, content_type='text/yaml; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="ozon_export.yml"'
    return response

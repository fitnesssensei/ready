import logging
import re
import uuid

from django.conf import settings
from django.contrib import admin
from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import path, reverse

from .models import Book, Category, EksmoBook, ManualBook, OzonTemplate
from .widgets import MultipleImageWidget

logger = logging.getLogger(__name__)

EKSMO_SEARCH_LIMIT = 20


def _normalize_isbn(raw: str) -> str:
    return ''.join(c for c in (raw or '') if c.isdigit())


def _is_isbn_query(query: str) -> bool:
    if not query:
        return False
    compact = re.sub(r'[\s\-]', '', query)
    if not compact:
        return False
    digits = sum(c.isdigit() for c in compact)
    return digits >= 4 and digits == len(compact)


def _search_eksmo_books(query: str):
    """
    Поиск книг из каталога Эксмо.
    
    Логика поиска:
    - Если запрос похож на ISBN (только цифры и дефисы), ищем по ISBN
    - Поиск по ISBN работает независимо от наличия дефисов:
      * Нормализуем запрос (удаляем дефисы и пробелы)
      * Нормализуем ISBN в базе данных (удаляем дефисы и пробелы)
      * Сравниваем нормализованные значения
    - Иначе ищем по названию книги
    
    Args:
        query: Строка поиска (может быть ISBN или название)
        
    Returns:
        QuerySet с найденными книгами
    """
    qs = Book.objects.filter(source=Book.SOURCE_EKSMO)
    q = query.strip()
    if len(q) < 2:
        return qs.none()
    
    # Проверяем, является ли запрос ISBN-подобным
    if _is_isbn_query(q):
        # Нормализуем запрос: удаляем все дефисы и пробелы, оставляем только цифры
        query_digits = _normalize_isbn(q)
        
        # Получаем все книги и фильтруем в Python
        # Это нужно потому что в базе ISBN могут храниться с дефисами или без
        # и нам нужно нормализовать оба значения для корректного сравнения
        all_books = list(qs)
        filtered_books = []
        
        for book in all_books:
            if not book.isbn:
                continue
            # Нормализуем ISBN из базы данных: удаляем дефисы и пробелы
            book_isbn_normalized = _normalize_isbn(book.isbn)
            # Проверяем, содержится ли нормализованный запрос в нормализованном ISBN
            if query_digits in book_isbn_normalized:
                filtered_books.append(book.pk)
        
        # Возвращаем отфильтрованный queryset по списку ID
        if filtered_books:
            return qs.filter(pk__in=filtered_books)
        return qs.none()
    
    # Если это не ISBN-запрос, ищем по названию
    return qs.filter(title__icontains=q)


def _book_to_form_dict(book: Book, *, for_manual_template: bool = False) -> dict:
    price = '' if for_manual_template else book.price
    old_price = '' if for_manual_template else (book.old_price or '')
    stock = 1 if for_manual_template else book.stock
    return {
        'title': book.title,
        'author': book.author,
        'author_oblozh': book.author_oblozh,
        'genre': book.genre,
        'publisher': book.publisher,
        'series': book.series or '',
        'publication_year': book.publication_year or '',
        'language': book.language,
        'condition': book.condition or '',
        'cover_type': book.cover_type,
        'pages': book.pages or '',
        'description': book.description,
        'isbn': book.isbn or '',
        'price': price,
        'old_price': old_price,
        'vat_rate': book.vat_rate,
        'stock': stock,
        'weight': book.weight or '',
        'length': book.length or '',
        'width': book.width or '',
        'height': book.height or '',
        'category': book.category_id or '',
        'publication_date': book.publication_date.isoformat() if book.publication_date else '',
        'photos': book.photos or [],
    }


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'ozon_category_id', 'created_at')
    search_fields = ('name', 'ozon_category_id')
    ordering = ('name',)


@admin.register(OzonTemplate)
class OzonTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'uploaded_at', 'file')
    list_filter = ('is_active', 'uploaded_at')
    search_fields = ('name', 'description')
    ordering = ('-uploaded_at',)
    readonly_fields = ('uploaded_at',)

    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'file', 'description', 'is_active')
        }),
        ('Служебное', {
            'fields': ('uploaded_at',),
            'classes': ('collapse',),
        }),
    )


class BaseBookAdmin(admin.ModelAdmin):
    change_form_template = 'admin_panel/change_form.html'
    actions = ['export_selected_to_excel', 'export_selected_to_ozon']

    list_display = (
        'sku', 'title', 'category', 'author', 'author_oblozh', 'genre',
        'publisher', 'series', 'language', 'condition', 'cover_type', 'pages',
        'price', 'old_price', 'stock', 'publication_year', 'created_at',
    )
    list_filter = (
        'category', 'genre', 'publisher', 'language', 'condition',
        'cover_type', 'vat_rate', 'publication_year', 'publication_date', 'created_at',
    )
    search_fields = (
        'sku', 'title', 'author', 'author_oblozh', 'genre',
        'publisher', 'series', 'language', 'isbn',
    )
    ordering = ('-created_at',)
    readonly_fields = ('source', 'created_at', 'updated_at')

    fieldsets = (
        ('Основная информация', {
            'fields': (
                'sku', 'title', 'category', 'author', 'author_oblozh', 'genre',
                'publisher', 'series', 'publication_year', 'language', 'condition',
                'cover_type', 'pages', 'photos', 'description',
            )
        }),
        ('Коммерческая информация', {
            'fields': ('price', 'old_price', 'vat_rate', 'stock', 'isbn')
        }),
        ('Логистика', {
            'fields': ('weight', 'length', 'width', 'height')
        }),
        ('Служебное', {
            'fields': ('source', 'publication_date', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == 'photos':
            kwargs['widget'] = MultipleImageWidget()
            kwargs['required'] = False
        return super().formfield_for_dbfield(db_field, **kwargs)

    def save_model(self, request, obj, form, change):
        existing_photos = form.cleaned_data.get('photos') or []
        if not isinstance(existing_photos, list):
            existing_photos = []

        new_photo_paths = []
        if 'photos' in request.FILES:
            for uploaded_file in request.FILES.getlist('photos'):
                if not uploaded_file:
                    continue
                ext = uploaded_file.name.rsplit('.', 1)[-1].lower()
                unique_name = f'{uuid.uuid4()}.{ext}'
                saved_path = default_storage.save(f'book_photos/{unique_name}', uploaded_file)
                new_photo_paths.append(saved_path)
                logger.debug("Saved book photo: %s", saved_path)

        obj.photos = (existing_photos + new_photo_paths)[:10]
        self._set_source(obj)
        super().save_model(request, obj, form, change)

    def _set_source(self, obj):
        raise NotImplementedError

    def export_selected_to_excel(self, request, queryset):
        from .views import export_books_to_excel
        request.excel_export_queryset = queryset
        return export_books_to_excel(request)

    export_selected_to_excel.short_description = "Экспортировать выбранные в Excel"

    def export_selected_to_ozon(self, request, queryset):
        from .views import export_books_to_ozon_template
        request.ozon_export_queryset = queryset
        return export_books_to_ozon_template(request)

    export_selected_to_ozon.short_description = "Экспортировать выбранные в шаблон Ozon"

    # def export_selected_ozon(self, request, queryset):
    #     from .views import export_ozon_yml
    #     request.ozon_export_queryset = queryset
    #     return export_ozon_yml(request)

    # export_selected_ozon.short_description = "Экспортировать выбранные в Ozon YML"


@admin.register(Book)
class BookRedirectAdmin(admin.ModelAdmin):
    """Старые ссылки /admin/admin_panel/book/ → каталоги manual/eksmo."""

    def has_module_permission(self, request):
        return False

    def changelist_view(self, request, extra_context=None):
        return redirect('admin:admin_panel_manualbook_changelist')

    def add_view(self, request, form_url='', extra_context=None):
        return redirect('admin:admin_panel_manualbook_add')

    def change_view(self, request, object_id, form_url='', extra_context=None):
        book = Book.objects.filter(pk=object_id).only('source').first()
        if not book:
            return redirect('admin:admin_panel_manualbook_changelist')
        if book.source == Book.SOURCE_EKSMO:
            return redirect('admin:admin_panel_eksombook_change', args=[object_id])
        return redirect('admin:admin_panel_manualbook_change', args=[object_id])

    def delete_view(self, request, object_id, extra_context=None):
        book = Book.objects.filter(pk=object_id).only('source').first()
        if not book:
            return redirect('admin:admin_panel_manualbook_changelist')
        if book.source == Book.SOURCE_EKSMO:
            return redirect('admin:admin_panel_eksombook_delete', args=[object_id])
        return redirect('admin:admin_panel_manualbook_delete', args=[object_id])


@admin.register(ManualBook)
class ManualBookAdmin(BaseBookAdmin):
    change_form_template = 'admin_panel/manualbook_change_form.html'
    change_list_template = 'admin_panel/change_list.html'

    def get_queryset(self, request):
        return super().get_queryset(request).filter(source=Book.SOURCE_MANUAL)

    def _set_source(self, obj):
        obj.source = Book.SOURCE_MANUAL

    def save_model(self, request, obj, form, change):
        if not change:
            obj.pk = None
        super().save_model(request, obj, form, change)

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                'search-eksmo/',
                self.admin_site.admin_view(self.search_eksmo_view),
                name='admin_panel_manualbook_search_eksmo',
            ),
            path(
                'eksmo-template/<int:book_id>/',
                self.admin_site.admin_view(self.eksmo_template_view),
                name='admin_panel_manualbook_eksmo_template',
            ),
        ]
        return custom + urls

    def _eksmo_admin_context(self):
        return {
            'eksmo_search_url': reverse('admin:admin_panel_manualbook_search_eksmo'),
            'eksmo_template_url_tpl': reverse(
                'admin:admin_panel_manualbook_eksmo_template',
                args=[0],
            ).replace('/0/', '/__ID__/'),
            'media_url': settings.MEDIA_URL,
        }

    def add_view(self, request, form_url='', extra_context=None):
        extra_context = {**(extra_context or {}), **self._eksmo_admin_context()}
        return super().add_view(request, form_url, extra_context)

    def search_eksmo_view(self, request):
        query = (request.GET.get('q') or '').strip()
        books = (
            _search_eksmo_books(query)
            .order_by('title')
            .values('id', 'title', 'author', 'isbn')[:EKSMO_SEARCH_LIMIT]
        )
        return JsonResponse({'results': list(books)})

    def eksmo_template_view(self, request, book_id):
        book = Book.objects.filter(pk=book_id, source=Book.SOURCE_EKSMO).first()
        if not book:
            return JsonResponse({'error': 'Книга не найдена в каталоге Эксмо'}, status=404)
        return JsonResponse({'book': _book_to_form_dict(book, for_manual_template=True)})


@admin.register(EksmoBook)
class EksmoBookAdmin(BaseBookAdmin):
    def get_queryset(self, request):
        return super().get_queryset(request).filter(source=Book.SOURCE_EKSMO)

    def _set_source(self, obj):
        obj.source = Book.SOURCE_EKSMO

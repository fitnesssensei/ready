"""
Экшен Django Admin: «Экспортировать выбранные в шаблон Яндекс Маркета».

Подключается к BookAdmin через monkey-patch — файл admin.py (и весь Ozon-код)
не изменяется. Активация: импорт этого модуля в admin_panel/apps.py (ready()).
"""
import logging

from .yandex_market import export_books_to_yandex_template

logger = logging.getLogger(__name__)


def export_selected_to_yandex(self, request, queryset):
    """Admin action: экспорт выбранных книг в шаблон Яндекс Маркета."""
    from .models import Book

    # Поддержка Book/EksmoBook/ManualBook прокси-моделей через базовый Book
    if queryset.model is not Book:
        queryset = Book.objects.filter(pk__in=queryset.values_list('pk', flat=True))
    request.yandex_export_queryset = queryset
    return export_books_to_yandex_template(request)


export_selected_to_yandex.short_description = (
    "Экспортировать выбранные в шаблон Яндекс Маркета"
)


def register_yandex_admin_actions():
    """Добавляет экшен в BookAdmin и админку шаблонов Яндекса (idempotent,
    admin.py не трогаем)."""

    from django.contrib import admin

    from .models import Book, YandexTemplate

    # --- 1. Экшен экспорта на странице книг ---
    try:
        book_admin = admin.site._registry.get(Book)
    except Exception as e:
        book_admin = None
        logger.warning(f"Яндекс: не удалось найти BookAdmin: {e}")

    if book_admin is not None:
        admin_cls = type(book_admin)

        if not hasattr(admin_cls, 'export_selected_to_yandex'):
            admin_cls.export_selected_to_yandex = export_selected_to_yandex

        if 'export_selected_to_yandex' not in admin_cls.actions:
            admin_cls.actions = list(admin_cls.actions) + ['export_selected_to_yandex']
            logger.info("Яндекс: экшен экспорта добавлен в %s", admin_cls.__name__)

    # --- 2. Админка шаблонов Яндекс Маркета ---
    if YandexTemplate not in admin.site._registry:
        @admin.register(YandexTemplate)
        class YandexTemplateAdmin(admin.ModelAdmin):
            """
            Админка для управления шаблонами Яндекс Маркета
            (зеркально OzonTemplateAdmin).
            """
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

    # --- 3. Ссылка на шаблоны Яндекса на странице шаблонов Ozon ---
    # Инлайн невозможен (нет FK на OzonTemplate), поэтому шаблоны Яндекса
    # добавляются на отдельной странице «Шаблоны Яндекс Маркета», которая
    # отображается в том же разделе админки, что и «Шаблоны Ozon».
    from .models import OzonTemplate

    ozon_admin = admin.site._registry.get(OzonTemplate)
    if ozon_admin is not None:
        ozon_admin_cls = type(ozon_admin)

        if not hasattr(ozon_admin_cls, '_yandex_link_added'):
            # Заметка со ссылкой на шаблоны Яндекса на страницах добавления/
            # редактирования шаблона Ozon (через стандартный messages).
            from django.contrib import messages
            from django.urls import reverse
            from django.utils.html import format_html

            original_change_view = ozon_admin_cls.change_view
            original_add_view = ozon_admin_cls.add_view

            def _notify_yandex(self, request):
                yandex_url = reverse('admin:admin_panel_yandextemplate_add')
                messages.info(
                    request,
                    format_html(
                        '📄 Шаблоны <b>Яндекс Маркета</b> добавляются '
                        '<a href="{}"><b>здесь</b></a> (раздел «Шаблоны Яндекс Маркета»).',
                        yandex_url,
                    ),
                )

            def change_view_with_yandex(self, request, object_id, *args, **kwargs):
                _notify_yandex(self, request)
                return original_change_view(self, request, object_id, *args, **kwargs)

            def add_view_with_yandex(self, request, *args, **kwargs):
                _notify_yandex(self, request)
                return original_add_view(self, request, *args, **kwargs)

            ozon_admin_cls.change_view = change_view_with_yandex
            ozon_admin_cls.add_view = add_view_with_yandex
            ozon_admin_cls._yandex_link_added = True
            logger.info("Яндекс: заметка-ссылка добавлена в %s", ozon_admin_cls.__name__)




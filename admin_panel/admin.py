import json
import logging
import uuid

from django import forms
from django.contrib import admin
from django.core.files.storage import default_storage

from .models import Book, Category
from .widgets import MultipleImageWidget

logger = logging.getLogger(__name__)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'ozon_category_id', 'created_at')
    search_fields = ('name', 'ozon_category_id')
    ordering = ('name',)


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    change_form_template = 'admin_panel/change_form.html'
    change_list_template = 'admin_panel/change_list.html'
    actions = ['export_selected_ozon']

    list_display = (
        'sku', 'title', 'category', 'author', 'author_oblozh', 'genre',
        'publisher', 'series', 'language', 'condition', 'cover_type', 'pages',
        'price', 'old_price', 'stock', 'publication_year', 'created_at',
    )
    list_filter = (
        'category', 'genre', 'publisher', 'language', 'condition',
        'cover_type', 'vat_rate', 'publication_year', 'publication_date', 'created_at',
    )
    search_fields = ('sku', 'title', 'author', 'author_oblozh', 'genre', 'publisher', 'series', 'language', 'isbn')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Основная информация', {
            'fields': (
                'sku', 'title', 'category', 'author', 'author_oblozh', 'genre',
                'publisher', 'series', 'publication_year', 'language', 'condition', 'cover_type', 'pages',
                'photos', 'description',
            )
        }),
        ('Коммерческая информация', {
            'fields': ('price', 'old_price', 'vat_rate', 'stock', 'isbn')
        }),
        ('Логистика', {
            'fields': ('weight', 'length', 'width', 'height')
        }),
        ('Даты', {
            'fields': ('publication_date', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == 'photos':
            kwargs['widget'] = MultipleImageWidget()
            kwargs['required'] = False
        return super().formfield_for_dbfield(db_field, **kwargs)

    def save_model(self, request, obj, form, change):
        """
        ✅ FIX: сохранение файлов только здесь, в одном месте.
        value_from_datadict в виджете возвращает только список существующих путей.
        """
        # form.cleaned_data['photos'] уже содержит список существующих путей
        # (после value_from_datadict виджета)
        existing_photos = form.cleaned_data.get('photos') or []
        if not isinstance(existing_photos, list):
            existing_photos = []

        # Обрабатываем новые загруженные файлы
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

        all_photos = existing_photos + new_photo_paths
        obj.photos = all_photos[:10]  # не более 10 фотографий

        super().save_model(request, obj, form, change)

    def export_selected_ozon(self, request, queryset):
        from .views import export_ozon_yml
        request.ozon_export_queryset = queryset
        return export_ozon_yml(request)

    export_selected_ozon.short_description = "Экспортировать выбранные в Ozon YML"

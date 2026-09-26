"""
Тесты конфигурации фильтров админки книг.

Проверяем, что в боковой панели «База книг» (/admin/admin_panel/eksmobook/)
и «Каталог — админка» (/admin/admin_panel/manualbook/) остался только фильтр
«Период издания», а стандартные (встроенные) фильтры Django убраны.

Тесты написаны на SimpleTestCase: база данных не нужна, поэтому тестовый
раннер не поднимает PostgreSQL и ничего не создаёт в реальной БД.
"""

from django.contrib import admin as django_admin
from django.test import RequestFactory, SimpleTestCase

from admin_panel.admin import (
    BaseBookAdmin,
    PublicationPeriodFilter,
    TopPublisherFilter,
)
from admin_panel.models import EksmoBook, ManualBook

# Встроенные фильтры Django, которые должны быть убраны из сайдбара
STANDARD_FILTERS = ('category', 'genre', 'language', 'book_type')

# Значения (value) фильтра «Период издания» из PublicationPeriodFilter.PERIODS
PERIOD_VALUES = ['to1950', '1951-1990', '1991-2010', 'from2011']


class BookAdminFilterConfigTests(SimpleTestCase):
    """Состав фильтров у BaseBookAdmin и его наследников."""

    def setUp(self):
        # request нужен только для сигнатуры get_list_filter — к БД не обращаемся
        self.request = RequestFactory().get('/admin/admin_panel/eksmobook/')

    def _model_admin(self, model):
        """Возвращает экземпляр ModelAdmin, зарегистрированный для модели."""
        return django_admin.site._registry[model]

    def test_list_filter_only_publication_period(self):
        """В list_filter остался ровно один фильтр — «Период издания»."""
        self.assertEqual(BaseBookAdmin.list_filter, (PublicationPeriodFilter,))

    def test_standard_filters_removed(self):
        """Стандартных (встроенных) фильтров Django в сайдбаре больше нет."""
        for field_name in STANDARD_FILTERS:
            self.assertNotIn(field_name, BaseBookAdmin.list_filter)

    def test_top_publisher_filter_removed_from_sidebar(self):
        """Фильтр издательств убран из сайдбара, но класс остался в модуле."""
        self.assertNotIn(TopPublisherFilter, BaseBookAdmin.list_filter)
        # Класс импортируется в deploy/measure_admin.py, поэтому не удаляем его
        self.assertTrue(issubclass(TopPublisherFilter, django_admin.SimpleListFilter))

    def test_both_pages_share_same_filters(self):
        """«База книг» и «Каталог — админка» показывают один и тот же фильтр."""
        for model in (EksmoBook, ManualBook):
            model_admin = self._model_admin(model)
            self.assertEqual(
                tuple(model_admin.get_list_filter(self.request)),
                (PublicationPeriodFilter,),
            )

    def test_period_filter_has_static_lookups(self):
        """«Период издания» — статический список значений, без запросов к БД."""
        model_admin = self._model_admin(EksmoBook)
        period_filter = PublicationPeriodFilter(
            self.request, {}, EksmoBook, model_admin,
        )
        lookups = period_filter.lookups(self.request, model_admin)
        self.assertEqual([value for value, _label in lookups], PERIOD_VALUES)

    def test_list_display_has_no_duplicates(self):
        """Ни один столбец не указан в list_display дважды.

        Дубликат в list_display Django не отсекает и системным чеком не ловит
        (проверка дублей есть только для fields/fieldsets/exclude), а колонка
        просто рендерится два раза — так было с 'pages'.
        """
        for model in (EksmoBook, ManualBook):
            columns = list(self._model_admin(model).get_list_display(None))
            duplicates = sorted({name for name in columns if columns.count(name) > 1})
            self.assertEqual(
                duplicates, [], f'{model.__name__}: дубли в list_display: {duplicates}',
            )

    def test_pages_column_listed_once(self):
        """Колонка «Страницы» (pages) выводится ровно один раз."""
        for model in (EksmoBook, ManualBook):
            columns = list(self._model_admin(model).get_list_display(None))
            self.assertEqual(columns.count('pages'), 1, f'{model.__name__}: pages')


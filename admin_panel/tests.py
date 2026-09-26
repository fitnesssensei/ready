"""
Тесты конфигурации фильтров админки книг.

Проверяем, что стандартные (встроенные) фильтры Django убраны из обеих страниц,
в «База книг» (/admin/admin_panel/eksmobook/) остался только «Период издания»,
а в «Каталог — админка» (/admin/admin_panel/manualbook/) добавлен фильтр
«Кем добавлена» с выбором сразу нескольких пользователей.

Тесты написаны на SimpleTestCase: база данных не нужна — кэш фильтра готовится
вручную, а SQL компилируется без выполнения. Поэтому тестовый раннер не
поднимает PostgreSQL и ничего не создаёт в реальной БД.
"""

from unittest.mock import patch
from urllib.parse import parse_qs

from django.contrib import admin as django_admin
from django.contrib.admin.views.main import ChangeList
from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.test import RequestFactory, SimpleTestCase

from admin_panel.admin import (
    BaseBookAdmin,
    CreatedByFilter,
    PublicationPeriodFilter,
    TopPublisherFilter,
)
from admin_panel.models import Book, EksmoBook, ManualBook

# Встроенные фильтры Django, которые должны быть убраны из сайдбара
STANDARD_FILTERS = ('category', 'genre', 'language', 'book_type')

# Значения (value) фильтра «Период издания» из PublicationPeriodFilter.PERIODS
PERIOD_VALUES = ['to1950', '1951-1990', '1991-2010', 'from2011']

# Значения фильтра «Кем добавлена»: (значение в query-строке, подпись в сайдбаре)
CREATED_BY_CHOICES = [('1', 'admin (5)'), ('7', 'manager (2)')]
NO_AUTHOR_CHOICE = ('none', 'Без автора (3)')


class FakeChangeList:
    """
    Заглушка ChangeList — нужен только get_query_string().

    Метод берётся у настоящего ChangeList, чтобы тест проверял реальные ссылки,
    которые фильтр отдаёт в сайдбар. Структуру ChangeList.filter_params повторяем
    как есть: это dict(request.GET.lists()), то есть {имя параметра: [значения]}.
    """

    get_query_string = ChangeList.get_query_string

    def __init__(self, filter_params):
        self.filter_params = filter_params


class BookAdminFilterConfigTests(SimpleTestCase):
    """Состав фильтров у BaseBookAdmin и его наследников."""

    def setUp(self):
        # request нужен только для сигнатуры get_list_filter — к БД не обращаемся
        self.request = RequestFactory().get('/admin/admin_panel/eksmobook/')

    def _model_admin(self, model):
        """Возвращает экземпляр ModelAdmin, зарегистрированный для модели."""
        return django_admin.site.get_model_admin(model)

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

    def test_eksmo_book_page_has_only_period_filter(self):
        """«База книг» показывает только фильтр «Период издания»."""
        model_admin = self._model_admin(EksmoBook)
        self.assertEqual(
            tuple(model_admin.get_list_filter(self.request)),
            (PublicationPeriodFilter,),
        )

    def test_manual_book_page_has_period_and_created_by_filters(self):
        """«Каталог — админка» показывает «Период издания» и «Кем добавлена»."""
        model_admin = self._model_admin(ManualBook)
        self.assertEqual(
            tuple(model_admin.get_list_filter(self.request)),
            (PublicationPeriodFilter, CreatedByFilter),
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


class CreatedByFilterTests(SimpleTestCase):
    """Фильтр «Кем добавлена»: состав, кэш, разбор значений, ссылки сайдбара."""

    def setUp(self):
        self.request = RequestFactory().get('/admin/admin_panel/manualbook/')
        # Кэш чистим, чтобы тесты не влияли друг на друга
        cache.clear()

    def tearDown(self):
        # После теста в кэше не должно остаться данных фильтра
        cache.clear()

    def _model_admin(self):
        return django_admin.site.get_model_admin(ManualBook)

    def _seed_cache(self, choices=None, with_no_author=True):
        """Готовит кэш фильтра — тогда lookups() не пойдёт в базу."""
        lookups = list(CREATED_BY_CHOICES if choices is None else choices)
        if with_no_author:
            lookups.append(NO_AUTHOR_CHOICE)
        cache.set(CreatedByFilter.CACHE_KEY, lookups, CreatedByFilter.CACHE_TTL)
        return lookups

    def _filter(self, values=None):
        """Собирает фильтр так же, как ChangeList: значения — списком."""
        params = {}
        if values:
            params[CreatedByFilter.parameter_name] = list(values)
        return CreatedByFilter(
            self.request, params, ManualBook, self._model_admin(),
        )

    @staticmethod
    def _where(queryset):
        """WHERE-условие и параметры — компиляция SQL без запроса в базу."""
        node = queryset.query.where
        if not node.children:
            # Условий нет вовсе: Django на пустом WHERE бросает FullResultSet
            return '', []
        compiler = queryset.query.get_compiler('default')
        return compiler.compile(node)

    @staticmethod
    def _query_values(query_string):
        """Значения параметра created_by из ссылки сайдбара."""
        return parse_qs(query_string.lstrip('?')).get(
            CreatedByFilter.parameter_name, [],
        )

    def _choices(self, filter_, selected_values=None, other_params=None):
        """Ссылки фильтра через настоящий ChangeList.get_query_string()."""
        params = {CreatedByFilter.parameter_name: list(selected_values or [])}
        params.update(other_params or {})
        return list(filter_.choices(FakeChangeList(params)))

    # --- где фильтр показывается ---
    def test_filter_is_only_on_manual_book_page(self):
        """«Кем добавлена» есть только в «Каталог — админка»."""
        eksmo_filters = tuple(
            django_admin.site.get_model_admin(EksmoBook).get_list_filter(self.request)
        )
        self.assertNotIn(CreatedByFilter, eksmo_filters)
        self.assertIn(
            CreatedByFilter,
            tuple(self._model_admin().get_list_filter(self.request)),
        )

    # --- подписи в сайдбаре ---
    def test_lookups_are_taken_from_cache(self):
        """Подписи и счётчики берутся из кэша — без запросов к БД."""
        seeded = self._seed_cache()
        self.assertEqual(
            list(self._filter().lookups(self.request, self._model_admin())),
            seeded,
        )

    def test_lookups_without_no_author_item(self):
        """Если книг без автора нет, пункт «Без автора» не показывается."""
        seeded = self._seed_cache(with_no_author=False)
        self.assertEqual(
            list(self._filter().lookups(self.request, self._model_admin())),
            seeded,
        )

    # --- отбор книг ---
    def test_queryset_includes_all_selected_users(self):
        """Отмечены двое — в условии оба id, а не только последний."""
        self._seed_cache()
        queryset = self._filter(['1', '7']).queryset(
            self.request, Book.objects.all(),
        )
        where_sql, params = self._where(queryset)
        self.assertIn('created_by_id', where_sql)
        self.assertEqual(params, [1, 7])

    def test_queryset_no_author(self):
        """Пункт «Без автора» отбирает книги с created_by IS NULL."""
        self._seed_cache()
        queryset = self._filter([CreatedByFilter.NO_AUTHOR]).queryset(
            self.request, Book.objects.all(),
        )
        where_sql, params = self._where(queryset)
        self.assertIn('IS NULL', where_sql)
        self.assertEqual(params, [])

    def test_queryset_no_author_plus_users(self):
        """«Без автора» вместе с пользователями даёт условие через OR."""
        self._seed_cache()
        queryset = self._filter(['7', CreatedByFilter.NO_AUTHOR]).queryset(
            self.request, Book.objects.all(),
        )
        where_sql, params = self._where(queryset)
        self.assertIn(' OR ', where_sql)
        self.assertIn('IS NULL', where_sql)
        self.assertEqual(params, [7])

    def test_queryset_ignores_garbage_value(self):
        """Мусор в query-параметре (created_by=abc) фильтр не применяет."""
        self._seed_cache()
        queryset = self._filter(['abc']).queryset(self.request, Book.objects.all())
        where_sql, params = self._where(queryset)
        self.assertEqual(params, [])
        self.assertNotIn('created_by_id', where_sql)

    def test_queryset_without_selected_values(self):
        """Без выбранных значений условие не добавляется вообще."""
        self._seed_cache()
        queryset = self._filter().queryset(self.request, Book.objects.all())
        where_sql, _params = self._where(queryset)
        self.assertNotIn('created_by_id', where_sql)

    # --- ссылки сайдбара (мультивыбор) ---
    def test_choices_add_user_to_selection(self):
        """Клик по невыбранному пользователю добавляет его к выбранным."""
        self._seed_cache()
        choices = self._choices(self._filter(['1']), ['1'])
        # 0 — «Все», 1 — admin (5), 2 — manager (2), 3 — «Без автора»
        self.assertFalse(choices[2]['selected'])
        self.assertEqual(self._query_values(choices[2]['query_string']), ['1', '7'])

    def test_choices_remove_user_from_selection(self):
        """Повторный клик по выбранному пользователю снимает его."""
        self._seed_cache()
        choices = self._choices(self._filter(['1', '7']), ['1', '7'])
        self.assertTrue(choices[1]['selected'])
        self.assertEqual(self._query_values(choices[1]['query_string']), ['7'])

    def test_choices_reset_filter(self):
        """Снятие последнего выбранного и пункт «Все» сбрасывают фильтр."""
        self._seed_cache()
        choices = self._choices(self._filter(['7']), ['7'])
        # «Все» не активно, пока отмечен хотя бы один пользователь
        self.assertFalse(choices[0]['selected'])
        self.assertTrue(choices[2]['selected'])
        self.assertEqual(self._query_values(choices[2]['query_string']), [])
        self.assertEqual(self._query_values(choices[0]['query_string']), [])

    def test_choices_keep_other_params(self):
        """Ссылки фильтра не теряют остальные параметры страницы (поиск)."""
        self._seed_cache()
        choices = self._choices(self._filter(), [], other_params={'q': ['война']})
        query_string = choices[1]['query_string'].lstrip('?')
        self.assertEqual(parse_qs(query_string).get('q'), ['война'])
        self.assertEqual(self._query_values(choices[1]['query_string']), ['1'])

    # --- нормализация значений из query-строки ---
    def test_garbage_value_is_dropped_from_state(self):
        """Мусор (?created_by=abc) не считается выбранным и не идёт в ссылки."""
        self._seed_cache()
        filter_ = self._filter(['abc'])
        self.assertEqual(filter_.selected_values, [])
        # Значит, в сайдбаре активен пункт «Все», а в ссылке — чистый id
        choices = self._choices(filter_, [])
        self.assertTrue(choices[0]['selected'])
        self.assertEqual(self._query_values(choices[1]['query_string']), ['1'])

    def test_garbage_value_does_not_stick_to_valid_one(self):
        """?created_by=abc&created_by=1: мусор отбрасывается, валидный id остаётся."""
        self._seed_cache()
        filter_ = self._filter(['abc', '1'])
        self.assertEqual(filter_.selected_values, ['1'])
        # Клик по второму пользователю не тащит мусор в URL
        choices = self._choices(filter_, ['abc', '1'])
        self.assertEqual(self._query_values(choices[2]['query_string']), ['1', '7'])
        # «Все» сбрасывает параметр целиком, вместе с мусором
        self.assertEqual(self._query_values(choices[0]['query_string']), [])

    def test_duplicate_values_are_collapsed(self):
        """Повторы в query-строке схлопываются: created_by=1&created_by=1."""
        self._seed_cache()
        filter_ = self._filter(['1', '1', '7'])
        self.assertEqual(filter_.selected_values, ['1', '7'])
        queryset = filter_.queryset(self.request, Book.objects.all())
        self.assertEqual(self._where(queryset)[1], [1, 7])
        # Ссылка «снять пользователя 7» не тащит дубль первого значения
        choices = self._choices(filter_, ['1', '1', '7'])
        self.assertEqual(self._query_values(choices[2]['query_string']), ['1'])

    # --- подписи: чистая функция ---
    def test_build_lookups_labels(self):
        """Подписи собираются без запросов к БД и покрывают крайние случаи."""
        self.assertEqual(
            CreatedByFilter.build_lookups([(1, 'admin', 5)], 0),
            [('1', 'admin (5)')],  # без книг без автора пункта нет
        )
        self.assertEqual(
            CreatedByFilter.build_lookups([(7, None, 2)], 3),
            [
                ('7', 'Пользователь #7 (2)'),  # пустое имя заменяем на id
                (CreatedByFilter.NO_AUTHOR, 'Без автора (3)'),
            ],
        )
        self.assertEqual(CreatedByFilter.build_lookups([], 0), [])

    # --- интеграция с ChangeList ---
    def test_changelist_passes_all_values_to_filter(self):
        """Связка «ChangeList → фильтр»: из query-строки доходят оба значения."""
        self._seed_cache()
        request = RequestFactory().get(
            '/admin/admin_panel/manualbook/?created_by=1&created_by=7',
        )
        request.user = AnonymousUser()
        model_admin = self._model_admin()
        # get_queryset() отдаём пустой набор: тест не должен ходить в базу
        with patch.object(
            type(model_admin), 'get_queryset', return_value=Book.objects.none(),
        ):
            changelist = model_admin.get_changelist_instance(request)
        created_by = next(
            spec for spec in changelist.filter_specs
            if isinstance(spec, CreatedByFilter)
        )
        self.assertEqual(created_by.selected_values, ['1', '7'])
        self.assertEqual(changelist.result_count, 0)
        # Тот же фильтр даёт в SQL оба id, а не только последний
        queryset = created_by.queryset(request, Book.objects.all())
        where_sql, params = self._where(queryset)
        self.assertIn('created_by_id', where_sql)
        self.assertEqual(params, [1, 7])


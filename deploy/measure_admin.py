#!/usr/bin/env python
"""
Замер реальных страниц админки на сервере.

Показывает то же, что видел пользователь: сколько секунд открывается список,
сколько SQL на это уходит и сколько весит HTML. Запускать на сервере:

    cd /home/semen/ready
    source venv/bin/activate
    python deploy/measure_admin.py

Перед оптимизацией и после — цифры должны отличаться в разы.

Скрипт только читает данные. SQL считается через CaptureQueriesContext, поэтому
работает и при DEBUG=False (в этом режиме connection.queries пуст).
"""

import os
import sys
import time

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shop_admin.settings')
# запуск из deploy/ — добавляем корень проекта в sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from django.conf import settings                       # noqa: E402
from django.contrib import admin as django_admin       # noqa: E402
from django.contrib.auth import get_user_model         # noqa: E402
from django.db import connection                       # noqa: E402
from django.test import Client                         # noqa: E402
from django.test.utils import CaptureQueriesContext    # noqa: E402
from django.utils.http import urlencode                # noqa: E402

from admin_panel.models import EksmoBook               # noqa: E402

CHANGELIST = '/admin/admin_panel/eksmobook/'

PAGES = [
    ('Список книг (как открывает пользователь)', CHANGELIST),
    ('Список + поиск "война"', CHANGELIST + '?' + urlencode({'q': 'война'})),
    ('Список + фильтр издательства', CHANGELIST + '?' + urlencode({'pub': 'Издательство АСТ'})),
    ('Список + период 1991–2010', CHANGELIST + '?' + urlencode({'period': '1991-2010'})),
    ('Форма добавления книги', CHANGELIST + 'add/'),
]


def pick_host():
    """Host, который пройдёт проверку ALLOWED_HOSTS."""
    for host in getattr(settings, 'ALLOWED_HOSTS', []):
        if host and not host.startswith('.') and host != '*':
            return host
    return 'localhost'


def pick_user():
    User = get_user_model()
    user = (
        User.objects.filter(is_superuser=True, is_active=True).order_by('id').first()
        or User.objects.filter(is_active=True).order_by('id').first()
    )
    if user is None:
        sys.exit('В базе нет активных пользователей — не могу открыть админку.')
    return user


def warm_publisher_cache():
    """
    Прогревает кэш фильтра издательств, чтобы агрегат не попал в замер.

    Если код варианта B ещё не задеплоен, фильтра нет — тогда просто ничего
    не прогреваем, чтобы скрипт годился и для замера «до».
    """
    try:
        from admin_panel.admin import TopPublisherFilter
    except ImportError:
        return None
    model_admin = django_admin.site._registry[EksmoBook]
    return TopPublisherFilter(None, {}, EksmoBook, model_admin).lookups(None, model_admin)


def measure(client, url):
    """Возвращает (код ответа, секунды, размер HTML в байтах, список запросов)."""
    with CaptureQueriesContext(connection) as captured:
        started = time.time()
        response = client.get(url)
        elapsed = time.time() - started
    return response.status_code, elapsed, len(response.content), list(captured.captured_queries)


def main():
    print(f'DEBUG   = {settings.DEBUG}')
    print(f'Host    = {pick_host()}')
    print(f'БД      = {settings.DATABASES["default"]["NAME"]}')

    with connection.cursor() as cur:
        cur.execute(
            "SELECT relname, n_live_tup, pg_size_pretty(pg_total_relation_size(relid)) "
            "FROM pg_stat_user_tables WHERE relname = 'admin_panel_book';"
        )
        row = cur.fetchone()
        if row:
            print(f'Таблица = {row[0]}: ~{row[1]:,} строк, {row[2]}')

    started = time.time()
    choices = warm_publisher_cache()
    if choices is None:
        print('Кэш издательств: фильтр TopPublisherFilter не найден — код варианта B не задеплоен')
    else:
        print(f'Кэш издательств: {len(choices)} значений, агрегат занял {time.time() - started:.2f} с')
    print()

    client = Client(SERVER_NAME=pick_host())
    client.force_login(pick_user())

    results = []
    for label, url in PAGES:
        code, elapsed, size, queries = measure(client, url)
        sql_time = sum(float(q['time']) for q in queries)
        results.append((label, url, code, elapsed, sql_time, len(queries), size))

    width = max(len(r[0]) for r in results)
    header = f'{"Страница":<{width}} | {"код":>4} | {"время":>8} | {"SQL":>8} | {"запр.":>6} | {"HTML":>10}'
    print(header)
    print('-' * len(header))
    for label, _url, code, elapsed, sql_time, n_queries, size in results:
        print(
            f'{label:<{width}} | {code:>4} | {elapsed:>7.2f}s | {sql_time:>7.2f}s | '
            f'{n_queries:>6} | {size / 1024:>7.0f} КБ'
        )

    not_ok = [r for r in results if r[2] != 200]
    if not_ok:
        print('\nВнимание, не все страницы открылись:')
        for label, _url, code, *_rest in not_ok:
            print(f'  {label}: HTTP {code}')
        print('  302 с Location "?e=1" означает, что параметр фильтра не распознан,')
        print('  то есть код варианта B (PublicationPeriodFilter/TopPublisherFilter)')
        print('  ещё не задеплоен. Строку с фильтром тогда можно игнорировать.')

    # Разбивка по запросам для самой долгой страницы
    worst = max(results, key=lambda r: r[3])
    print(f'\nСамая долгая страница: {worst[0]} ({worst[3]:.2f}s)')
    _code, _elapsed, _size, queries = measure(client, worst[1])
    print('Самые дорогие запросы на ней:')
    for query in sorted(queries, key=lambda q: -float(q['time']))[:5]:
        print(f'  {float(query["time"]):7.2f}s  {query["sql"][:100]}')

    print('\nОриентиры после вариантов A+B (замерено 18.09.2026 на этом проде):')
    print('  список без фильтров      ~4 с   (было 15.8 с), HTML ~250 КБ (было 15.5 МБ)')
    print('  фильтр периода           ~4 с   (периоды строят выборку быстро, время уходит в COUNT(*))')
    print('  фильтр издательства      <1 с   после составного индекса (было 74-101 с)')
    print('  оставшиеся ~4 с — это SELECT COUNT(*) пагинатора, лечится вариантом C')


if __name__ == '__main__':
    main()

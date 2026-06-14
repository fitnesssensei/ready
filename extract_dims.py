"""
Извлекает размеры (format, thickness) из exmo_books.json
в отдельный компактный JSON-файл.

ВАЖНО: В исходном JSON один ISBN может встречаться много раз
с разными частями данных. Скрипт объединяет данные:
- Если в одной записи format, а в другой thickness — берёт оба.
- Если в разных записях разный format — берёт последний (более полный).

Выходной формат:
    {
        "9785041125417": {"w": 115, "l": 180, "h": 18},
        ...
    }

Использование:
    python extract_dims.py
    python extract_dims.py --input vBaze/exmo_books.json --output vBaze/dims_only.json
"""

import json
import re
import sys
from pathlib import Path


def isbn_digits(raw: str) -> str:
    """ISBN → только цифры"""
    return ''.join(c for c in (raw or '') if c.isdigit())


def parse_format_dims(raw: str):
    """«125x200 мм» → (width, length) в мм"""
    match = re.search(r'(\d+)\s*[xх×]\s*(\d+)', raw or '', re.IGNORECASE)
    if not match:
        return None, None
    return int(match.group(1)), int(match.group(2))


def parse_thickness_mm(raw: str):
    """«18 мм» → height в мм"""
    match = re.search(r'(\d+)', raw or '')
    if not match:
        return None
    value = int(match.group(1))
    if value <= 0:
        return None
    return value


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Извлечение размеров из JSON каталога')
    parser.add_argument('--input', default='vBaze/exmo_books.json', help='Входной JSON файл')
    parser.add_argument('--output', default='vBaze/dims_only.json', help='Выходной JSON файл')
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f'Ошибка: файл {input_path} не найден')
        sys.exit(1)

    print(f'Читаю {input_path}...')
    with input_path.open(encoding='utf-8') as f:
        rows = json.load(f)

    print(f'Загружено {len(rows)} записей')

    # Собираем размеры для каждого ISBN, объединяя данные из разных записей
    merged: dict[str, dict] = {}
    skipped_no_isbn = 0
    skipped_no_dims_total = 0

    for row in rows:
        isbn_key = isbn_digits(row.get('isbn', ''))
        if not isbn_key or len(isbn_key) not in (10, 13):
            skipped_no_isbn += 1
            continue

        width, length = parse_format_dims(row.get('format', ''))
        height = parse_thickness_mm(row.get('thickness', ''))

        if width is None and length is None and height is None:
            skipped_no_dims_total += 1
            continue

        # Объединяем: если уже есть запись, дополняем недостающие поля
        if isbn_key not in merged:
            merged[isbn_key] = {}

        entry = merged[isbn_key]
        if width is not None:
            entry['w'] = width
        if length is not None:
            entry['l'] = length
        if height is not None:
            entry['h'] = height

    # Считаем статистику
    total_with_dims = len(merged)
    with_w = sum(1 for v in merged.values() if 'w' in v)
    with_l = sum(1 for v in merged.values() if 'l' in v)
    with_h = sum(1 for v in merged.values() if 'h' in v)
    full_3d = sum(1 for v in merged.values() if 'w' in v and 'l' in v and 'h' in v)
    only_wl = sum(1 for v in merged.values() if 'w' in v and 'l' in v and 'h' not in v)
    only_h = sum(1 for v in merged.values() if 'h' in v and 'w' not in v and 'l' not in v)

    output_path = Path(args.output)
    with output_path.open('w', encoding='utf-8') as f:
        json.dump(merged, f, ensure_ascii=False, indent=None, separators=(',', ':'))

    output_size = output_path.stat().st_size

    print(f'\nРезультат:')
    print(f'  Всего записей в исходном JSON:    {len(rows)}')
    print(f'  Без ISBN:                         {skipped_no_isbn}')
    print(f'  Без размеров (format/thickness):   {skipped_no_dims_total}')
    print(f'  Уникальных ISBN с размерами:       {total_with_dims}')
    print(f'  Из них:')
    print(f'    — есть ширина (w):              {with_w}')
    print(f'    — есть длина (l):               {with_l}')
    print(f'    — есть высота (h):              {with_h}')
    print(f'    — полные 3 размера (w+l+h):     {full_3d}')
    print(f'    — только w+l (без h):           {only_wl}')
    print(f'    — только h (без w/l):           {only_h}')
    print(f'  Выходной файл:                     {output_path}')
    print(f'  Размер файла:                      {output_size:,} байт ({output_size/1024/1024:.2f} МБ)')


if __name__ == '__main__':
    main()

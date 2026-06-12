"""
Объединяет все JSON-файлы из заданной папки в один JSON-файл.

Если JSON-файлы содержат списки, итоговый файл будет содержать один общий список.
Если файл содержит объект или другое значение, оно добавляется как отдельный элемент
в итоговый список.

Примеры использования:
    python merge_json.py --input JSON --output merged_books.json
    python merge_json.py -i JSON -o merged_books.json
    python merge_json.py -i JSON -o merged_books.json --no-recursive
"""

import argparse
import json
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(
        description="Объединить все JSON-файлы из папки в один файл."
    )
    parser.add_argument(
        "-i",
        "--input",
        required=True,
        type=Path,
        help="Папка, в которой нужно искать JSON-файлы.",
    )
    parser.add_argument(
        "-o",
        "--output",
        required=True,
        type=Path,
        help="Путь к итоговому JSON-файлу.",
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Искать JSON-файлы только в указанной папке, без вложенных папок.",
    )
    return parser.parse_args()


def collect_json_files(input_dir: Path, recursive: bool = True):
    """Найти все JSON-файлы в папке."""
    pattern = "**/*.json" if recursive else "*.json"
    return sorted(input_dir.glob(pattern))


def merge_json_files(input_dir: Path, output_file: Path, recursive: bool = True):
    """Объединить JSON-файлы в один общий список."""
    if not input_dir.exists():
        raise FileNotFoundError(f"Папка не найдена: {input_dir}")

    if not input_dir.is_dir():
        raise NotADirectoryError(f"Указанный путь не является папкой: {input_dir}")

    output_file = output_file.resolve()
    input_dir = input_dir.resolve()

    json_files = [
        file_path
        for file_path in collect_json_files(input_dir, recursive=recursive)
        if file_path.resolve() != output_file
    ]

    if not json_files:
        raise FileNotFoundError(f"В папке не найдено JSON-файлов: {input_dir}")

    merged_data = []

    for file_path in json_files:
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, list):
            merged_data.extend(data)
        else:
            merged_data.append(data)

    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(merged_data, file, ensure_ascii=False, indent=2)

    return len(json_files), len(merged_data)


def main():
    args = parse_args()

    files_count, items_count = merge_json_files(
        input_dir=args.input,
        output_file=args.output,
        recursive=not args.no_recursive,
    )

    print(f"Объединено файлов: {files_count}")
    print(f"Всего записей: {items_count}")
    print(f"Результат сохранен: {args.output}")


if __name__ == "__main__":
    main()

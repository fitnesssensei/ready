
# Ready — Django-админка для книжного магазина

# Обязательно смотри /Users/rustamismagilov/Desktop/ready/.clinerules

## 1. Назначение проекта

Проект `ready` — это Django-приложение для администрирования каталога книг интернет-магазина и подготовки данных для Ozon Seller.
Основная область применения — управление букинистическими и обычными книгами: импорт каталогов из JSON, ручное редактирование товаров, загрузка фото, экспорт выбранных книг в Excel и в Excel-шаблон Ozon
Проект не является публичным storefront-сайтом: главная страница перенаправляет в Django Admin, а пользовательский интерфейс `/shop/` содержит только демонстрационные страницы.

---

## 2. Технологический стек

- **Backend:** Python, Django 5.1.4
- **База данных:** PostgreSQL
- **Админка:** Django Admin с кастомными шаблонами и действиями
- **Excel:** `openpyxl`
- **Конфигурация:** `python-decouple`
- **YAML:** `PyYAML` используется в закомментированном YML-экспорте
- **Статика:** встроенные файлы Django Admin в `staticfiles/admin/`
- **Медиафайлы:** `media/`, включая Ozon-шаблоны и загружаемые фото книг
Основные зависимости указаны в `requirements.txt`:

```txt
Django==5.1.4
psycopg2-binary==2.9.10
PyYAML==6.0.2
python-decouple==3.8
openpyxl==3.1.2
```

---

## 3. Структура проекта

```txt
ready/
├── manage.py                         # Django CLI
├── requirements.txt                  # зависимости
├── .env.example                      # пример переменных окружения
├── доки.md                           # старые заметки по деплою/импорту
├── shop_admin/                       # основной Django-проект
│   ├── settings.py                   # настройки Django
│   ├── urls.py                       # маршруты проекта
│   ├── wsgi.py
│   └── asgi.py
├── admin_panel/                      # основное приложение
│   ├── models.py                     # модели каталога
│   ├── admin.py                      # кастомная Django Admin
│   ├── views.py                      # экспорт Excel/Ozon
│   ├── urls.py                       # маршруты /shop/
│   ├── widgets.py                    # виджет загрузки нескольких фото
│   ├── ozon_api.py                   # закомментированный Ozon API-клиент
│   ├── management/commands/          # Django-команды импорта/обработки
│   └── templates/admin_panel/        # шаблоны админки и демо-страниц
├── import_books.py                   # legacy-скрипт импорта книг (source='eksmo')
├── import_ast.py                     # импорт книг издательства АСТ (source='ast')
├── import_eksmo_books.py             # импорт книг Эксмо (source='eksmo')
├── merge_json.py                     # объединение JSON-файлов
├── extract_dims.py                   # извлечение размеров из JSON
├── deploy/                           # скрипты оптимизации и замеров прода (см. раздел 19)
│   ├── optimize_A.sh                 # тюнинг сервера: DEBUG=False, PostgreSQL, gunicorn, индекс
│   └── measure_admin.py              # замеры страниц админки «до/после»
├── vBaze/                            # большие JSON-каталоги
└── media/                            # media-файлы и шаблоны Ozon
```

---

## 4. Конфигурация и запуск

### Переменные окружения

Проект читает настройки через `decouple.config`.
Пример `.env` можно создать по образцу `.env.example`:

```env
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DB_NAME=shop_admin_db
DB_USER=postgres
DB_PASSWORD=your_password_here
DB_HOST=localhost
DB_PORT=5432
# Ozon API сейчас отключён
# OZON_SHOP_ID=your_ozon_shop_id_here
```

## Важные настройки из `shop_admin/settings.py`

- PostgreSQL используется по умолчанию.
- `LANGUAGE_CODE = 'ru-ru'`
- `TIME_ZONE = 'Europe/Moscow'`
- `MEDIA_ROOT = BASE_DIR / 'media'`
- `STATIC_ROOT = BASE_DIR / 'staticfiles'`
- `ALLOWED_HOSTS` по умолчанию разрешает `*`
- Ozon Seller API отключён: `admin_panel/ozon_api.py` и часть management-команд закомментированы.

### Установка зависимостей

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Миграции

```bash
python manage.py migrate
```

### Запуск локального сервера

```bash
python manage.py runserver
```

Главная страница `/` перенаправляет в `/admin/`.

---

## 5. Модели данных

Все основные сущности находятся в `admin_panel/models.py`.

### Category

Категории товаров с Ozon category ID.
Поля:

- `name` — название категории
- `ozon_category_id` — уникальный ID категории Ozon
- `description` — описание
- `created_at` — дата создания

### Book

Основная модель книги/товара. Используется как для ручных книг магазина, так и для импортированных книг Эксмо.
Ключевые поля:

- `source` — источник: `manual` или `eksmo`
- `sku` — артикул, уникальный
- `title` — название
- `author` — автор (поддерживает несколько значений через разделитель `;`)
- `author_oblozh` — автор на обложке
- `genre` — направление
- `publisher` — издательство (поддерживает несколько значений через разделитель `;`)
- `series` — серия
- `publication_year` — год издания
- `language` — язык издания: `russian`, `english`, `french`, `german`
- `condition` — сохранность: `excellent`, `good`, `veriGood`, `satisfactorily`, `bad`
- `cover_type` — тип переплёта: `hard`, `soft`, `softSuper`, `klapan`, `klapanSuper`, `poluKozha`, `hardSuper`, `textile`, `textileSuper`, `block`, `Bumvinyl`, `integral`, `integralSuper`, `leather`, `sheet`, `copper`
- `paper_type` — тип бумаги: `offset`, `art`, `newsprint`, `recycled`, `kremovaya`, `design`, `karton`, `coated`
- `target_audience` — целевая аудитория: `for adults`, `for children`
- `age_restrictions` — возрастные ограничения: `18+`, `16+`, `14+`, `12+`, `10+`, `9+`
- `book_type` — тип книги: `printed book`, `second`, `bookinist`
- `hashtags` — хештеги
- `pages` — количество страниц
- `photos` — JSONField со списком путей к фото
- `description` — описание/аннотация
- `price` — цена
- `old_price` — старая цена
- `vat_rate` — НДС: `0`, `10`, `20`
- `stock` — остаток
- `isbn` — ISBN
- `weight` — вес с упаковкой в граммах
- `length`, `width`, `height` — размеры с упаковкой в мм
- `publication_date`, `created_at`, `updated_at`
- `created_by` — кто создал книгу (ForeignKey на User, заполняется автоматически)

### Константы модели Book (`admin_panel/constants.py`)

Списки `choices` и строковые дефолты модели `Book` вынесены из `admin_panel/models.py` в отдельный модуль `admin_panel/constants.py`, чтобы модель не содержала данных.

Что вынесено:

- списки`choices`:`SOURCE_CHOICES`,`COVER_TYPES`,`VAT_RATES`,`GENRE`,`TARGET_AUDIENCE`,`AGE_RESTRICTIONS`,`IS_ADULT`,`LANGUAGE_CHOICES`,`CONDITION_CHOICES`,`BOOK_TYPE`,`PAPER_TYPES`;
- строковые источники: `SOURCE_MANUAL`, `SOURCE_EKSMO`, `SOURCE_AST`;
- строковые дефолты полей: `DEFAULT_SOURCE`, `DEFAULT_GENRE`, `DEFAULT_COVER_TYPE`, `DEFAULT_BOOK_TYPE`, `DEFAULT_PAPER_TYPE`, `DEFAULT_LANGUAGE`, `DEFAULT_CONDITION`, `DEFAULT_IS_ADULT`, `DEFAULT_AGE_RESTRICTION`, `DEFAULT_VAT_RATE`, `DEFAULT_TNVED_CODE`.

В классе `Book` значения ссылаются на константы модуля. Для обратной совместимости `Book.SOURCE_MANUAL / SOURCE_EKSMO / SOURCE_AST` сохранены как атрибуты-ссылки — код (`admin.py`, `import_*.py`, management-команды), использующий `Book.SOURCE_*`, работает без изменений. Миграции не потребовались (наборы значений не менялись).

### ⚠️ Замечание по `admin.py` (`OzonTemplateAdmin`)

При добавлении админки VK (`VkIntegrationAdmin`) в `admin_panel/admin.py` у `OzonTemplateAdmin` были удалены `readonly_fields = ('uploaded_at',)` и блок `fieldsets` (поля `name, file, description, is_active, year_from, year_to`). Код намеренно **не восстанавливали** — это требует проверки/доработки при следующем изменении VK- или Ozon-интеграции.

### Proxy-модели

- `ManualBook(Book)` — ручные книги магазина.
- `EksmoBook(Book)` — каталог Эксмо.

## Proxy-модели позволяют разделять книги в админке по источнику, не создавая отдельные таблицы

**Кастомные permissions для ManualBook:**

Для модели `ManualBook` созданы отдельные permissions (не путать со стандартными permissions от `Book`):

| Codename | Название в админке | Назначение |
|---------- --------- -------- ------- -------
| `add_book_manual` | Может добавлять книги в Каталог — админка | Добавление |
| `delete_book_manual` | Может удалять книги из Каталог — админка | Удаление |
| `change_book_manual` | Может редактировать книги в Каталог — админка | Редактирование |
| `view_book_manual` | Может просматривать книги в Каталог — админка | Просмотр |

Это позволяет дать пользователю права **только** на «Каталог — админка», не давая доступа к «База книг». Детальнее см. раздел «Управление правами пользователей».

### OzonTemplate

Модель для загрузки Excel-шаблонов Ozon Seller.
Особенности:

- хранит файл в `media/ozon_templates/`
- может быть активным только один шаблон
- при активации нового шаблона старые автоматически деактивируются

---

## 6. Django Admin

Админка — центральная часть проекта.

### Разделы

- `Category` — категории
- `OzonTemplate` — шаблоны Ozon
- `Каталог — админка` — ручные книги
- `База книг` — книги Эксмо
- `Book` — скрытый общий список, перенаправляет в proxy-разделы

### Возможности админки

- просмотр, поиск, фильтрация книг
- экспорт выбранных книг в Excel
- экспорт выбранных книг в шаблон Ozon
- загрузка до 10 фото к книге
- ручное создание книги из каталога Эксмо
- поиск книг по артикулу, названию или ISBN (по всем каталогам)
- автоматическая подстановка данных книги Эксмо в форму ручной книги
- автоматическое определение категории по году издания (≤2010 → «Букинистическое издание», ≥2011 → «Современные печатные издания»)

### Поиск при добавлении книги

При создании ручной книги в форме появляется блок «Поиск по всем каталогам (админка + Эксмо)».
Логика:

1. Пользователь вводит артикул, название или ISBN.
2. AJAX-запрос обращается в `search-eksmo/`.
3. Поиск идёт по всем каталогам (админка + Эксмо).
4. Для ISBN-запросов нормализуются цифры и дефисы.
5. Найденная книга подставляется в форму. При сохранении создаётся новая запись с `source='manual'`.
6. Книга отображается и в «Каталог — админка», и в «База книг».

### Поиск в выпадающих списках (Select2)

При создании или редактировании книги поля с длинными списками выбора (`жанр`, `тип переплёта`, `тип бумаги`, `целевая аудитория`, `возрастные ограничения`, `язык`, `сохранность`) преобразованы в **Select2** — выпадающий список с поиском по вводу.

Логика:

1. Select2 инициализируется через JavaScript в `admin_panel/templates/admin_panel/change_form.html`
2. Библиотека Select2 уже встроена в Django (`staticfiles/admin/js/vendor/select2/`), дополнительная установка не требуется
3. Поиск появляется при фокусе на поле — можно начать вводить текст, и список отфильтруется

**Как добавить новое поле в список:**

В файле `admin_panel/templates/admin_panel/change_form.html` найти массив `searchableFields` и добавить имя поля (name атрибут из модели):

```javascript
var searchableFields = [
    'genre', 'cover_type', 'paper_type',
    'target_audience', 'age_restrictions',
    'language', 'condition'
];
```

**Для ForeignKey-полей (например, `category`)** используется встроенный механизм Django `autocomplete_fields` в `admin.py` — он также использует Select2, но с серверным AJAX-поиском.

---

### Автоопределение категории по году издания

При сохранении книги в админке (`BaseBookAdmin.save_model`) автоматически определяется категория на основе года издания:

| Год издания | Категория |
|------
| Не указан | Категория не меняется |
| ≤ 2010 | «Букинистическое издание» |
| ≥ 2011 | «Современные печатные издания» |

Категории создаются автоматически через `get_or_create` при первом сохранении.
Работает для обоих разделов: «Каталог — админка» и «База книг».

---

## 7. Управление правами пользователей

### Разделение прав на «Каталог — админка» и «База книг»

По умолчанию `ManualBook` — proxy-модель от `Book`, поэтому стандартные permissions (`Can add book`, `Can delete book` и т.д.) дают доступ сразу ко всем книгам. Чтобы разделить права, для `ManualBook` созданы **кастомные permissions** (см. раздел «Proxy-модели»).

**Как создать пользователя с правом только на добавление и удаление книг в «Каталог — админка»:**

1. Создать группу (например, «Менеджер каталога») через **Authentication and Authorization → Groups**
2. В группу добавить только 2 permission:
   - `admin_panel | ManualBook | add_book_manual | Может добавлять книги в Каталог — админка`
   - `admin_panel | ManualBook | delete_book_manual | Может удалять книги из Каталог — админка`
3. Создать пользователя через **Authentication and Authorization → Users**
4. Назначить пользователю эту группу

> ⚠️ **Важно:** Не добавляйте стандартные permissions (`Can add manual book`, `Can delete manual book` и т.д.) — они дают доступ к родительской модели `Book`, то есть и к «База книг» тоже.

### Статистика пользователя на странице редактирования

На странице `/admin/auth/user/<id>/change/` добавлена секция **«Статистика»** с полем **«Добавлено книг (каталог)»**.

Счётчик показывает количество книг с `source='manual'`, добавленных этим пользователем (поле `Book.created_by`).

Техническая реализация:

- `Book.created_by` — ForeignKey на `auth.User`, заполняется автоматически при создании книги через админку
- `CustomUserAdmin` — кастомная админка для `User`, переопределяет `get_fieldsets` и добавляет read-only поле
- Регистрация: стандартный `UserAdmin` отключается через `admin.site.unregister(User)`, затем регистрируется `CustomUserAdmin`

---

## 8. Экспорт

### Экспорт в обычный Excel

Файл: `admin_panel/views.py`, функция `export_books_to_excel`.
Создаёт файл `books_export.xlsx` со столбцами:

- ID
- Артикул
- Название
- Автор
- Автор на обложке
- Жанр
- Издательство
- Серия
- Год издания
- Язык
- Сохранность
- Тип переплёта
- Страницы
- ISBN
- Цена
- Старая цена
- НДС
- Остаток
- Вес, размеры
- Категория
- Источник
- Дата создания

### Экспорт в шаблон Ozon

Файл: `admin_panel/views.py`, функция `export_books_to_ozon_template`.

Логика:

1. Берётся активный `OzonTemplate`.
2. Открывается лист `Шаблон`.
3. Заголовки читаются из строки 2.
4. Данные книг записываются начиная со строки 5.
5. Поля маппятся по русским названиям колонок Ozon (все 78 колонок).

**Маппинг полей:**

| Колонка Ozon | Поле модели Book / источник |
|------
| № | Автонумерация |
| Артикул*| `sku` |
| Название товара | `title` |
| Цена, руб.* | `price` |
| Цена до скидки, руб. | `old_price` |
| НДС, %*| `vat_rate` |
| SKU | `sku` |
| Штрихкод (Серийный номер / EAN) | `isbn` |
| Вес в упаковке, г* | `weight` |
| Ширина упаковки, мм*| `width / 10` |
| Высота упаковки, мм* | `height / 10` |
| Длина упаковки, мм*| `length / 10` |
| Ссылка на главное фото* | `photos[0]` → полный URL |
| Ссылки на дополнительные фото | `photos[1:]` → полные URL через запятую |
| Артикул фото | `sku` |
| Автор на обложке*| `author_oblozh` (если пусто → `author`) |
| Автор | `author` |
| Тип обложки | `get_cover_type_display()` |
| Тип книги | Из `book_type`: Печатная книга / Б/У / Букинистическое издание |
| Тип* | Из `book_type`: Печатная книга / Second-hand / Букинистическое издание |
| Бренд*| `publisher` (или 'Нет бренда') |
| ТН ВЭД коды ЕАЭС* | `4901990000` (фиксированный код для книг) |
| Направление* | `get_genre_display()` |
| Целевая аудитория литературы | `get_target_audience_display()` |
| #Хештеги | `hashtags` |
| Аннотация | `description` |
| Издательство | `publisher` |
| Серия | `series` |
| Год выпуска | `publication_year` |
| Тип бумаги в книге | `get_paper_type_display()` |
| Язык издания | `get_language_display()` |
| Количество страниц | `pages` |
| Размер упаковки (Длина х Ширина х Высота), см | `length/10 x width/10 x height/10` |
| Размеры, мм | `length x width x height` |
| Вес товара, г | `weight` |
| ISBN | `isbn` |
| Сохранность книги | `get_condition_display()` |
| Возрастные ограничения | `get_age_restrictions_display()` |
| Признак 18+ | `да` если age_restrictions == '18+' |

**Константы в `views.py`:**

- `BOOK_TYPE_OZON_MAPPING` — маппинг `book_type` → колонка "Тип*"
- `BOOK_TYPE_DISPLAY_MAPPING` — маппинг `book_type` → колонка "Тип книги"

Фотографии преобразуются из относительных путей в полные URL через `MEDIA_BASE_URL`.

---

## 9. Ozon-интеграция

В проекте есть два уровня Ozon-интеграции:

### Работает сейчас

- загрузка Excel-шаблонов Ozon через `OzonTemplate`
- экспорт выбранных книг в Excel-шаблон Ozon
- маппинг полей книги на колонки шаблона
- генерация ссылок на фото

### Закомментировано / отключено

- прямой Ozon Seller API-клиент в `admin_panel/ozon_api.py`
- команды:
  - `export_to_ozon`
  - `check_ozon_import`
  - `get_ozon_category_info`
  - `get_ozon_types`
  - `prepare_eksmo_for_ozon`
Причины отключения:
- API-клиент ожидает `OZON_CLIENT_ID` и `OZON_API_KEY`, но в настройках они не подключены.
- В `.env.example` Ozon-интеграция явно помечена как отключённая.

- Файлы и команды оставлены как заготовки.

---

## 10. Импорт и обработка данных

### `import_books.py`

Legacy-скрипт для импорта книг из `JSON/13000_libex.json`.
Парсит:

- название
- автора
- ISBN
- описание/annotation
- издательство
- категорию
- год
- страницы
- переплёт
- серию
- язык
- размеры из `format` / `thickness`
- размеры из текста аннотации
- вес из текста аннотации

Импортирует книги с `source='eksmo'` батчами по 500 записей.

### `import_eksmo_books.py`

Самостоятельный скрипт импорта книг Эксмо (source='eksmo') из JSON.
Запуск:

```bash

python import_eksmo_books.py
python import_eksmo_books.py --update
python import_eksmo_books.py --dry-run
python import_eksmo_books.py --file /path/to/file.json

```

По умолчанию ожидает файл:

```txt
parsing/eksmo_books_mt_deduped.json
```

Особенности:

- парсит ISBN с дефисами и без
- парсит размеры из `format` и `thickness`
- обновляет существующие книги по цифрам ISBN при `--update`
- использует `bulk_create` / `bulk_update`
- batch size: 500

### `fill_isbn_digits.py`

Django-команда для заполнения поля `isbn_digits` у книг, у которых есть ISBN, но `isbn_digits` пустой.

Поле `isbn_digits` хранит ISBN только цифрами (без дефисов/пробелов). Используется для быстрого поиска по ISBN и сопоставления книг при импорте/обновлении.

Запуск:

```bash
python manage.py fill_isbn_digits
python manage.py fill_isbn_digits --dry-run
```

### `extract_dims.py`

Извлекает размеры из `vBaze/exmo_books.json` в компактный JSON.
Выходной формат:

```json

{
  "9785041125417": {"w": 115, "l": 180, "h": 18}
}
```

Запуск:

```bash

python extract_dims.py --input vBaze/exmo_books.json --output vBaze/dims_only.json
```

### `apply_dims_from_json.py`

Заполняет размеры книг из компактного JSON-файла.
Запуск:

```bash
python manage.py apply_dims_from_json
python manage.py apply_dims_from_json --dry-run
python manage.py apply_dims_from_json --force
```

Обновляет только пустые поля `width`, `length`, `height`, если не указан `--force`.

### `update_eksmo_dimensions.py`

Обновляет размеры книг Эксмо из `vBaze/exmo_books.json`.
Запуск:

```bash
python manage.py update_eksmo_dimensions
python manage.py update_eksmo_dimensions --dry-run
python manage.py update_eksmo_dimensions --force
```

### `convert_dims_to_mm.py`

Конвертирует старые размеры из сантиметров в миллиметры.
Запуск:

```bash
python manage.py convert_dims_to_mm
python manage.py convert_dims_to_mm --dry-run
```

### `fill_dims_from_annotation.py`

Пытается извлечь размеры из текста аннотации.
Поддерживаемые паттерны:

- `Размеры: 267x214x21 мм`
- `Размер: 297x226x12 мм`
- `Размеры: 125x200 мм`
Запуск:

```bash
python manage.py fill_dims_from_annotation
python manage.py fill_dims_from_annotation --source eksmo
python manage.py fill_dims_from_annotation --source manual
python manage.py fill_dims_from_annotation --all
python manage.py fill_dims_from_annotation --dry-run
```

### `merge_json.py`

Объединяет JSON-файлы из папки в один JSON-массив.
Запуск:

```bash
python merge_json.py --input JSON --output merged_books.json
python merge_json.py -i JSON -o merged_books.json
python merge_json.py -i JSON -o merged_books.json --no-recursive
```

---

## 11. Данные и большие файлы

В проекте есть большие JSON-файлы и Excel-файлы:

- `vBaze/exmo_books.json`
- `vBaze/12825_libex.json`
- `Букинистические издания (1942-2010 гг.)_25.05.2026.xlsx`
- `media/ozon_templates/*.xlsx`

Часть больших файлов игнорируется Git через `.gitignore`:

```gitignore
vBaze/12825_libex.json
vBaze/exmo_books.json
*.xlsx
*.xls
media/book_photos/
media/ozon_templates/
```

В старой заметке `доки.md` указано, что в базе данных на сервере было около `37111` книг с размерами, а также упоминалось `12825` книг. Эти цифры относятся к состоянию БД/данных на момент заметки и могут отличаться от текущего состояния.

---

## 12. Маршруты

Основные URL находятся в `shop_admin/urls.py`.

```txt
/                 → перенаправление в /admin/
/admin/           → Django Admin
/shop/            → демо-страницы admin_panel
/shop/products/   → демо-страница товаров
/shop/orders/     → демо-страница заказов
/shop/customers/  → демо-страница клиентов
```

Custom admin routes для ручных книг:

```txt
/admin/admin_panel/manualbook/search-eksmo/
/admin/admin_panel/manualbook/eksmo-template/<book_id>/
```

---

## 13. Шаблоны и frontend

В проекте есть простые шаблоны:

- `base.html` — общий layout с боковым меню
- `dashboard.html` — демо-панель
- `products.html` — демо-страница товаров
- `orders.html` — демо-страница заказов
- `customers.html` — демо-страница клиентов
- `manualbook_change_form.html` — форма с поиском по каталогу Эксмо
- `multiple_image_widget.html` — виджет загрузки нескольких фото
- `change_form.html` — кастомизация формы админки
- `change_list.html` — кастомизация списка админки

### Кастомные виджеты

В `admin_panel/widgets.py` определены:

- **`MultipleImageWidget`** — виджет для загрузки нескольких фотографий к книге. Хранит список путей в JSONField.
- **`TagInputWidget`** — теговый input для множественных значений. Используется для полей `author` и `publisher`.  
  Позволяет вводить несколько значений через Enter, отображает их в виде тегов-плипок с возможностью удаления.  
  Значения хранятся в `CharField` через разделитель `"; "` (точка с запятой + пробел).  
  Поддерживает автодополнение из существующих значений (через `search_field_view`), клавиатурную навигацию и мобильные устройства.  
  CSS: `admin_panel/static/admin_panel/css/tag_input.css`  
  JS: `admin_panel/static/admin_panel/js/tag_input.js`
Демо-страницы `/shop/` не подключены к реальным моделям и показывают статический текст.

---

## 14. Миграции

Миграции находятся в `admin_panel/migrations/`.
История миграций отражает развитие модели книги:

- начальные модели
- разделение авторов/жанров/категорий
- добавление publication year, publisher, cover type, language, pages
- добавление цены, старой цены, остатка, НДС
- добавление размеров, веса, ISBN
- добавление `source`
- добавление `OzonTemplate`
- конвертация размеров в мм
- конвертация веса в граммы
- исправления constraints и verbose names
- добавление paper_type (тип бумаги), target_audience (целевая аудитория), age_restrictions (возрастные ограничения), hashtags
- добавление book_type (тип книги: печатная, second-hand, букинистика)
- расширение cover_type (добавлены: softSuper, klapan, klapanSuper, poluKozha, hardSuper, textile, textileSuper, block, Bumvinyl, integral, integralSuper, leather, sheet, copper)
- расширение condition (добавлены: veriGood, satisfactorily, bad)
- добавление choices для language (russian, english, french, german)
- добавление choices для target_audience и age_restrictions
Текущая актуальная схема описана в `admin_panel/models.py`; именно её следует считать источником правды.

---

## 15. Деплой

В `доки.md` есть пример деплоя на VDS-сервер.

### Локально

```bash
git add .
git commit -m "описание изменений"
git push origin main
```

### На сервере

```bash
ssh semen@v3144166.hosted-by-vdsina.ru
cd /home/semen/ready
git pull origin main
source venv/bin/activate
python manage.py migrate --noinput
python manage.py collectstatic --noinput
sudo systemctl restart gunicorn
```

### Проверка количества книг с размерами на сервере

```bash
sudo -u postgres psql -d shop_admin_db -c "SELECT COUNT(*) FROM admin_panel_book WHERE height IS NOT NULL AND length IS NOT NULL AND width IS NOT NULL;"
```

---

## 16. Известные особенности и ограничения

1. **Ozon API отключён.**  
   Работает только экспорт в Excel-шаблон Ozon. Прямая загрузка через API закомментирована.
2. **Демо-страницы `/shop/` не являются магазином.**  
   Они не выводят товары, заказы и клиентов из БД.
3. **`dashboard.html` содержит устаревшую строку про Django 6.0.3.**  
   В `requirements.txt` и проекте используется Django 5.1.4.
4. **`import_books.py` — legacy-скрипт (source='eksmo').**  
   Более актуальный скрипт — `python import_eksmo_books.py`.
5. **`import_ast.py` — импорт книг издательства АСТ (source='ast').**  
    Скрипт для импорта книг из JSON-файла издательства АСТ (\`JSON/dnevnikiAST.json\`). Поддерживает:
    - Парсинг размеров из поля format ("145, 207" → width/length)
    - Конвертацию веса из кг в граммы
    - Маппинг возрастных ограничений (0+, 6+ → 9+ и т.д.)
    - Автоматическое создание категорий по строковому названию
    - Пропуск дубликатов по ISBN + source
    - Режим --stdin для передачи JSON через пайп (без копирования на сервер)
    Использование: \`python import_ast.py\` или \`cat books.json | python import_ast.py --stdin\`.

6. **Размеры хранятся в мм.**  
   Для старых данных есть команда `convert_dims_to_mm`.
7. **Фото книг хранятся как JSONField со списком относительных путей.**  
   Загрузка файлов выполняется в `BaseBookAdmin.save_model()`.
8. **Некоторые большие данные игнорируются Git.**  
   Для восстановления полного каталога нужны внешние JSON/Excel-файлы или серверная БД.
9. **В рабочей области уже есть изменения в старых `.md`-файлах.**  
   Этот файл создан отдельно как новая документация проекта.
10. **Автоматическое определение категории.**  
   Категория присваивается по году издания при сохранении книги. Логика в `BaseBookAdmin.save_model()`.
11. **Экспорт в несколько шаблонов Ozon поддерживается.**это работает только в локалке !
   Если активно несколько шаблонов `OzonTemplate` с разными диапазонами `year_from`/`year_to`, функция `export_books_to_ozon_template` распределяет книги по шаблонам согласно году издания. При одном активном шаблоне возвращается `.xlsx`; при двух и более — ZIP-архив (`ozon_templates_export.zip`) со всеми сгенерированными файлами.

11.**Экспорт в несколько шаблонов Ozon поддерживается.**это работает только в локалке !
   Если активно несколько шаблонов `OzonTemplate` с разными диапазонами `year_from`/`year_to`, функция `export_books_to_ozon_template` распределяет книги по шаблонам согласно году издания. При одном активном шаблоне возвращается `.xlsx`; при двух и более — ZIP-архив (`ozon_templates_export.zip`) со всеми сгенерированными файлами.
12. **Множественные авторы и издательства.**  
    Поля `author` и `publisher` в форме добавления/редактирования книги используют кастомный виджет `TagInputWidget`, который позволяет вводить несколько значений.  
    - Для добавления — нажмите Enter (или выберите подсказку)
    - Для удаления — нажмите × на теге или Backspace в пустом поле
    - Для автодополнения — начните печатать (подсказки из существующих значений)
    - Хранение в БД — через разделитель `"; "`, миграции не потребовались

---

## 17. Полезные команды

```bash
# Проверка Django
python manage.py check
# Применить миграции
python manage.py migrate
# Импортировать книги Эксмо (самостоятельный скрипт)
python import_eksmo_books.py --dry-run
# Импортировать книги АСТ из JSON
python import_ast.py
# Импортировать книги АСТ через пайп (без сохранения JSON на сервере)
cat books.json | python import_ast.py --stdin
# Обновить существующие книги Эксмо
python import_eksmo_books.py --update
# Извлечь размеры из большого JSON
python extract_dims.py --input vBaze/exmo_books.json --output vBaze/dims_only.json
# Заполнить размеры из compact JSON
python manage.py apply_dims_from_json --dry-run
# Заполнить размеры из аннотаций
python manage.py fill_dims_from_annotation --source eksmo --dry-run
# Конвертировать см в мм
python manage.py convert_dims_to_mm --dry-run
# Заполнить isbn_digits для книг с ISBN (если поле пустое)
python manage.py fill_isbn_digits
# Собрать статику
python manage.py collectstatic --noinput
# Замеры страниц админки «до/после» (запускать на сервере из корня проекта)
python deploy/measure_admin.py
# Тюнинг сервера: DEBUG=False, PostgreSQL, gunicorn, составной индекс (сначала dry-run)
bash deploy/optimize_A.sh --dry-run
```

---

## 18. Ветки и Git

Репозиторий разделён на ветки по назначению. Рабочая (стабильная) ветка — `main`; ветки-фичи выносятся отдельно, чтобы не смешивать незавершённый код с рабочим.

| Ветка | Содержимое | Статус |

| **`main`** | Рабочая ветка: экспорт в несколько шаблонов Ozon (вкл. ZIP-архив при ≥2 шаблонах), справочники `shablon/*.xml` | ✅ Стабильная, запушена в `origin` |
| **`production`** | Совпадает с `origin/production` (состояние на сервере), без экспериментальных фич | ✅ Стабильная |
| **`feature/avito-xml`** | Экспорт выбранных книг в XML для Avito (`export_books_to_avito_xml`, `admin_panel/avito_catalogs.py`) | ⚠️ WIP — **не работает** (см. раздел 8) |
| **`feature/zip-export`** | Снапшот логики ZIP-экспорта (несколько активных шаблонов Ozon → `.zip`) | ✅ Рабочая, идентична `main` |

Справочные XML для Avito (`shablon/autor.xml`, `shablon/siries.xml`, `shablon/avito.xml`) лежат на `main`/`feature/zip-export`, но **не** на `feature/avito-xml`. При доработке Avito-экспорта подтяните их в ветку фичи:

```bash
git checkout feature/avito-xml
git merge main        # подтянуть shablon/*.xml
```

Публикация веток на GitHub:

```bash
git push -u origin main feature/avito-xml feature/zip-export
```

---

## 19. Оптимизация админки `/admin/admin_panel/eksmobook/`

Диагностика выполнена на живом проде `v3144166.hosted-by-vdsina.ru` (только чтение,
временные скрипты после себя убраны). Все цифры ниже — **замеры на этом сервере**,
а не оценки.

---

### 1. Что сделано в этом патче

#### Вариант B — код (в этом репозитории, нужен деплой)

| Файл | Что изменено |
|---|---|
| `admin_panel/admin.py` | добавлены `PublicationPeriodFilter` и `TopPublisherFilter`; в `BaseBookAdmin.list_filter` убраны прямые `publisher` и `publication_year` |
| `shop_admin/settings.py` | добавлена явная секция `CACHES` (LocMemCache) под кэш фильтра издательств |

#### Вариант A — сервер (скрипт, запускается на сервере)

| Файл | Что делает |
|---|---|
| `deploy/optimize_A.sh` | `DEBUG=False`, тюнинг PostgreSQL, gunicorn sync → gthread, составной индекс, остановка мёртвого деплоя |
| `deploy/measure_admin.py` | замер страниц админки «до/после» |

---

### 2. Как применить

#### Шаг 0. Привести рабочую копию прода в порядок

Сейчас на сервере ветка `main`, HEAD на `15051e7`, и есть **незакоммиченная правка**
`admin_panel/migrations/0096_normalize_language_and_target_audience.py`.

Проверено: её содержимое **побайтово совпадает** с тем, что уже лежит в `main`
(коммит `17e9674`). То есть исправление сделали руками прямо на сервере вместо
деплоя. Его можно безопасно отбросить и просто подтянуть коммиты:

```bash
cd /home/semen/ready
git checkout -- admin_panel/migrations/0096_normalize_language_and_target_audience.py
git pull origin main      # приедет ровно тот же самый фикс 0096 (origin/main = 17e9674)
```

Проверено: `origin/main` указывает на `17e9674` — тот самый фикс. Прод стоит на
`15051e7`, то есть отстаёт на один коммит. Отбрасывать правку безопасно: её
содержимое придёт из репозитория.

Если этого не сделать, `git pull` и `git cherry-pick` будут спотыкаться о грязное
дерево, а `git reset --hard` уничтожит этот фикс.

#### Шаг 1. Код (вариант B)

```bash
# локально
git add admin_panel/admin.py shop_admin/settings.py deploy/
git commit -m "perf: фильтры админки — периоды вместо DISTINCT по 726k строк"
git push origin main

# на сервере
ssh semen@v3144166.hosted-by-vdsina.ru
cd /home/semen/ready
git pull origin main
source venv/bin/activate
python manage.py collectstatic --noinput
sudo systemctl restart gunicorn
```

Миграции не нужны — модели не менялись. `python manage.py check` проходит без замечаний.

> Учтите: локальная ветка `main` сейчас **на 2 коммита впереди `origin/main`**
> (`6a8c3e4` про tnved_code и `3f3b39b` про READdoki.md). `git push origin main`
> отправит и их — это нормально, просто чтобы не было неожиданностью.
> Альтернатива, если не хотите тащить их в прод сейчас:
> ```bash
> git checkout -b perf/admin-filters
> git add admin_panel/admin.py shop_admin/settings.py deploy/
> git commit -m "perf: фильтры админки — периоды вместо DISTINCT по 726k строк"
> git push origin perf/admin-filters
> ```
> и на сервере `git cherry-pick <хеш>`.

#### Шаг 2. Сервер (вариант A)

```bash
cd /home/semen/ready

# сначала посмотреть план, ничего не меняя
bash deploy/optimize_A.sh --dry-run

# применить; индексы лучше создавать ночью — это несколько минут нагрузки на диск
bash deploy/optimize_A.sh
```

Скрипт идемпотентен, бэкапит `.env` и `gunicorn.service` в
`/home/semen/ready/backups/optimize-A-<timestamp>/`.

#### Шаг 3. Проверка

```bash
cd /home/semen/ready && source venv/bin/activate
python deploy/measure_admin.py
```

---

### 3. Замеры: до и после

Страница прогонялась через Django test client на самом сервере с суперпользователем.

| Метрика | Было | После B (замерено) |
|---|---|---|
| **Список книг** | **15.79 с / 15.5 МБ** | **4.14 с / 248 КБ** |
| Список + поиск `?q=война` | 27.09 с | — (лечится вариантом D) |
| Форма добавления | 0.11 с | 0.11 с |
| Ссылок в сайдбаре | 82 722 | 54 |

Что ушло из 15.79 с:

| Запрос | Было | Стало |
|---|---|---|
| `SELECT DISTINCT publisher` | 4.78 с + 15.4 МБ HTML | **0** |
| `SELECT DISTINCT publication_year` | 4.26 с | **0** |
| `SELECT COUNT(*)` пагинатора | 4.03 с | 3.34 с (это вариант C, ещё не сделан) |
| Отрисовка шаблонов | ~2.5 с (следствие `DEBUG=True`) | лечится вариантом A |

Оставшиеся ~4 с — это ровно тот `COUNT(*)`, который убирает вариант C.

---

### 4. Что нашлось попутно и важно знать

#### 4.1. Фильтр по издательству был не просто медленным, а катастрофическим

Админка сортирует список по `created_at DESC` с `LIMIT 100`. Когда применён фильтр по
издательству, планировщик идёт по индексу `book_created_at_idx` назад и **отбрасывает всё,
что не подходит**:

```
Index Scan Backward using book_created_at_idx
  Filter: publisher = 'Издательство АСТ'
  Rows Removed by Filter: 457067        <-- вот оно
  Execution Time: 56543 ms
```

Книги в таблице **не сгруппированы по издательству**: АСТ импортирован раньше, а последние
сотни тысяч строк — почти целиком Эксмо. Поэтому «свежий» индекс приходится просматривать
почти насквозь.

Замеренные страницы с фильтром издательства **до** составного индекса:

| Значение фильтра | Время страницы |
|---|---|
| `Издательство "Эксмо"` | **100.85 с** |
| `Издательство АСТ` | **74.37 с** |
| `М.: АСТ` | 9.20 с |

Это **не регресс от варианта B**: такой запрос был ровно таким же медленным и до патча —
просто раньше до него было почти невозможно добраться через список из 82 024 значений.
Вариант B делает фильтр доступным, поэтому составной индекс обязателен:

```sql
CREATE INDEX CONCURRENTLY book_publisher_created_idx
    ON admin_panel_book (publisher, created_at DESC);
```

Он превращает это в чтение ровно 100 строк индекса вместо 456 967 отброшенных.
Скрипт `deploy/optimize_A.sh` создаёт его автоматически.

> Проверить фактический эффект можно только после создания индекса — `deploy/measure_admin.py`
> покажет время по строке «Список + фильтр издательства».

#### 4.2. Что НЕ помогает (проверено, в патч не вошло)

| Гипотеза | Результат замера | Вывод |
|---|---|---|
| `max_parallel_workers_per_gather = 0` (1 vCPU) | COUNT(*) **5.52 с** против 4.72 с с параллелью | **хуже**, не трогаем |
| `random_page_cost = 1.1` | план не меняется, 5.29 с | бесполезно, не трогаем |
| `work_mem` 4 → 16 МБ для `DISTINCT publisher` | сорт ушёл в память (7.6 МБ), но время то же | не главное, но оставляем |
| Индексировать `publisher` (одиночный) | индекс уже есть, план всё равно seq scan | дело не в индексе, а в `ORDER BY` + `LIMIT` |
| Создать `(publication_year, created_at DESC)` | периоды и так работают: worst case «до 1950» = 1.1 с, остальные < 5 мс | **не нужен** |

#### 4.3. Дрейф схемы: 7 индексов из `models.py` отсутствуют в БД

Миграции `0077` и `0078` помечены применёнными (24.06.2026), но их индексов в базе нет:

```
book_isbn_idx        book_author_idx      book_series_idx
book_category_idx    book_condition_idx   book_cover_type_idx
book_book_type_idx
```

**`python manage.py migrate` это не починит** — Django считает, что они уже созданы. Судя по
всему, таблицу когда-то пересоздавали, а `django_migrations` сохранился.

Хорошая новость: на текущую скорость они не влияют (фильтры по этим полям идут через `choices`
или FK-индекс). Это гигиена схемы, а не производительность. Если захотите восстановить:

```sql
CREATE INDEX CONCURRENTLY IF NOT EXISTS book_isbn_idx       ON admin_panel_book (isbn);
CREATE INDEX CONCURRENTLY IF NOT EXISTS book_author_idx     ON admin_panel_book (author);
CREATE INDEX CONCURRENTLY IF NOT EXISTS book_series_idx     ON admin_panel_book (series);
CREATE INDEX CONCURRENTLY IF NOT EXISTS book_book_type_idx  ON admin_panel_book (book_type);
CREATE INDEX CONCURRENTLY IF NOT EXISTS book_condition_idx  ON admin_panel_book (condition);
CREATE INDEX CONCURRENTLY IF NOT EXISTS book_cover_type_idx ON admin_panel_book (cover_type);
ANALYZE admin_panel_book;
```

`book_category_idx` создавать не нужно — он дублирует автоматический FK-индекс
`admin_panel_book_category_id_f4540259`.

#### 4.4. Кэш `LocMemCache` — на каждый воркер свой

В `settings.py` стоит локальный кэш процессов. У gunicorn 2 воркера, значит агрегат
топ-50 издательств посчитается 2 раза за 6 часов (≈5.2 с каждый раз). Это приемлемо.
С Redis кэш будет общим — код при этом не меняется, только `BACKEND`/`LOCATION`.

#### 4.5. Что уже один раз уронило прод: `Meta.ordering` + `DISTINCT`

Из незакоммиченной правки миграции 0096 (см. шаг 0) видно, что предыдущая её версия делала:

```python
Book.objects.exclude(language='').values_list('language', flat=True).distinct()
```

У `Book` задано `Meta.ordering = ['-created_at']`, поэтому Django подставил `created_at`
в `SELECT DISTINCT`. `created_at` уникален → вернулась почти вся таблица (726 k строк),
PostgreSQL отсортировал её целиком, а Django материализовал сотни тысяч строк в Python.
Итог, судя по комментарию в самой правке: 16+ ГБ чтения, 2 ч 43 мин CPU, диск 100 %,
`PANIC: could not write to pg_wal/xlogtemp` и аварийное завершение PostgreSQL
(crash recovery прошёл, данные уцелели). PostgreSQL на момент диагностики был поднят
примерно за 3 часа до неё, а исправленная 0096 применилась уже после рестарта.

Это ровно тот класс ошибки, от которого страхует `.order_by()` в `TopPublisherFilter`.
Правило для этого проекта простое: **любой `distinct()` или `annotate()` по `Book`
обязан начинаться с `.order_by()`**.

---

### 5. Полный диагноз (исходное состояние)

**Сервер:** 1 vCPU, 961 МБ RAM (+2 ГБ swap, 276 МБ занято), диск 10 ГБ (64 %),
`rotational=1`, PostgreSQL 16, `shared_buffers` 128 МБ, **cache hit 60 %**,
gunicorn 2 sync-воркера, `DEBUG=True`, второй мёртвый gunicorn из `/var/www/ready`.

**Данные:** `admin_panel_book` — **726 235 строк** (eksmo 577 658 / ast 147 818 / manual 759),
**937 МБ**, 12 индексов, **82 024 уникальных издательства**, 219 уникальных годов.

**Причины тормозов по вкладу:**

1. Фильтр `publisher` — `SELECT DISTINCT` по 726 k строк (4.8 с) **плюс** 82 722 ссылки
   в HTML = 15.4 МБ, от которых виснет браузер. → **исправлено в B**
2. `SELECT COUNT(*)` пагинатора — 4 с на каждое открытие. → *остаётся, вариант C*
3. Фильтр `publication_year` — ещё 4 с. → **исправлено в B**
4. Поиск: 13 полей `icontains` → `UPPER(col) LIKE UPPER('%...%')`, полный скан ~9.9 с.
   → *остаётся, вариант D*
5. `DEBUG=True` — нет кэша шаблонов, все 107 запросов пишутся в память. → **исправлено в A**
6. `_search_all_books()` делает `list(qs)` — выгружает все 726 k объектов в память Python
   (4.3–4.6 с на каждый AJAX при вводе). → *остаётся, вариант D*
7. Cache hit 60 % + 128 МБ `shared_buffers` + HDD. → **частично в A**
8. 2 sync-воркера: два медленных запроса блокируют весь сайт. → **исправлено в A**
9. `list_display` из 29 колонок. → *остаётся*
10. `EksmoBookAdmin.get_queryset` отдаёт все 726 k книг, хотя раздел называется «База книг».
    → *остаётся, продуктовое решение*

---

### 6. Что осталось на потом

#### Вариант C. Убрать `SELECT COUNT(*)` — минус последние 4 секунды

```python
# admin_panel/paginator.py
from django.core.paginator import Paginator
from django.db import connection


class ApproxCountPaginator(Paginator):
    """Не считает строки по всей таблице, если фильтров нет."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._count = None

    @property
    def count(self):
        if self._count is None:
            self._count = self._compute_count()
        return self._count

    def _compute_count(self):
        qs = self.object_list
        model = getattr(qs, 'model', None)
        if model is None or qs.query.where:
            return self.object_list.count()
        try:
            with connection.cursor() as cur:
                cur.execute(
                    "SELECT reltuples::bigint FROM pg_class WHERE oid = %s::regclass",
                    [model._meta.db_table],
                )
                return max(cur.fetchone()[0], 0)
        except Exception:
            return self.object_list.count()
```

```python
class BaseBookAdmin(admin.ModelAdmin):
    paginator = ApproxCountPaginator
    list_per_page = 25
```

Число страниц станет приблизительным — для 726 k строк это неважно.

#### Вариант D. Поиск и автодополнение

Ключевой нюанс: Django для `icontains` генерирует **`UPPER(col) LIKE UPPER('%...%')`**, а не
`ILIKE`. Поэтому триграммный индекс нужен **по выражению `UPPER(col)`** — обычный
`gin (col gin_trgm_ops)` не будет использован (проверено через `EXPLAIN`):

```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX CONCURRENTLY book_title_trgm
    ON admin_panel_book USING gin (UPPER(title) gin_trgm_ops);
-- аналогично author, author_oblozh, publisher, series, isbn_digits
```

Плюс переписать `_search_all_books()`, убрав `list(qs)` (все 492 748 строк с ISBN имеют
заполненный `isbn_digits`, поэтому питоновский перебор не нужен вообще), и сократить
`search_fields` с 13 полей до 5.

#### Вариант E. Инфраструктура

2 vCPU / 4 ГБ RAM / NVMe. Сейчас БД 937 МБ при 1 ГБ RAM и HDD — cache hit 60 %.
Это устраняет первопричину, а не симптомы. Плюс Redis под кэш и `CONN_MAX_AGE = 60`.

---

### 7. Безопасность — отдельно

`DEBUG=True` на проде (закрывается вариантом A) означал, что любая 500-я ошибка отдаёт
наружу трейсбек с настройками, SQL и путями к файлам. В логах nginx при этом видны
активные сканы: `/.git/config`, `/055b92507911e16e307c8525bae08828`,
`/LAPI/V1.0/System/DeviceBasicInfo` (эксплойт IP-камер). Закрыть это стоит в первую очередь.

---

### 8. Удаление фильтров из сайдбара (26.09.2026)

По задаче боковая панель фильтров почищена: остался только «Период издания».

| Фильтр | Тип | Было | Стало |
|---|---|---|---|
| `category` | встроенный Django (`RelatedFieldListFilter`) | в сайдбаре | убран |
| `genre` | встроенный (`ChoicesFieldListFilter`) | в сайдбаре | убран |
| `language` | встроенный | в сайдбаре | убран |
| `book_type` | встроенный | в сайдбаре | убран |
| `TopPublisherFilter` | кастомный | в сайдбаре | убран |
| `PublicationPeriodFilter` | кастомный | в сайдбаре | **оставлен** |

Правка одна на обе страницы: `BaseBookAdmin.list_filter` в `admin_panel/admin.py`.
Наследники — `EksmoBookAdmin` («База книг», `/admin/admin_panel/eksmobook/`)
и `ManualBookAdmin` («Каталог — админка», `/admin/admin_panel/manualbook/`).

Классы `PublicationPeriodFilter` и `TopPublisherFilter` **в коде оставлены**:
`TopPublisherFilter` импортирует `deploy/measure_admin.py` (без него падают замеры)
и на него ссылается секция `CACHES` в `shop_admin/settings.py`.

| Файл | Что изменено |
|---|---|
| `admin_panel/admin.py` | в `BaseBookAdmin.list_filter` остался только `PublicationPeriodFilter`; убраны `'category'`, `'genre'`, `'language'`, `'book_type'` и `TopPublisherFilter` |
| `admin_panel/tests.py` | было 3 строки заглушки, добавлены 5 тестов |

Тесты (`SimpleTestCase`, база данных не нужна):

1. в `list_filter` ровно один фильтр — «Период издания»;
2. стандартных фильтров Django в сайдбаре больше нет;
3. `TopPublisherFilter` убран из сайдбара, но класс остался в модуле;
4. «База книг» и «Каталог — админка» показывают один и тот же набор фильтров;
5. у «Периода издания» статические `lookups` — запросов к БД нет.

Проверка:

```bash
python manage.py check                # System check identified no issues (0 silenced).
python manage.py test admin_panel -v2 # Ran 5 tests in 0.001s ... OK
```

Тесты не трогают PostgreSQL: `SimpleTestCase` не требует БД, раннер пишет
`Skipping setup of unused database(s): default.`

Чтобы фильтры исчезли на проде, нужен деплой кода и `sudo systemctl restart gunicorn`
(как в шаге 1 выше). Миграции не нужны — модели не менялись.

---

## 20. Краткое резюме

`ready` — это Django-админка для книжного магазина с упором на импорт каталога Эксмо, ручное управление товарами, загрузку фотографий и экспорт данных для Ozon. Основное рабочее место администратора — Django Admin. Основной источник товаров — модель `Book` с разделением по `source=manual` и `source=eksmo`. Для Ozon реализован безопасный офлайн-экспорт в Excel-шаблон, а прямой API пока отключён.

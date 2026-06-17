
# Ready — Django-админка для книжного магазина

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
├── import_books.py                   # legacy-скрипт импорта книг
├── merge_json.py                     # объединение JSON-файлов
├── extract_dims.py                   # извлечение размеров из JSON
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
- `author` — автор
- `author_oblozh` — автор на обложке
- `genre` — направление
- `publisher` — издательство
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

### Proxy-модели

- `ManualBook(Book)` — ручные книги магазина.
- `EksmoBook(Book)` — каталог Эксмо.

## Proxy-модели позволяют разделять книги в админке по источнику, не создавая отдельные таблицы

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

## 7. Экспорт

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
5. Поля маппятся по русским названиям колонок Ozon.

Заполняются поля:

- артикул
- название товара
- цена
- цена до скидки
- НДС
- вес и размеры
- автор
- автор на обложке
- тип обложки
- тип товара
- бренд
- ТН ВЭД
- издательство
- серия
- год выпуска
- язык
- количество страниц
- ISBN
- аннотация
- главное фото
- дополнительные фото

Фотографии преобразуются из относительных путей в полные URL через `MEDIA_BASE_URL`.

---

## 8. Ozon-интеграция

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

## 9. Импорт и обработка данных

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

### `admin_panel/management/commands/import_eksmo_books.py`

Основная Django-команда импорта Эксмо.
Запуск:

```bash

python manage.py import_eksmo_books
python manage.py import_eksmo_books --update
python manage.py import_eksmo_books --dry-run
python manage.py import_eksmo_books --file /path/to/file.json

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

## 10. Данные и большие файлы

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

## 11. Маршруты

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

## 12. Шаблоны и frontend

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
Демо-страницы `/shop/` не подключены к реальным моделям и показывают статический текст.

---

## 13. Миграции

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

## 14. Деплой

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

## 15. Известные особенности и ограничения

1. **Ozon API отключён.**  
   Работает только экспорт в Excel-шаблон Ozon. Прямая загрузка через API закомментирована.
2. **Демо-страницы `/shop/` не являются магазином.**  
   Они не выводят товары, заказы и клиентов из БД.
3. **`dashboard.html` содержит устаревшую строку про Django 6.0.3.**  
   В `requirements.txt` и проекте используется Django 5.1.4.
4. **`import_books.py` — legacy-скрипт.**  
   Более актуальная команда — `python manage.py import_eksmo_books`.
5. **Размеры хранятся в мм.**  
   Для старых данных есть команда `convert_dims_to_mm`.
6. **Фото книг хранятся как JSONField со списком относительных путей.**  
   Загрузка файлов выполняется в `BaseBookAdmin.save_model()`.
7. **Некоторые большие данные игнорируются Git.**  
   Для восстановления полного каталога нужны внешние JSON/Excel-файлы или серверная БД.
8. **В рабочей области уже есть изменения в старых `.md`-файлах.**  
   Этот файл создан отдельно как новая документация проекта.
9. **Автоматическое определение категории.**  
   Категория присваивается по году издания при сохранении книги. Логика в `BaseBookAdmin.save_model()`.

---

## 16. Полезные команды

```bash
# Проверка Django
python manage.py check
# Применить миграции
python manage.py migrate
# Импортировать книги Эксмо
python manage.py import_eksmo_books --dry-run
# Обновить существующие книги Эксмо
python manage.py import_eksmo_books --update
# Извлечь размеры из большого JSON
python extract_dims.py --input vBaze/exmo_books.json --output vBaze/dims_only.json
# Заполнить размеры из compact JSON
python manage.py apply_dims_from_json --dry-run
# Заполнить размеры из аннотаций
python manage.py fill_dims_from_annotation --source eksmo --dry-run
# Конвертировать см в мм
python manage.py convert_dims_to_mm --dry-run
# Собрать статику
python manage.py collectstatic --noinput
```

---

## 17. Краткое резюме

`ready` — это Django-админка для книжного магазина с упором на импорт каталога Эксмо, ручное управление товарами, загрузку фотографий и экспорт данных для Ozon. Основное рабочее место администратора — Django Admin. Основной источник товаров — модель `Book` с разделением по `source=manual` и `source=eksmo`. Для Ozon реализован безопасный офлайн-экспорт в Excel-шаблон, а прямой API пока отключён.

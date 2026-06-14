# Проект "Горы Книг" - Админка интернет-магазина

## Подробная техническая документация для глубокого изучения

## Очень важно

- отвечай всегда кратко !!!!
- отвечай только на русском языке !!!
- делай все всегда быстро !!!
- Этот файл создан для глубокого изучения проекта
- Все комментарии и примечания написаны на русском языке
- Проект создан с использованием современных стека технологий

```fish
# Активация виртуального окружения (Fish shell)
source ../goryKnig_venv/bin/activate.fish

# Запуск сервера
python manage.py runserver

```zsh
# Активация виртуального окружения 
source venv/bin/activate

# Запуск сервера
python manage.py runserver

```

## Общее описание

**Название проекта:** Горы Книг  
**Тип:** Админ панель для интернет-магазина  
**Версия Django:** 5.1.4  
**База данных:** PostgreSQL  
**Язык интерфейса:** Русский  
**Фреймворк:** Django 5.1.4  
**Функции экспорта:** Excel (.xlsx), Ozon шаблоны (.xlsx)

Проект представляет собой административную панель для управления интернет-магазином книг. Создан с использованием современного стека технологий и готов к дальнейшей разработке и масштабированию.

## Технический стек

### Backend

- **Django 5.1.4** - веб-фреймворк
- **PostgreSQL** - система управления базами данных
- **psycopg2-binary 2.9.10** - драйвер для подключения PostgreSQL к Python
- **PyYAML 6.0.2** - библиотека для работы с YAML форматом
- **openpyxl 3.1.2** - библиотека для работы с Excel файлами (.xlsx)
- **python-decouple 3.8** - загрузка конфигурации из переменных окружения (.env)
- **Python 3.14** - язык программирования

### Frontend

- **HTML5** - разметка
- **CSS3** - стилизация (встроенные стили)
- **JavaScript** - интерактивность (минимально)

### Среда разработки

- **Virtual Environment (venv)** - изолированное окружение Python
- **Fish Shell** - командная оболочка (используется пользователем)
- **macOS** - операционная система
- **Homebrew** - менеджер пакетов для PostgreSQL

## Структура проекта

```text
goryKnig/
├── shop_admin/                    # Основной пакет Django
│   ├── __init__.py               # Пустой файл для пакета
│   ├── asgi.py                   # ASGI конфигурация
│   ├── settings.py               # Основные настройки проекта
│   ├── urls.py                   # Главные URL маршруты
│   └── wsgi.py                   # WSGI конфигурация
├── admin_panel/                   # Приложение админки
│   ├── __init__.py               # Пустой файл для пакета
│   ├── admin.py                  # Конфигурация админки Django
│   ├── apps.py                   # Конфигурация приложения
│   ├── migrations/               # Директория миграций (14 файлов)
│   ├── models.py                 # Модели данных (Book, Category, ManualBook, EksmoBook)
│   ├── tests.py                  # Тесты приложения
│   ├── urls.py                   # URL маршруты приложения
│   ├── views.py                  # View функции
│   ├── widgets.py                # Кастомные виджеты (MultipleImageWidget)
│   ├── management/               # Команды управления Django
│   │   └── commands/             # Кастомные команды
│   │       └── import_eksmo_books.py # Импорт книг из JSON
│   └── templates/                # Шаблоны приложения
│       └── admin_panel/          # Шаблоны админки
│           ├── base.html         # Базовый шаблон
│           ├── dashboard.html    # Главная панель
│           ├── products.html     # Управление товарами
│           ├── orders.html       # Управление заказами
│           ├── customers.html    # Управление клиентами
│           ├── change_form.html  # Кастомный шаблон формы админки
│           ├── change_list.html  # Кастомный шаблон списка (кнопка экспорта Ozon)
│           └── multiple_image_widget.html # Шаблон виджета загрузки фото
├── manage.py                     # Управляющий скрипт Django
├── requirements.txt              # Зависимости Python
├── .env.example                  # Пример переменных окружения
├── goryKnig.md                  # Детальная документация (этот файл)
├── parsing/                     # Данные для импорта
│   └── eksmo_books_mt_deduped.json # JSON файл с книгами Эксмо (12MB)
└── media/                        # Директория для загруженных файлов
    └── book_photos/              # Фотографии книг
```

../goryKnig_venv/                 # Виртуальное окружение (вне корня проекта)

## Подробное описание компонентов

### 1. Основные настройки (shop_admin/settings.py)

#### Загрузка конфигурации

```python
from decouple import config, Csv
```

Использует python-decouple для загрузки переменных окружения из .env файла.

#### База данных

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='shop_admin_db'),
        'USER': config('DB_USER', default='postgres'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}
```

- **ENGINE:** `django.db.backends.postgresql` - использование PostgreSQL
- **NAME:** `shop_admin_db` - имя базы данных
- **USER:** `postgres` - пользователь PostgreSQL
- **PASSWORD:** пустая строка (стандартно для Homebrew на macOS)
- **HOST:** `localhost` - локальный сервер
- **PORT:** `5432` - стандартный порт PostgreSQL

#### Безопасность

```python
SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())
```

- **SECRET_KEY:** секретный ключ для криптографической подписи (в продакшене должен быть в переменных окружения)
- **DEBUG:** True - режим отладки (в продакшене должен быть False)
- **ALLOWED_HOSTS:** пустой список (в продакшене нужно добавить домен)

#### Международные настройки

```python
LANGUAGE_CODE = 'ru-ru'    # Русский язык
TIME_ZONE = 'Europe/Moscow'  # Московская временная зона
USE_I18N = True              # Включена интернационализация
USE_TZ = True                # Включена поддержка часовых поясов
```

#### Установленные приложения

```python
INSTALLED_APPS = [
    'django.contrib.admin',      # Панель администратора Django
    'django.contrib.auth',       # Система аутентификации
    'django.contrib.contenttypes', # Типы контента
    'django.contrib.sessions',   # Сессии
    'django.contrib.messages',   # Сообщения
    'django.contrib.staticfiles', # Статические файлы
    'admin_panel',              # Наше приложение админки
]
```

### 2. Приложение admin_panel

#### Модель данных Category (admin_panel/models.py)

Модель категорий для связи с Ozon:

- `name` - Название категории (CharField, max_length=200)
- `ozon_category_id` - Уникальный ID категории Ozon (CharField, max_length=50, unique)
- `description` - Описание категории (TextField, blank)
- `created_at` - Дата создания (DateTimeField, auto_now_add=True)

**Meta:**

- verbose_name = "Категория"
- verbose_name_plural = "Категории"
- ordering = ['name']

#### Proxy-модели (admin_panel/models.py)

**ManualBook** - прокси-модель для книг из админки (source='manual')

- verbose_name = "Книга (админка)"
- verbose_name_plural = "Каталог — админка"

**EksmoBook** - прокси-модель для книг из импорта Эксмо (source='eksmo')

- verbose_name = "Книга (Эксмо)"
- verbose_name_plural = "Каталог — Эксмо"

Позволяют разделять каталоги в админке Django.

#### Модель данных Book (admin_panel/models.py)

Модель Book полностью реализована и содержит следующие поля:

**Основная информация:**

- `title` - Название книги (CharField, max_length=200)
- `source` - Источник (choices: 'manual' - Админка, 'eksmo' - Импорт Эксмо, db_index=True)
- `sku` - Артикул (CharField, max_length=50, unique, nullable)
- `category` - Внешний ключ на модель Category (ForeignKey, nullable)
- `author` - Автор (CharField, max_length=100)
- `author_oblozh` - Автор на обложке (CharField, max_length=100)
- `genre` - Жанр (CharField, max_length=100)
- `publisher` - Издательство (CharField, max_length=100)
- `series` - Серия (CharField, max_length=200, nullable)
- `publication_year` - Год издания (PositiveIntegerField, nullable)
- `language` - Язык издания (CharField, max_length=50)
- `condition` - Сохранность (choices: 'excellent' - Отличная, 'good' - Хорошая, nullable)
- `cover_type` - Тип переплёта (choices: 'hard' - Твердый, 'soft' - Мягкий)
- `pages` - Количество страниц (PositiveIntegerField, nullable)
- `photos` - Фотографии (JSONField, список путей к файлам, до 10 фото)
- `description` - Описание (TextField, blank)

**Коммерческая информация:**

- `price` - Цена (DecimalField, max_digits=10, decimal_places=2)
- `old_price` - Старая цена / цена до скидки (DecimalField, nullable)
- `vat_rate` - Ставка НДС (choices: '0' - Без НДС, '10' - 10%, '20' - 20%)
- `stock` - Остаток на складе (PositiveIntegerField, default=1)
- `isbn` - ISBN (CharField, max_length=20, nullable, уникальный с source)

**Логистика:**

- `weight` - Вес с упаковкой в кг (DecimalField, max_digits=6, decimal_places=4, nullable)
- `length` - Длина с упаковкой в см (DecimalField, max_digits=6, decimal_places=2, nullable)
- `width` - Ширина с упаковкой в см (DecimalField, max_digits=6, decimal_places=2, nullable)
- `height` - Высота с упаковкой в см (DecimalField, max_digits=6, decimal_places=2, nullable)

**Даты:**

- `publication_date` - Дата публикации (DateField, nullable)
- `created_at` - Дата создания (DateTimeField, auto_now_add=True)
- `updated_at` - Дата обновления (DateTimeField, auto_now=True)

**Meta:**

- verbose_name = "Книга"
- verbose_name_plural = "Книги"
- ordering = ['-created_at']
- constraints: UniqueConstraint для (isbn, source) когда isbn не null

#### URL маршрутизация (admin_panel/urls.py)

```python
urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('products/', views.products, name='products'),
    path('orders/', views.orders, name='orders'),
    path('customers/', views.customers, name='customers'),
    path('export-ozon-yml/', views.export_ozon_yml, name='export_ozon_yml'),
]
```

**Примечание:** URL `export-ozon-yml/` используется для экспорта всех книг в Ozon YML (кнопка в шапке списка книг).

#### View функции (admin_panel/views.py)

- **dashboard()** - главная панель управления
- **products()** - управление товарами
- **orders()** - управление заказами
- **customers()** - управление клиентами
- **export_ozon_yml()** - экспорт книг в Ozon YML формате

#### Django Admin конфигурация (admin_panel/admin.py)

**CategoryAdmin - админка для модели Category:**

- `list_display` - name, ozon_category_id, created_at
- `search_fields` - name, ozon_category_id
- `ordering` - name

**ManualBookAdmin и EksmoBookAdmin** - отдельные админки для proxy-моделей

- Позволяют разделять каталоги в интерфейсе

**BookAdmin - кастомная админка для модели Book:**

- **change_form_template** - использует кастомный шаблон 'admin_panel/change_form.html'
- **formfield_for_dbfield** - подменяет виджет для поля photos на MultipleImageWidget
- **save_model** - кастомный метод сохранения с обработкой загрузки фото:

  - Обрабатывает удаление фото через скрытое поле photos_existing
  - Обрабатывает удаление фото через скрытое поле photos_existing
  - Загружает новые файлы в media/book_photos/
  - Генерирует уникальные имена файлов с UUID
  - Ограничивает количество фото до 10
  - Объединяет существующие фото с новыми

- **list_display** - поля в списке: title, author, author_oblozh, genre, publisher, language, cover_type, pages, price, old_price, stock, publication_year, created_at
- **list_filter** - фильтры: category, genre, publisher, language, cover_type, vat_rate, publication_year, publication_date, created_at
- **search_fields** - поиск по: title, author, author_oblozh, genre, publisher, language, isbn
- **ordering** - сортировка по -created_at
- **actions** - export_selected_ozon (экспорт выбранных книг в Ozon YML)
- **readonly_fields** - только для чтения: created_at, updated_at

- **fieldsets** - группировка полей:

  - Основная информация: title, category, author, author_oblozh, genre, publisher, publication_year, language, cover_type, pages, photos, description
  - Основная информация: title, category, author, author_oblozh, genre, publisher, publication_year, language, cover_type, pages, photos, description
  - Коммерческая информация: price, old_price, vat_rate, stock, isbn
  - Логистика: weight, length, width, height
  - Даты (свернуто): publication_date, created_at, updated_at

#### Функция экспорта в Ozon YML (admin_panel/views.py)

Функция `export_ozon_yml()` генерирует YAML-файл для загрузки товаров на маркетплейс Ozon.

**Особенности:**

- Валидация обязательных полей перед экспортом (название, цена > 0, категория с Ozon ID, остаток, фото)
- Два режима экспорта:

  - Экспорт выбранных книг (через action в админке)
  - Экспорт всех книг (кнопка в шапке списка)
- Формирует YAML со структурой:

  ```yaml
  shop_id: <OZON_SHOP_ID>
  offers:
    - offer_id: <id книги>
      name: <название>
      price: <цена>
      currency_code: RUB
      category_id: <ozon_category_id>
      vendor: <издательство>
      author: <автор>
      year: <год издания>
      isbn: <ISBN>
      description: <описание>
      stock: <остаток>
      vat: <ставка НДС>
      old_price: <старая цена> (если есть)
      pictures: [<URL фото>] (если есть)
      weight: <вес> (если есть)
      depth: <длина> (если есть)
      width: <ширина> (если есть)
      height: <высота> (если есть)
  ```

- Файл сохраняется с именем `ozon_export.yml`

**Обязательные поля для успешного экспорта:**

1. Название книги (title)
2. Цена > 0 (price)
3. Категория с заполненным ozon_category_id
4. Остаток на складе (stock)
5. Хотя бы одна фотография (photos)

#### Кастомный виджет MultipleImageWidget (admin_panel/widgets.py)

**MultipleImageWidget** - виджет для множественной загрузки фотографий:

- **template_name** - 'admin_panel/multiple_image_widget.html'
- **render()** - рендерит виджет с контекстом:

  - photos - список существующих фото
  - photos - список существующих фото
  - photos_json - JSON строка для JavaScript
  - MEDIA_URL - путь к медиа файлам

- **value_from_datadict()** - обработка данных формы:
  - Получает загруженные файлы
  - Сохраняет файлы с уникальными именами (UUID)
  - Объединяет существующие и новые фото
  - Ограничивает общее количество до 10

- **format_value()** - форматирование значения для отображения

#### Шаблоны

**base.html** - базовый шаблон с:

- Современным CSS дизайном (цветовая схема: #2c3e50, #34495e)
- Боковой навигацией с 4 разделами
- Адаптивной версткой (Flexbox и CSS Grid)
- Подсветкой активного раздела
- Системными шрифтами macOS (-apple-system, BlinkMacSystemFont)

**dashboard.html** - главная панель со статистикой:

- 4 карточки статистики (товары, заказы, клиенты, продажи)
- Приветственное сообщение
- Секция быстрых действий

**multiple_image_widget.html** - шаблон виджета загрузки фото:

- Отображение загруженных фотографий с превью
- Кнопки удаления для каждого фото
- Поле для множественной загрузки файлов (multiple)
- Предпросмотр выбранных файлов с размером
- Скрытое поле для существующих фото (photos_existing)
- JavaScript для управления списком фото
- Ограничение до 10 фотографий

**change_form.html** - кастомный шаблон формы админки:

- JavaScript для автоматической установки enctype="multipart/form-data"
- MutationObserver для отслеживания изменений DOM
- Перехват отправки формы для корректной загрузки файлов

**change_list.html** - кастомный шаблон списка книг:

- Кнопка «📥 Экспорт всех в Ozon YML» в шапке списка
- Ссылка на URL `/admin/admin_panel/book/export-ozon-yml/`

**products.html** - управление товарами (заглушка)
**orders.html** - управление заказами (заглушка)
**customers.html** - управление клиентами (заглушка)

### 3. Настройки MEDIA файлов (shop_admin/settings.py)

```python
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'
```

- **MEDIA_URL** - URL префикс для медиа файлов
- **MEDIA_ROOT** - путь к директории для хранения загруженных файлов
- Фотографии книг сохраняются в `media/book_photos/`

### 4. Главная URL конфигурация (shop_admin/urls.py)

```python
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('admin_panel.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

- В режиме DEBUG добавляется раздача MEDIA файлов
- Позволяет просматривать загруженные фотографии по URL /media/

## Процесс установки и настройки

### 1. Создание проекта

```fish
# Создание директории проекта
mkdir goryKnig
cd goryKnig

# Создание виртуального окружения в родительской директории
python3 -m venv ../goryKnig_venv

# Установка Django
../goryKnig_venv/bin/pip install Django==6.0.3

# Создание Django проекта
../goryKnig_venv/bin/python3 -m django startproject shop_admin .
```

### 2. Создание приложения админки

```fish
../goryKnig_venv/bin/python3 manage.py startapp admin_panel
```

### 3. Настройка PostgreSQL

```fish
# Установка PostgreSQL через Homebrew
brew install postgresql@18

# Запуск PostgreSQL
brew services start postgresql@18

# Создание базы данных
createdb shop_admin_db
```

### 4. Установка зависимостей

```fish
# Установка драйвера PostgreSQL
../goryKnig_venv/bin/pip install psycopg2-binary==2.9.10

# Запись зависимостей в файл
echo "Django==5.1.4" > requirements.txt
echo "psycopg2-binary==2.9.10" >> requirements.txt
echo "PyYAML==6.0.2" >> requirements.txt
echo "python-decouple==3.8" >> requirements.txt
```

### 5. Миграции базы данных

```fish
../goryKnig_venv/bin/python3 manage.py migrate
```

### 6. Создание суперпользователя

```fish
../goryKnig_venv/bin/python3 manage.py createsuperuser
# Имя: knigi
# Email: (пустой)
# Пароль: (установлен пользователем)
```

## Особенности реализации

### 1. Дизайн интерфейса

- **Цветовая схема:** Темно-серая (#2c3e50, #34495e)
- **Шрифты:** Системные шрифты macOS (-apple-system, BlinkMacSystemFont)
- **Верстка:** Flexbox и CSS Grid
- **Адаптивность:** Поддержка мобильных устройств

### 2. Навигация

- Боковая панель с 4 разделами
- Подсветка активного раздела
- Плавные переходы и анимации

### 3. Структура данных

- Реализована полная модель Book с 22 полями
- Поддержка множественной загрузки фотографий (до 10 штук)
- Интеграция с Django Admin через BookAdmin
- Готовность к добавлению моделей заказов и клиентов

## Текущий функционал

### 1. Основная админка (<http://127.0.0.1:8000>)

- Главная панель с демонстрационной статистикой
- Разделы товаров, заказов, клиентов
- Современный интерфейс

### 2. Django Admin (<http://127.0.0.1:8000/admin>)

- Полнофункциональная админка для модели Book
- Создание, редактирование, удаление книг
- Множественная загрузка фотографий (до 10 штук)
- Предпросмотр и удаление загруженных фото
- Фильтрация по категории, жанру, издательству, языку, типу переплёта, НДС, году, дате публикации
- Поиск по названию, автору, автору на обложке, жанру, издательству, языку, ISBN
- Группировка полей по категориям (Основная, Коммерческая, Логистика, Даты)
- Отображение списка с ключевыми полями
- Сортировка по дате создания (новые сверху)
- Поля только для чтения (created_at, updated_at)
- Аутентификация пользователей
- Управление группами и правами

## Потенциальные улучшения

### 1. Дополнительные модели данных

Модели Category и Book уже реализованы. Примеры будущих моделей:

```python
# Пример будущих моделей для admin_panel/models.py
class Order(models.Model):
    customer_name = models.CharField(max_length=100)
    customer_email = models.EmailField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

class Customer(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)
    address = models.TextField()
```

**Примечание:** Модели Category и Book уже полностью реализованы.

### 2. API эндпоинты

- REST API для мобильного приложения
- GraphQL для сложных запросов
- WebSocket для реального времени

### 3. Дополнительные функции

- Система уведомлений
- Аналитика и отчеты
- Интеграция с платежными системами
- Управление складом
- SEO оптимизация

## История миграций базы данных

Проект имеет 14+ миграций (0001-0015+), которые показывают эволюцию модели Book:

- **0001_initial.py** - начальная миграция
- **0002_remove_book_authors_remove_book_genres_and_more.py** - удаление полей authors и genres
- **0003_initial.py** - создание моделей Author, Category, Publisher, Book с связями ManyToMany
- **0004_remove_book_authors_remove_book_categories_and_more.py** - удаление связей
- **0005_book_genre_book_publication_year_book_publisher.py** - добавление полей genre, publication_year, publisher
- **0006_book_cover_type_book_language_book_pages_and_more.py** - добавление полей cover_type, language, pages, description
- **0007_book_old_price_book_stock_book_vat_rate_and_more.py** - добавление коммерческих полей old_price, stock, vat_rate
- **0008_book_author_oblozh_book_height_book_length_and_more.py** - добавление полей author_oblozh, height, length, width, weight
- **0009_bookphoto_book_photos.py** - создание модели BookPhoto и добавление поля photos
- **0010_remove_book_photos_book_images_delete_bookphoto.py** - удаление поля photos и модели BookPhoto
- **0011_remove_book_images_bookimage.py** - удаление поля images
- **0012_book_photo_delete_bookimage.py** - удаление модели BookImage
- **0013_remove_book_photo_book_photos.py** - удаление поля photo
- **0014_alter_book_photos.py** - добавление поля photos как JSONField

**Текущее состояние:** Модель Book использует JSONField для хранения списка путей к фотографиям, что позволяет хранить до 10 фото на одну книгу.

### Команда импорта книг Эксмо (admin_panel/management/commands/import_eksmo_books.py)

**Функция:** Импорт каталога книг из JSON файла в модель Book с source='eksmo'.

**Запуск:**

```fish
# Базовый импорт
python manage.py import_eksmo_books

# Обновление существующих записей по ISBN
python manage.py import_eksmo_books --update

# Тестовый запуск без записи в БД
python manage.py import_eksmo_books --dry-run

# Указание пути к файлу
python manage.py import_eksmo_books --file /путь/к/файлу.json
```

**Особенности:**

- По умолчанию использует `parsing/eksmo_books_mt_deduped.json`
- Пакетная запись (BATCH_SIZE = 500)
- Валидация ISBN (10 или 13 цифр)
- Парсинг размеров из формата «125x200 мм»
- Парсинг типа переплёта из текста
- Режим --update: сопоставление по цифрам ISBN, сохранение с дефисами
- Пропускает записи без валидного ISBN

**Поля импорта:**

- title, author, publisher, series, publication_year
- cover_type, pages, description
- width, length, height (из format и thickness)
- isbn (с дефисами, до 20 символов)
- source=eksmo, price=0, stock=0, photos=[]

### Дополнительные файлы проекта

**shop_admin/asgi.py** - ASGI конфигурация для асинхронного сервера
**shop_admin/wsgi.py** - WSGI конфигурация для традиционных серверов
**admin_panel/apps.py** - конфигурация приложения AdminPanelConfig
**admin_panel/tests.py** - файл для тестов приложения (пока пустой)
**parsing/eksmo_books_mt_deduped.json** - JSON файл с данными книг Эксмо (12MB)

## Команды управления

### Базовые команды Django
```fish
# Запуск сервера разработки
../goryKnig_venv/bin/python3 manage.py runserver

# Создание миграций
../goryKnig_venv/bin/python3 manage.py makemigrations

# Применение миграций
../goryKnig_venv/bin/python3 manage.py migrate

# Создание суперпользователя
../goryKnig_venv/bin/python3 manage.py createsuperuser

# Сбор статических файлов
../goryKnig_venv/bin/python3 manage.py collectstatic

# Запуск тестов
../goryKnig_venv/bin/python3 manage.py test
```

### Команды PostgreSQL
```fish
# Подключение к базе данных
psql -h localhost -U postgres -d shop_admin_db

# Создание новой базы данных
createdb new_database_name

# Удаление базы данных
dropdb database_name

# Резервное копирование
pg_dump shop_admin_db > backup.sql

# Восстановление из резервной копии
psql shop_admin_db < backup.sql
```

## Конфигурация окружения

### Переменные окружения (.env.example)
```
# Database
DB_NAME=shop_admin_db
DB_USER=postgres
DB_PASSWORD=your_password_here
DB_HOST=localhost
DB_PORT=5432

# Django
SECRET_KEY=your_secret_key_here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Ozon Integration
OZON_SHOP_ID=your_ozon_shop_id_here
```

### Требования к системе
- **Python:** 3.10+
- **PostgreSQL:** 12+
- **Операционная система:** macOS/Linux/Windows
- **Память:** минимум 2GB RAM
- **Дисковое пространство:** минимум 1GB

## Безопасность

### Текущие меры безопасности
- DEBUG = True (только для разработки)
- SECRET_KEY в настройках
- Защита от CSRF атак
- Валидация паролей

### Рекомендации для продакшена
- Установить DEBUG = False
- Настроить ALLOWED_HOSTS
- Использовать переменные окружения для чувствительных данных
- Настроить HTTPS
- Регулярные резервные копии
- Мониторинг безопасности

## Развертывание

### Для разработки
```fish
# Активация виртуального окружения (Fish shell)
source ../goryKnig_venv/bin/activate.fish

# Запуск сервера
python manage.py runserver
```

### Для продакшена (рекомендации)
- Использовать Gunicorn + Nginx
- Настроить системный сервис (systemd)
- Настроить SSL сертификаты
- Настроить мониторинг и логирование
- Использовать контейнеризацию (Docker)

## Тестирование

### Запуск тестов
```fish
# Запуск всех тестов
../goryKnig_venv/bin/python3 manage.py test

# Запуск тестов конкретного приложения
../goryKnig_venv/bin/python3 manage.py test admin_panel

# Запуск с покрытием кода
../goryKnig_venv/bin/python3 manage.py test --coverage
```

### Структура тестов
- Тесты моделей (models.py)
- Тесты представлений (views.py)
- Тесты форм (forms.py)
- Тесты API (api.py)

## Логирование

### Настройка логирования (будущая реализация)
```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'django.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

## Мониторинг и аналитика

### Возможные инструменты
- **Sentry** - отслеживание ошибок
- **New Relic** - производительность приложения
- **Google Analytics** - статистика использования
- **Prometheus + Grafana** - метрики и дашборды

## Версионирование

### История версий
- **v1.0.0** - Базовая структура проекта
  - Django 6.0.3
  - PostgreSQL интеграция
  - Базовый UI админки
  - Аутентификация пользователей

### Планируемые версии
- **v1.1.0** - Модели данных и CRUD операции
- **v1.2.0** - REST API
- **v1.3.0** - Расширенная аналитика
- **v2.0.0** - Микросервисная архитектура

## Заключение

Проект "Горы Книг" представляет собой современную, масштабируемую админ панель для интернет-магазина. Создан с использованием лучших практик Django и готов к дальнейшей разработке. Архитектура проекта позволяет легко добавлять новый функционал и интегрировать с внешними сервисами.

**Ключевые преимущества:**
- Современный технологический стек
- Чистая архитектура кода
- Готовность к масштабированию

---

## Функционал экспорта данных

### 1. Экспорт в Excel

**Описание:** Экспорт выбранных книг в стандартный Excel файл (.xlsx) со всеми данными.

**Как использовать:**
1. Перейдите в раздел "Каталог — админка" или "Каталог — Эксмо"
2. Выберите нужные книги через чекбоксы
3. В выпадающем списке действий выберите "Экспортировать выбранные в Excel"
4. Нажмите "Выполнить"
5. Скачается файл `books_export.xlsx`

**Структура экспорта:**
- 25 колонок с полной информацией о книгах
- Заголовки: ID, Артикул, Название, Автор, Жанр, Издательство, ISBN, Цена, и т.д.
- Автоматическая ширина колонок
- Форматирование заголовков (жирный шрифт, выравнивание)

**Технические детали:**
- Библиотека: `openpyxl 3.1.2`
- Функция: `export_books_to_excel()` в `admin_panel/views.py`
- Action: `export_selected_to_excel` в `admin_panel/admin.py`

---

### 2. Экспорт в шаблон Ozon

**Описание:** Экспорт выбранных книг в официальный шаблон Ozon для загрузки товаров на маркетплейс.

**Как использовать:**

**Шаг 1: Загрузить шаблон Ozon**
1. Скачайте актуальный шаблон из Ozon Seller (формат .xlsx)
2. Зайдите в админку → "Шаблоны Ozon"
3. Нажмите "Добавить шаблон Ozon"
4. Заполните:
   - **Название:** например "Букинистические издания май 2026"
   - **Файл:** загрузите Excel файл
   - **Активный:** поставьте галочку
5. Сохраните

**Шаг 2: Экспортировать книги**
1. Перейдите в "Каталог — админка" или "Каталог — Эксмо"
2. Выберите нужные книги через чекбоксы
3. В выпадающем списке действий выберите "Экспортировать выбранные в шаблон Ozon"
4. Нажмите "Выполнить"
5. Скачается заполненный шаблон Ozon с вашими книгами

**Маппинг полей:**

| Поле Ozon | Поле в БД | Преобразование |
|-----------|-----------|----------------|
| Артикул* | sku | - |
| Название товара | title | - |
| Цена, руб.* | price | - |
| Цена до скидки, руб. | old_price | - |
| НДС, %* | vat_rate | - |
| Вес в упаковке, г* | weight | кг → граммы (×1000) |
| Ширина упаковки, мм* | width | см → мм (×10) |
| Высота упаковки, мм* | height | см → мм (×10) |
| Длина упаковки, мм* | length | см → мм (×10) |
| Автор на обложке | author_oblozh | - |
| Автор | author | - |
| Тип обложки | cover_type | Твердый/Мягкий |
| Тип* | - | "Букинистическое издание" |
| Бренд* | publisher | - |
| ТН ВЭД коды ЕАЭС* | - | "4901990000" (код для книг) |
| Издательство | publisher | - |
| Серия | series | - |
| Год выпуска | publication_year | - |
| Язык издания | language | - |
| Количество страниц | pages | - |
| ISBN | isbn | - |
| Аннотация | description | - |

**Технические детали:**
- Библиотека: `openpyxl 3.1.2`
- Функция: `export_books_to_ozon_template()` в `admin_panel/views.py`
- Action: `export_selected_to_ozon` в `admin_panel/admin.py`
- Модель: `OzonTemplate` в `admin_panel/models.py`
- Лист шаблона: "Шаблон"
- Строка заголовков: 2
- Начало данных: строка 5

**Особенности:**
- Автоматическое преобразование единиц измерения (кг→г, см→мм)
- Поддержка только одного активного шаблона
- При загрузке нового активного шаблона, предыдущий автоматически деактивируется
- Валидация наличия шаблона перед экспортом
- Обработка ошибок с понятными сообщениями

---

## Модели данных

### OzonTemplate (новая модель)

**Описание:** Модель для хранения шаблонов Ozon, загружаемых вручную через админку.

**Поля:**
- `name` - Название шаблона (CharField, max_length=200)
- `file` - Excel файл шаблона (FileField, upload_to='ozon_templates/')
- `description` - Описание шаблона (TextField, blank=True)
- `is_active` - Активный шаблон (BooleanField, default=True)
- `uploaded_at` - Дата загрузки (DateTimeField, auto_now_add=True)

**Meta:**
- verbose_name = "Шаблон Ozon"
- verbose_name_plural = "Шаблоны Ozon"
- ordering = ['-uploaded_at']

**Логика:**
- При сохранении активного шаблона, все остальные автоматически деактивируются
- Только один шаблон может быть активным одновременно
- Файлы хранятся в `media/ozon_templates/`

**Админка:**
- Список: название, активность, дата загрузки, файл
- Фильтры: активность, дата загрузки
- Поиск: название, описание
- Readonly: дата загрузки

---

## База данных

### Текущее состояние (25.05.2026)

**Пользователи:**
- Логин: `semen`
- Пароль: `semen`
- Тип: суперпользователь

**Книги:**
- Всего: 9141 книга
- Источник: Импорт из Эксмо (parsing/eksmo_books_mt_deduped.json)
- Все книги имеют source='eksmo'

**Категории:**
- Всего: 3 категории

**Таблицы:**
- `admin_panel_book` - книги
- `admin_panel_category` - категории
- `admin_panel_ozontemplate` - шаблоны Ozon (новая)
- `auth_user` - пользователи
- `django_admin_log` - логи админки
- `django_session` - сессии
- и другие системные таблицы Django

---

## Импорт данных

### Импорт книг из JSON

**Скрипт:** `import_books.py` (в корне проекта)

**Описание:** Импортирует книги из JSON файла в базу данных.

**Использование:**
```bash
python import_books.py
```

**Особенности:**
- Батчевая вставка по 500 книг
- Пропуск дубликатов по ISBN и источнику
- Автоматическое определение типа переплета
- Парсинг года издания и количества страниц
- Установка source='eksmo' для всех импортированных книг
- Логирование прогресса

**Результат последнего импорта:**
- Импортировано: 9141 книга
- Пропущено: 0
- Источник: `parsing/eksmo_books_mt_deduped.json`

---

## Поиск в админке

### Поиск по ISBN

**Описание:** Реализован поиск книг по ISBN через стандартное поле поиска Django admin.

**Особенности:**
- Поиск работает по точному совпадению
- ISBN должен быть введен в том же формате, что хранится в БД
- Поддерживаются форматы с дефисами и без: `978-5-04-122320-5` или `9785041223205`

**Поля поиска:**
- SKU (артикул)
- Название
- Автор
- Автор на обложке
- Жанр
- Издательство
- Серия
- Язык
- ISBN

---

## Обслуживание базы данных

### Очистка базы данных

**Удаление всех книг:**
```bash
python manage.py shell -c "from admin_panel.models import Book; Book.objects.all().delete()"
```

**Удаление всех пользователей:**
```bash
python manage.py shell -c "from django.contrib.auth.models import User; User.objects.all().delete()"
```

**Создание нового суперпользователя:**
```bash
python manage.py shell -c "from django.contrib.auth.models import User; User.objects.create_superuser('username', 'email@example.com', 'password')"
```

**Полное пересоздание БД:**
```bash
# 1. Удалить базу
psql -U rustamismagilov -c "DROP DATABASE shop_admin_db;"

# 2. Создать заново
psql -U rustamismagilov -c "CREATE DATABASE shop_admin_db;"

# 3. Применить миграции
python manage.py migrate

# 4. Создать суперпользователя
python manage.py createsuperuser
```

---

## История изменений (25.05.2026)

### Добавлено:
1. ✅ Экспорт книг в Excel (.xlsx)
2. ✅ Модель OzonTemplate для хранения шаблонов Ozon
3. ✅ Экспорт книг в шаблон Ozon с автоматическим маппингом полей
4. ✅ Админка для управления шаблонами Ozon
5. ✅ Библиотека openpyxl для работы с Excel
6. ✅ Импорт 9141 книги из JSON файла Эксмо
7. ✅ Очистка базы данных от старых данных
8. ✅ Создание нового пользователя semen/semen

### Удалено:
1. ❌ Экспорт в Ozon YML (YAML формат) - закомментирован
2. ❌ Кнопка "Экспорт всех в Ozon YML" из change_list.html
3. ❌ Action "Экспортировать выбранные в Ozon YML"
4. ❌ URL маршрут для export_ozon_yml

### Изменено:
1. 🔄 requirements.txt - добавлен openpyxl==3.1.2
2. 🔄 Python версия обновлена до 3.14
3. 🔄 База данных полностью очищена и заполнена заново

---
- Полная документация
- Безопасная конфигурация

Проект готов как для разработки новых функций, так и для развертывания в продакшене.

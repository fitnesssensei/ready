# GoryKnig — Django Admin Panel

Панель управления интернет-магазином книг с экспортом в Ozon YML.

## Быстрый старт

### 1. Установите зависимости
```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Настройте переменные окружения
Отредактируйте файл `.env` в корне проекта:
```
DB_NAME=shop_admin_db
DB_USER=postgres
DB_PASSWORD=ваш_пароль
DB_HOST=localhost
DB_PORT=5432

OZON_SHOP_ID=ваш_shop_id_на_озон
```

> Для продакшена обязательно замените `SECRET_KEY` на уникальный и установите `DEBUG=False`.

### 3. Создайте базу данных PostgreSQL
```bash
psql -U postgres -c "CREATE DATABASE shop_admin_db;"
```

### 4. Примените миграции
```bash
python manage.py migrate
```

### 5. Создайте суперпользователя
```bash
python manage.py createsuperuser
```

### 6. Запустите сервер
```bash
python manage.py runserver
```

Откройте http://127.0.0.1:8000/admin/ и войдите под суперпользователем.

---

## Структура проекта

```
goryKnig/
├── manage.py
├── requirements.txt
├── .env                    # ← ваши секреты (не коммитить в git!)
├── .env.example            # ← шаблон для команды
├── shop_admin/             # Django-проект (settings, urls)
├── admin_panel/            # Основное приложение
│   ├── models.py           # Модели Book, Category
│   ├── admin.py            # Настройка Django Admin
│   ├── views.py            # Экспорт Ozon YML
│   ├── widgets.py          # Виджет загрузки фото
│   ├── migrations/         # Миграции БД
│   └── templates/          # HTML-шаблоны
└── media/                  # Загруженные файлы
```

## Экспорт в Ozon YML

- **Экспорт выбранных**: отметьте книги галочками → действие «Экспортировать выбранные в Ozon YML»
- **Экспорт всех**: кнопка «📥 Экспорт всех в Ozon YML» в шапке списка книг

Для успешного экспорта у каждой книги должны быть заполнены:
- Название, Цена > 0, Категория с Ozon ID, Остаток на складе, хотя бы одна фотография

## Известные ограничения

- Формат экспорта — YAML (`.yml`). Если Ozon требует XML-based YML, нужно доработать `views.py`.
- Максимум 10 фотографий на книгу.

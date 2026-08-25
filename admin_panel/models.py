from email.policy import default
from random import choice
from webbrowser import get
from django.db import models
from django.conf import settings  # ← для ссылки на модель User (AUTH_USER_MODEL)
from . import constants


class OzonTemplate(models.Model):
    """
    Модель для хранения шаблонов Ozon.

    Шаблоны загружаются вручную через админку и используются для экспорта
    товаров в формате, совместимом с Ozon Seller.

    Особенности:
    - Несколько шаблонов могут быть активными одновременно
    - По году издания книги определяется, в какой шаблон она попадёт
    - Файлы хранятся в media/ozon_templates/
    """

    # Название шаблона для идентификации (например, "Букинистика май 2026")
    name = models.CharField(max_length=200, verbose_name="Название шаблона")

    # Excel файл шаблона, скачанный из Ozon Seller
    file = models.FileField(upload_to='ozon_templates/', verbose_name="Excel файл")

    # Необязательное описание для дополнительной информации
    description = models.TextField(blank=True, verbose_name="Описание")

    # Минимальный год издания (включительно), с которого книги попадают в этот шаблон
    year_from = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Год от (включительно)",
        help_text="Если указано — книги с publication_year >= этого значения могут попасть сюда."
    )
    # Максимальный год издания (включительно), до которого книги попадают в этот шаблон
    year_to = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Год до (включительно)",
        help_text="Если указано — книги с publication_year <= этого значения могут попасть сюда."
    )

    # Флаг активности
    is_active = models.BooleanField(default=True, verbose_name="Активный")

    # Автоматическая дата загрузки шаблона
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата загрузки")

    class Meta:
        verbose_name = "Шаблон Ozon"
        verbose_name_plural = "Шаблоны Ozon"
        ordering = ['-uploaded_at']  # Сортировка по дате: новые сверху

    def __str__(self):
        """Строковое представление: название + дата"""
        return f"{self.name} ({self.uploaded_at.strftime('%Y-%m-%d')})"


class Category(models.Model):
    name = models.CharField(max_length=200, verbose_name="Название категории")
    ozon_category_id = models.CharField(max_length=50, verbose_name="ID категории Озон", unique=True, blank=True, null=True)
    description = models.TextField(blank=True, verbose_name="Описание")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} (Ozon ID: {self.ozon_category_id})"

def get_default_category():
    # Возвращаем первую категорию из списка (по алфавиту)
    cat = Category.objects.order_by('name').first()
    return cat.id if cat else None

def normalize_isbn(value):
    """Оставляет от ISBN только цифры (убирает дефисы и прочие символы)."""
    return ''.join(c for c in (value or '') if c.isdigit())

class Book(models.Model):
    # Обратная совместимость: атрибуты Book.SOURCE_* ссылаются на константы
    SOURCE_MANUAL = constants.SOURCE_MANUAL
    SOURCE_EKSMO = constants.SOURCE_EKSMO
    SOURCE_AST = constants.SOURCE_AST

    SOURCE_CHOICES = constants.SOURCE_CHOICES

    COVER_TYPES = constants.COVER_TYPES

    VAT_RATES = constants.VAT_RATES

    GENRE = constants.GENRE
    TARGET_AUDIENCE = constants.TARGET_AUDIENCE

    AGE_RESTRICTIONS = constants.AGE_RESTRICTIONS

    IS_ADULT = constants.IS_ADULT

    LANGUAGE_CHOICES = constants.LANGUAGE_CHOICES

    CONDITION_CHOICES = constants.CONDITION_CHOICES

    BOOK_TYPE = constants.BOOK_TYPE

    # строка "тип бумаги"
    PAPER_TYPES = constants.PAPER_TYPES

    title = models.CharField(max_length=200, verbose_name="Название", default="")
    source = models.CharField(
        max_length=10,
        choices=SOURCE_CHOICES,
        default=constants.DEFAULT_SOURCE,
        verbose_name="Источник",
        db_index=True,
    )
    
    sku = models.CharField(max_length=50, unique=True, blank=True, null=True, verbose_name="Артикул")
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Категория",
        default=get_default_category
    )

    author = models.CharField(max_length=100, verbose_name="Автор", default="", blank=True)
    author_oblozh = models.CharField(max_length=100, verbose_name="Автор на обложке", blank=True, null=True)
    illustrator = models.CharField(max_length=100, verbose_name="Иллюстратор", blank=True, null=True)
    translator = models.CharField(max_length=100, verbose_name="Переводчик", blank=True, null=True)
    genre = models.CharField(max_length=100, choices=GENRE, verbose_name="Направление", default=constants.DEFAULT_GENRE, blank=True)
    target_audience = models.CharField(max_length=100, choices=TARGET_AUDIENCE, verbose_name="Целевая аудитория", default=constants.DEFAULT_TARGET_AUDIENCE, blank=True)  # целевая аудитория 
    age_restrictions = models.CharField(max_length=100, choices=AGE_RESTRICTIONS, verbose_name="Возрастные ограничения", default=constants.DEFAULT_AGE_RESTRICTION, blank=True)  # возраст огран  
    is_adult = models.CharField(choices=IS_ADULT, verbose_name="Признак 18+", default=constants.DEFAULT_IS_ADULT, blank=True )
    publisher = models.CharField(max_length=100, verbose_name="Издательство", default="")
    series = models.CharField(max_length=200, verbose_name="Серия", blank=True, null=True)
    publication_year = models.PositiveIntegerField(verbose_name="Год издания", blank=True, null=True)
    language = models.CharField(max_length=50, choices=LANGUAGE_CHOICES, verbose_name="Язык издания", default=constants.DEFAULT_LANGUAGE)  # Язык издания
    condition = models.CharField(
        max_length=20, choices=CONDITION_CHOICES, verbose_name="Сохранность", default=constants.DEFAULT_CONDITION, blank=True  # состояние 
    )
    cover_type = models.CharField(
        max_length=20, choices=COVER_TYPES, verbose_name="Тип переплёта", default=constants.DEFAULT_COVER_TYPE
    )
    # строка "тип книги
    book_type = models.CharField(
        max_length=20, choices=BOOK_TYPE, verbose_name="Тип книги", default=constants.DEFAULT_BOOK_TYPE, blank=True)  # тип книги 

    # строка "тип бумаги"
    paper_type = models.CharField(
    max_length=20, choices=PAPER_TYPES, verbose_name="Тип бумаги", default=constants.DEFAULT_PAPER_TYPE, blank=True   # "тип бумаги"
    )
    # blank=True - для строк ; обе делают поле не обязательным 
    # null=True больше подходит для числовых 
    hashtags = models.CharField(max_length=200, verbose_name="Хештеги", blank=True, null=True)  # хештеги"
    pages = models.PositiveIntegerField(verbose_name="Количество страниц", blank=True, null=True)
    photos = models.JSONField(default=list, verbose_name="Фотографии", blank=True)
    description = models.TextField(blank=True, verbose_name="Описание", default="")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена", blank=True, null=True)  # цена не обязательно
    old_price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Старая цена / цена до скидки",
        blank=True, null=True
    )
    # ✅ FIX: default должен быть кодом из choices ('0'), а не отображаемым текстом ('Без НДС')
    vat_rate = models.CharField(max_length=2, choices=VAT_RATES, verbose_name="Ставка НДС", default=constants.DEFAULT_VAT_RATE)
    stock = models.PositiveIntegerField(verbose_name="Остаток на складе", default=1)
    isbn = models.CharField(max_length=20, verbose_name="ISBN", blank=True, null=True, )
    isbn_digits = models.CharField(   # isbn без дефисов
            max_length=20,
            blank=True,
            db_index=True,
            verbose_name="ISBN только цифры",
        )
    tnved_code = models.CharField(
        max_length=200, verbose_name="ТН ВЭД коды ЕАЭС", 
        default=constants.DEFAULT_TNVED_CODE, 
        blank=True, null=True
    )
    weight = models.DecimalField(
        max_digits=8, decimal_places=4, verbose_name="Вес с упаковкой (г)", blank=True, null=True
    )
    length = models.DecimalField(
        max_digits=6, decimal_places=2, verbose_name="Длина с упаковкой (мм)", blank=True, null=True
    )
    width = models.DecimalField(
        max_digits=6, decimal_places=2, verbose_name="Ширина с упаковкой (мм)", blank=True, null=True
    )
    height = models.DecimalField(
        max_digits=6, decimal_places=2, verbose_name="Высота с упаковкой (мм)", blank=True, null=True
    )
    publication_date = models.DateField(blank=True, null=True, verbose_name="Дата публикации")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    # --- Кто добавил книгу (заполняется автоматически при создании через админку) ---
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # ссылка на стандартную модель User
        on_delete=models.SET_NULL,  # если пользователя удалят — книга остаётся
        null=True, blank=True,
        editable=False,  # не показываем в форме добавления/редактирования книги
        verbose_name="Кем добавлена"
    )

    def save(self, *args, **kwargs):
        self.isbn_digits = normalize_isbn(self.isbn)
        super().save(*args, **kwargs)
    class Meta:
        verbose_name = "Книга"
        verbose_name_plural = "Книги"
        ordering = ['-created_at']
        indexes = [
        # Композитные индексы (составные)
        models.Index(fields=['source', 'created_at'], name='book_source_created_idx'),
        models.Index(fields=['source', 'isbn'],       name='book_source_isbn_idx'),
        # Одиночные индексы на часто используемые поля
        models.Index(fields=['created_at'],           name='book_created_at_idx'),
        models.Index(fields=['isbn'],                 name='book_isbn_idx'),
        # Индексы на поля фильтров (для быстрого поиска/фильтрации)
        models.Index(fields=['genre'],                name='book_genre_idx'),
        models.Index(fields=['publisher'],            name='book_publisher_idx'),
        models.Index(fields=['publication_year'],     name='book_pub_year_idx'),
        models.Index(fields=['category'],             name='book_category_idx'),
        models.Index(fields=['book_type'],            name='book_book_type_idx'),
        models.Index(fields=['language'],             name='book_language_idx'),
        models.Index(fields=['author'],               name='book_author_idx'),
        models.Index(fields=['series'],               name='book_series_idx'),
        models.Index(fields=['condition'],            name='book_condition_idx'),
        models.Index(fields=['cover_type'],           name='book_cover_type_idx'),
        ]
        # ... остальной код (constraints закомментированы и т.д.)
        # 🔇 Дедупликация на уровне БД отключена — она выполняется
        # на уровне приложения (в скриптах импорта).
        # constraints = [
        #     models.UniqueConstraint(
        #         fields=['isbn', 'source'],
        #         condition=models.Q(isbn__isnull=False),
        #         name='unique_isbn_per_source',
        #     ),
        # ]

    def __str__(self):
        return self.title


class ManualBook(Book):
    class Meta:
        proxy = True
        verbose_name = "Книга (админка)"
        verbose_name_plural = "Каталог — админка"
        permissions = [
            ("add_book_manual", "Может добавлять книги в Каталог — админка"),
            ("delete_book_manual", "Может удалять книги из Каталог — админка"),
            ("change_book_manual", "Может редактировать книги в Каталог — админка"),
            ("view_book_manual", "Может просматривать книги в Каталог — админка"),
        ]


class EksmoBook(Book):
    class Meta:
        proxy = True
        verbose_name = "Книга"
        verbose_name_plural = "База книг"
